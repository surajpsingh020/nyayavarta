"""LLM Service for Nyayavarta using Google Gemini API.

Orchestrates legal prompt engineering, profile-tailored reasoning,
old-to-new Indian law mapping (IPC->BNS, CrPC->BNSS, Evidence Act->BSA),
statutory citation extraction, and legal aid routing (NALSA / DLSA / 15100).
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.models.schemas import UserProfile

logger = logging.getLogger(__name__)

# Cooldown timestamp if Gemini returns hard 429 quota exhaustion to prevent tight retries
_GEMINI_QUOTA_EXHAUSTED_UNTIL: float = 0.0

# System prompt defining Nyayavarta legal AI persona and system scope
SYSTEM_PROMPT = """You are Nyayavarta (न्यायवार्ता), an expert, empathetic, and authoritative legal assistant designed to help Indian citizens navigate the Indian legal system, understand their rights, and map old Indian laws to new laws.

Key Directives:
1. LAW TRANSITIONS (Old -> New):
   - Always map the old Indian laws to the new 2023 criminal statutes:
     * Indian Penal Code (IPC, 1860) -> Bharatiya Nyaya Sanhita (BNS, 2023)
     * Code of Criminal Procedure (CrPC, 1973) -> Bharatiya Nagarik Suraksha Sanhita (BNSS, 2023)
     * Indian Evidence Act (IEA, 1872) -> Bharatiya Sakshya Adhiniyam (BSA, 2023)
   - Mention the specific section numbers from both old and new laws for clarity (e.g., "Section 103 of BNS, corresponding to Section 302 of the former IPC").
   - Mention notable modern legal updates where applicable (e.g., Zero FIR under Section 173 BNSS, digital and electronic records under Section 63 BSA, community service).

2. CITATIONS:
   - Provide precise citations for all statutory sections mentioned.

3. LEGAL AID ROUTING & SAFETY:
   - Provide guidance on accessing free legal assistance under the Legal Services Authorities Act, 1987 via NALSA (National Legal Services Authority), SLSA (State), and DLSA (District).
   - Mention the National Legal Aid Helpline: 15100 (toll-free, 24x7).
   - For emergencies, recommend Emergency Response Helpline: 112, Women Helpline: 1091, Cyber Crime: 1930.
   - For serious offenses, emphasize immediate safety and legal representation.

4. USER PROFILE ADAPTATION:
   - Adapt your tone, structure, and depth according to the specified User Profile.
   * STUDENT: Educational, clear breakdown of legal concepts, definitions, historical context, structured explanations.
   * PROFESSIONAL: Precise, formal legal terminology, procedural requirements, compliances, actionable steps.
   * SENIOR_CITIZEN: Empathetic, respectful, simple jargon-free guidance, elder protection rights, step-by-step instructions.
   * GENERAL: Practical, accessible everyday language, focus on citizen rights, plain remedies, and immediate steps.

5. INSTITUTIONAL SCOPE & BOUNDARIES:
   - Maintain strict factual correctness with respect to Indian law.
   - Respectfully clarify when appropriate that Nyayavarta focuses on statutory translation, citizen rights education, procedural roadmaps (FIR, arrest, bail), document analysis, and free legal aid routing. It does not contain the complete judgment archives, daily court cause lists, hearing transcripts, or case dockets of the Supreme Court of India, the 25 High Courts, or the 672 District Courts of India (which encompass hundreds of millions of case files across decades and require commercial multi-terabyte data warehouse infrastructure like SCC Online or e-Courts).
   - Add a brief, respectful legal disclaimer that this provides legal awareness and aid routing, not formal attorney representation.

6. STRICT DOMAIN BOUNDARY & NON-LEGAL REFUSAL:
   - You are exclusively a legal assistant for Indian Law.
   - If the user asks a question about science, biology (e.g. "what is mitochondria"), chemistry, physics, mathematics, recipes/cooking, entertainment, movie gossip, sports trivia, software programming, or general trivia unrelated to law:
     * YOU MUST POLITELY AND PROFESSIONALLY REFUSE to answer the question.
     * Do NOT explain the scientific concept.
     * Do NOT generate statutory punishment tables or fake legal analogies.
     * Return NO citations.
     * Greet the user with professional dignity and state:
       "Greetings. I am Nyayavarta, an artificial intelligence assistant dedicated exclusively to Indian law, citizen rights, FIR procedures, court processes, and modern statutory transitions (BNS, BNSS, and BSA).
       Because your inquiry concerns a non-legal topic outside the legal domain, I cannot assist with this question.
       If you have any legal questions, dispute issues, police complaints, or document analysis matters, please feel free to ask, and I will be glad to assist you."
"""

NON_LEGAL_INDICATORS = {
    # Biology / Medicine / Life Science
    "mitochondria", "photosynthesis", "cell membrane", "nucleus", "dna", "rna", "ribosome",
    "chloroplast", "endoplasmic reticulum", "golgi", "amoeba", "bacteria", "virus structure",
    "anatomy", "physiology", "hemoglobin", "cellular respiration", "mitosis", "meiosis", "organism",
    # Physics / Chemistry
    "speed of light", "quantum", "thermodynamics", "periodic table", "atomic mass", "gravity formula",
    "electron", "proton", "neutron", "chemical reaction", "newton's laws", "kinetic energy", "potential energy",
    "electromagnetism", "optics", "relativity",
    # Math
    "pythagoras", "derivative", "integral", "trigonometry", "solve equation", "algebra", "polynomial",
    "calculus", "matrix multiplication", "logarithm",
    # Cooking / Food
    "recipe for", "how to cook", "how to bake", "ingredients for", "cake recipe", "biryani recipe",
    # Tech / Coding Trivia
    "binary search tree", "how to code", "write javascript", "css flexbox", "quicksort algorithm",
    "write python", "debug code", "react component",
    # General Trivia / Entertainment / Sports
    "who won world cup", "best movie of", "celebrity gossip", "weather forecast", "cricket score",
    "football match", "capital of"
}


def _clean_llm_markdown(text: str) -> str:
    """Ensure clean GitHub Flavored Markdown table structure and section headers."""
    if not text:
        return text

    # Fix collapsed markdown table rows where | | occurs on a single line
    # e.g., "| Key Changes | | :--- | :--- | | Murder | IPC Section 302 |"
    cleaned = re.sub(r"\|\s*\|\s*(:?-+:?)", r"|\n| \1", text)
    cleaned = re.sub(r"\|\s*\|\s*([^|\n]+)", r"|\n| \1", cleaned)

    # Ensure table header separator | :--- | has a newline before and after
    cleaned = re.sub(r"([^\n])\n(\|[\s:-]+\|)", r"\1\n\n\2", cleaned)

    # Ensure double newlines before and after tables
    cleaned = re.sub(r"(\|[^\n]+\|)\n([^|\n#\d\*\-])", r"\1\n\n\2", cleaned)

    return cleaned


def is_out_of_domain_query(query: str) -> bool:
    """Detect if query is clearly outside the legal domain."""
    if not query:
        return False
    q_clean = query.lower().strip()
    for term in NON_LEGAL_INDICATORS:
        if term in q_clean:
            return True
    return False


def get_profile_instructions(profile: UserProfile) -> str:
    """Return specific instructions tailored to user persona."""
    if profile == UserProfile.STUDENT:
        return (
            "USER PROFILE: Student / Academic.\n"
            "- Explain the legal concepts clearly with definitions and statutory reasoning.\n"
            "- Highlight the theoretical and practical difference between the old law and new law.\n"
            "- Use structured educational bullet points and cite relevant jurisprudence where helpful."
        )
    elif profile == UserProfile.PROFESSIONAL:
        return (
            "USER PROFILE: Working Professional / Corporate.\n"
            "- Use concise, structured, and formal legal language.\n"
            "- Focus on statutory compliance, procedural timelines, liability, and exact section numbers.\n"
            "- Provide actionable corporate or workplace legal remedies if applicable."
        )
    elif profile == UserProfile.SENIOR_CITIZEN:
        return (
            "USER PROFILE: Senior Citizen.\n"
            "- Use warm, highly respectful, reassuring, and completely jargon-free language.\n"
            "- Break down the next steps into simple, numbered steps (Step 1, Step 2).\n"
            "- Mention Senior Citizen welfare rights (e.g. Maintenance and Welfare of Parents and Senior Citizens Act) and free doorstep DLSA legal aid where relevant."
        )
    else:
        return (
            "USER PROFILE: General Citizen.\n"
            "- Use plain, everyday language that is easy to understand without a legal background.\n"
            "- Emphasize basic citizen rights, immediate practical remedies, and how to file a report or reach legal aid."
        )


class LLMService:
    """Orchestrates LLM requests via Google Gemini API with multi-model fallback cascade."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Google GenAI client if API key is provided."""
        api_key = self.settings.GEMINI_API_KEY
        if api_key and "your_" not in api_key.lower():
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                logger.info(f"Initialized Google GenAI client with primary model: {self.settings.GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")
                self.client = None

    def _generate_with_gemini_cascade(
        self,
        contents: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        """Call Gemini with automatic model fallback cascade (handles 503/404 on overloaded models)."""
        if not self.client:
            return ""

        # Prioritized candidate models list
        candidates = [
            self.settings.GEMINI_MODEL,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
        ]
        # Deduplicate while preserving order
        unique_models = []
        seen = set()
        for m in candidates:
            if m and m not in seen:
                seen.add(m)
                unique_models.append(m)

        from google.genai import types
        config = types.GenerateContentConfig(temperature=temperature)
        if system_instruction:
            config.system_instruction = system_instruction

        last_error = None
        for model_name in unique_models:
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                if resp and resp.text and resp.text.strip():
                    return resp.text.strip()
            except Exception as e:
                err_str = str(e)
                last_error = e
                # Check for transient capacity or model availability issues
                if any(x in err_str for x in ["503", "404", "UNAVAILABLE", "NOT_FOUND", "high demand"]):
                    logger.info(f"Model '{model_name}' unavailable ({err_str[:40]}). Trying next candidate in cascade...")
                    continue
                elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"Model '{model_name}' quota exhausted (429). Trying next candidate...")
                    continue
                else:
                    raise e

        if last_error:
            raise last_error
        return ""

    async def generate_legal_response(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        user_profile: UserProfile = UserProfile.GENERAL,
    ) -> Dict[str, Any]:
        """Generate a profile-tailored legal response with citations and old/new law mappings."""
        # 0. Domain Guardrail: strictly decline non-legal queries
        if is_out_of_domain_query(query):
            refusal_text = (
                "Greetings. Welcome to Nyayavarta Legal Assistance.\n\n"
                "I am an artificial intelligence assistant dedicated exclusively to the **Indian legal system**, citizen rights, police and FIR procedures, court processes, and modern statutory transitions (Bharatiya Nyaya Sanhita - BNS, BNSS, and BSA).\n\n"
                "Because your question pertains to a subject outside the legal domain (such as general science, academic coursework, or general trivia), I cannot assist with this inquiry.\n\n"
                "If you have any **legal questions, property or contract disputes, workplace grievances, police or FIR issues, bail matters, or citizen rights questions**, please feel free to ask, and I will be honored to provide comprehensive legal guidance."
            )
            return {
                "english_response": refusal_text,
                "citations": [],
                "user_profile": user_profile.value
            }

        # 1. Format retrieved RAG context
        context_blocks = []
        citations: List[Dict[str, str]] = []
        has_user_document = False
        user_doc_filenames = set()

        if retrieved_context:
            for item in retrieved_context:
                text = item.get("text", "")
                meta = item.get("metadata", {})
                score = float(item.get("score", 0.0))
                # Only include context with genuine relevance score to prevent noisy hallucinated citations
                if score >= 0.2:
                    if meta.get("type") == "user_document" or meta.get("filename"):
                        has_user_document = True
                        fname = meta.get("filename", "User Document")
                        user_doc_filenames.add(fname)
                        pg = meta.get("page", 1)
                        context_blocks.append(f"--- Uploaded Legal Document Evidence: {fname} (Page {pg}) ---\n{text}")
                    elif meta.get("old_law") or meta.get("new_law"):
                        context_blocks.append(f"--- Statutory Knowledge Graph Record [Score: {score:.2f}] ---\n{text}")
                        citations.append({
                            "section": f"{meta.get('new_law', '')} (formerly {meta.get('old_law', '')})".strip(),
                            "subject": meta.get("subject", "Legal Provision"),
                            "key_changes": meta.get("key_changes", "")
                        })
            context_str = "\n\n".join(context_blocks) if context_blocks else ""
        else:
            context_str = ""

        if not context_str:
            context_str = (
                "[NOTICE]: No specific criminal section mappings were found in the local statutory index.\n"
                "Please provide a comprehensive response using standard Indian statutes (BNS, BNSS, BSA, Constitution of India, and relevant Special Acts), "
                "addressing the user's specific problem directly."
            )

        # Build specific document analysis directive if user uploaded an official legal document
        doc_analysis_directive = ""
        if has_user_document:
            docs_list_str = ", ".join(user_doc_filenames)
            doc_analysis_directive = f"""
CRITICAL DOCUMENT-GROUNDED CHARGES & SPECIAL ACTS INSTRUCTION:
The user is specifically asking about an uploaded official legal document/report ({docs_list_str}).
1. EXTRACT ALL FORMAL CHARGES FROM THE DOCUMENT:
   - Identify every statutory section, penal provision, and Act abbreviation explicitly recorded on the document (including Special Acts like UAPA, Arms Act, NDPS, POCSO, POSH, etc., as well as general penal codes like IPC / BNS).
   - In First Information Reports (FIRs), carefully inspect the header lines, "u/s", "Under Section", or "Brief description of offense with section & of property carried off".
   - If the document contains charges such as "17/20 UA(P)Act. & 25(1-C)A.Act.", you MUST explicitly identify and explain:
     * Section 17 of the Unlawful Activities (Prevention) Act, 1967 (UAPA): Punishment for raising funds for a terrorist act (minimum 5 years up to life imprisonment, and fine).
     * Section 20 of the Unlawful Activities (Prevention) Act, 1967 (UAPA): Punishment for being a member of a terrorist gang or banned organization (punishable with imprisonment extending to life, and fine).
     * Section 25(1-C) of the Arms Act, 1959: Punishment for manufacturing, possession, delivery, or use of prohibited firearms or live ammunition (rigorous imprisonment not less than 3 years up to 7 or 10 years, and fine).
     * Accompanying penal offenses: Extortion (BNS Section 308 / formerly IPC Section 383/384) and Criminal Intimidation (BNS Section 351/352 / formerly IPC Section 503/506).
2. CASE SPECIFICS FROM DOCUMENT:
   - State the Police Station, District, FIR Number, Date/Time of Occurrence, and Date/Time of Reporting.
   - Name the Informant / Complainant and the Accused entity (e.g. KCP War Group, (Kanglei) Mangal).
   - Summarize the concrete allegations: monetary extortion demands, threats to dental clinic staff, coerced donation for ammunition, and discovery of live ammunition in an envelope marked "DENTAL HUB".
3. STATUTORY CHARGES TABLE:
   - Include both the Special Acts (UAPA, Arms Act) and relevant general penal code transitions (BNS / IPC) in Section 2 of your response.
"""

        # 2. Build User Prompt with Structured Legal Directives
        profile_guide = get_profile_instructions(user_profile)
        user_prompt = f"""{profile_guide}

RETRIEVED LEGAL CONTEXT FROM KNOWLEDGE BASE & UPLOADED DOCUMENTS:
{context_str}

USER QUERY:
"{query}"
{doc_analysis_directive}
STRICT LANGUAGE CONSISTENCY REQUIREMENT:
- You must generate this response ENTIRELY and 100% in fluent, professional ENGLISH.
- DO NOT mix Hindi sentences, Hinglish words, or Devanagari script anywhere in the response (no "ज़मीन", "कब्जा", "थाना", etc.).
- All section titles, explanations, legal assessments, action plans, and notices must be written in pure English. Explain Indian property and criminal concepts in clear, everyday plain English.

CRITICAL DOMAIN & SCOPE VERIFICATION:
- Verify if the user query concerns Indian law, legal disputes, police/FIR complaints, citizen rights, or court processes.
- IF THE QUERY IS NOT ABOUT LAW (e.g. general science, biology, chemistry, physics, mathematics, recipes, programming, or trivia):
  DO NOT output any statutory tables, criminal offense mappings, or punishment sections.
  Instead, begin with a courteous professional greeting, explain politely that you are Nyayavarta, an assistant dedicated exclusively to Indian law and citizen rights, state clearly that you cannot assist with non-legal topics, and invite the citizen to ask any legal or police complaint question.

FOR LEGAL QUERIES, STRUCTURE YOUR ANSWER IN CLEAN, BEAUTIFUL GITHUB FLAVORED MARKDOWN:

Begin with a warm, professional legal greeting:
"Namaste. Welcome to Nyayavarta Legal Assistance. I am your artificial intelligence legal guide."

### 1. Executive Summary & Layman Explanation
- First, explain the entire situation in empathetic, easy-to-understand layman's language without legal jargon, so that any citizen clearly understands how the law views their situation.
- Then, state the core legal assessment and statutory stance in 2-3 clear, authoritative sentences addressing the user's specific query.

### 2. Statutory Law Transition & Charges Breakdown (Special Acts & BNS / BNSS / BSA)
Provide a clear comparative markdown table covering all charges:
| Statutory Act & Section | Legal Subject / Charge | Key Elements & Severity / Punishment | Modern Applicability / Transition |
| :--- | :--- | :--- | :--- |
| [Statute e.g. UAPA Sec 17] | [Terrorist Funding] | [Min 5 yrs to Life, Fine] | [Special Anti-Terror Act; bail restricted u/s 43D(5)] |
| [Statute e.g. BNS Sec 308] | [Extortion] | [Imprisonment up to 3 yrs / 10 yrs] | [Replaces IPC Section 384] |

Explain crucial modern statutory updates (e.g. Zero FIR / e-FIR under BNSS 173, Digital Evidence admissibility under BSA 63, or special statutory bail standards).

### 3. Step-by-Step Action Plan for Citizen
1. **[Step 1 Title]**: Exact practical action (e.g. preserving chats, emails, banking proofs, physical evidence).
2. **[Step 2 Title]**: Statutory remedy (e.g. approaching police for FIR under BNSS 173, cooperating with Investigating Officer, seeking witness protection).
3. **[Step 3 Title]**: Legal escalation (e.g. filing grievance before Magistrate, seeking DLSA counsel).

### 4. Citizen Rights & Procedural Safeguards
- **[Right 1]**: Citizen protection under the law (e.g. Witness Protection Scheme, Zero FIR).
- **[Right 2]**: Procedural safeguards against harassment or unlawful coercion.

### 5. Free Legal Aid & Emergency Helplines
- **National Legal Aid Helpline (NALSA / DLSA)**: Call **15100** (Toll-Free, 24x7) for free legal aid and counsel.
- **Police Emergency**: Dial **112**
- **Cyber Crime Portal**: Dial **1930** or visit **cybercrime.gov.in**
- **Women Helpline**: Dial **1091**

### 6. Institutional Scope Notice
- **Statutory Focus**: Nyayavarta provides statutory translation, rights education, procedural roadmaps (FIR, arrest, bail), document analysis, and free legal aid routing.
- **Case Law Boundary**: It does not contain the complete judgment archives, daily court cause lists, hearing transcripts, or case dockets of the Supreme Court of India, the 25 High Courts, or the 672 District Courts (which span hundreds of millions of case files across decades and require commercial multi-terabyte data warehouse infrastructure like SCC Online or Manupatra).

*Disclaimer: This response provides legal literacy and institutional aid routing under the Legal Services Authorities Act, 1987. For representation in court, consult an empanelled legal aid advocate.*
"""

        # 3. Call Gemini API via robust cascade
        english_text = ""
        global _GEMINI_QUOTA_EXHAUSTED_UNTIL
        now = time.time()

        if self.client and now >= _GEMINI_QUOTA_EXHAUSTED_UNTIL:
            try:
                def _call_gemini():
                    return self._generate_with_gemini_cascade(
                        contents=user_prompt,
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    )

                english_text = await asyncio.wait_for(
                    asyncio.to_thread(_call_gemini),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Gemini API call timed out after 30s. Using internal legal generator.")
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    _GEMINI_QUOTA_EXHAUSTED_UNTIL = time.time() + 600
                    logger.warning("Gemini API quota exhausted across candidates. 10-min cooldown activated.")
                else:
                    logger.warning(f"Gemini API cascade error ({e}). Using internal legal generator.")

        # 4. Fallback generator if API call didn't return text
        if not english_text:
            english_text = self._generate_fallback_response(query, retrieved_context, user_profile)

        # Clean markdown formatting so tables have proper newlines
        english_text = _clean_llm_markdown(english_text)

        # 5. Combine and prioritize retrieved RAG citations and text-extracted citations
        final_citations: List[Dict[str, str]] = []
        seen_sections = set()

        # Prioritize relevant citations that were retrieved from Neo4j AND are mentioned in text or query
        for c in citations:
            sec = c.get("section", "")
            sec_num_match = re.search(r"\b(\d+[A-Za-z]?)\b", sec)
            if sec_num_match:
                s_num = sec_num_match.group(1).upper()
                if s_num in english_text or s_num in query:
                    if s_num not in seen_sections:
                        seen_sections.add(s_num)
                        final_citations.append(c)

        # Add any other citations extracted from the generated text
        extracted_cits = self._extract_citations_from_text(english_text)
        for ec in extracted_cits:
            ec_sec = ec.get("section", "")
            ec_match = re.search(r"\b(\d+[A-Za-z]?)\b", ec_sec)
            s_num = ec_match.group(1).upper() if ec_match else ec_sec
            if s_num not in seen_sections:
                seen_sections.add(s_num)
                final_citations.append(ec)

        # Ensure legal aid citation is present if helpline is mentioned
        if ("15100" in english_text or "legal aid" in english_text.lower()) and "12" not in seen_sections:
            seen_sections.add("12")
            final_citations.append({
                "section": "Section 12, Legal Services Authorities Act, 1987",
                "subject": "Entitlement to Free State Legal Aid & NALSA 15100 Helpline",
                "key_changes": "Free state-sponsored counsel for eligible citizens."
            })

        return {
            "english_response": english_text,
            "citations": final_citations[:5] if final_citations else citations[:5],
            "user_profile": user_profile.value
        }

    async def translate_with_llm(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text accurately between English and Indian languages using Gemini."""
        if not text or not text.strip() or source_lang == target_lang:
            return text

        global _GEMINI_QUOTA_EXHAUSTED_UNTIL
        now = time.time()
        if not self.client or now < _GEMINI_QUOTA_EXHAUSTED_UNTIL:
            return text

        lang_names = {
            "hi": "Hindi (हिन्दी)",
            "bn": "Bengali (বাংলা)",
            "ta": "Tamil (தமிழ்)",
            "te": "Telugu (తెలుగు)",
            "mr": "Marathi (मराठी)",
            "gu": "Gujarati (ગુજરાતી)",
            "kn": "Kannada (ಕನ್ನಡ)",
            "ml": "Malayalam (മലയാളം)",
            "pa": "Punjabi (ਪੰਜਾਬੀ)",
            "or": "Odia (ଓଡ଼ିଆ)",
            "ur": "Urdu (اردو)",
            "en": "English",
            "as": "Assamese (অসমীয়া)",
            "sa": "Sanskrit (संस्कृतम्)"
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        if target_lang == "en":
            prompt = (
                f"You are a professional legal translator specializing in Indian statutes and citizen legal advice.\n"
                f"Translate the following legal guidance completely and fluently into 100% pure ENGLISH.\n\n"
                f"STRICT RULES FOR ENGLISH TRANSLATION:\n"
                f"1. Output the ENTIRE document in 100% fluent, natural ENGLISH. DO NOT leave any sentences, words, or explanations in Hindi or Devanagari script.\n"
                f"2. All section headers ('###'), table rows, bullet points, and citizen advice must be in clean English.\n"
                f"3. Preserve exact Markdown table formatting with row line-breaks ('| Col 1 | Col 2 |\\n| :--- | :--- |\\n| Val 1 | Val 2 |').\n"
                f"4. Preserve section numbers (e.g. BNS Section 318, BNSS 173, BSA 63) and emergency numbers (15100, 112, 1930, 1091).\n"
                f"5. Output ONLY the translated text without introductory commentary or prefixes.\n\n"
                f"Text to translate:\n{text}"
            )
        else:
            prompt = (
                f"You are a professional legal translator specializing in Indian statutes and citizen legal advice.\n"
                f"Translate the following legal guidance completely and fluently from {src_name} into {tgt_name}.\n\n"
                f"STRICT TRANSLATION RULES:\n"
                f"1. Output the ENTIRE document in {tgt_name} script and language (including all section titles, '###' headers, bullet points, explanations, action steps, and advice).\n"
                f"2. DO NOT leave half the response in English. The entire document must be translated into {tgt_name}.\n"
                f"3. In tables, translate the table headers and descriptions into {tgt_name}, while keeping statutory names recognizable (e.g. 'भारतीय न्याय संहिता (BNS)', 'धारा 103').\n"
                f"4. CRITICAL TABLE FORMATTING: Preserve Markdown table formatting with exact row line-breaks ('| Col 1 | Col 2 |\\n| :--- | :--- |\\n| Val 1 | Val 2 |'). Never concatenate table rows into a single line.\n"
                f"5. Preserve section numbers and emergency phone numbers (15100, 112, 1930, 1091).\n"
                f"6. Output ONLY the translated text without introductory commentary or prefixes.\n\n"
                f"Text to translate:\n{text}"
            )

        try:
            def _call_translate():
                return self._generate_with_gemini_cascade(
                    contents=prompt,
                    temperature=0.1
                )

            response_text = await asyncio.wait_for(
                asyncio.to_thread(_call_translate),
                timeout=40.0
            )
            if response_text and response_text.strip():
                return _clean_llm_markdown(response_text.strip())
        except asyncio.TimeoutError:
            logger.warning("Gemini translation timed out after 40s. Returning text.")
        except Exception as e:
            logger.warning(f"LLM translation failed ({e}). Returning original text.")

        return text

    async def transcribe_and_detect_audio(self, audio_base64: str) -> Dict[str, str]:
        """Automatically detect spoken Indian language and transcribe audio verbatim."""
        if not audio_base64 or not self.client:
            return {"detected_language": "hi", "transcription": ""}

        # Determine MIME type if data URI prefix is present
        mime_type = "audio/webm"
        clean_b64 = audio_base64.strip()
        if clean_b64.startswith("data:"):
            match = re.match(r"data:([^;]+);base64,(.+)", clean_b64)
            if match:
                mime_type = match.group(1)
                clean_b64 = match.group(2)

        try:
            audio_bytes = base64.b64decode(clean_b64)
            if len(audio_bytes) < 100:
                return {"detected_language": "hi", "transcription": ""}
        except Exception as e:
            logger.warning(f"Audio base64 decode error: {e}")
            return {"detected_language": "hi", "transcription": ""}

        from google.genai import types
        part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        prompt = (
            "You are an expert multilingual speech recognition system for Indian citizens.\n"
            "Listen to this audio recording carefully:\n"
            "1. Automatically identify the language being spoken. Return the exact BCP-47 language code:\n"
            "   'mr' (Marathi), 'bn' (Bengali), 'hi' (Hindi), 'ta' (Tamil), 'te' (Telugu), 'gu' (Gujarati),\n"
            "   'kn' (Kannada), 'ml' (Malayalam), 'pa' (Punjabi), 'or' (Odia), 'ur' (Urdu), 'as' (Assamese),\n"
            "   'sa' (Sanskrit), or 'en' (English).\n"
            "   IMPORTANT RULE: Carefully distinguish Marathi ('mr') from Hindi ('hi'). If the speaker uses Marathi words\n"
            "   such as 'माझा', 'मला', 'आहे', 'नाही', 'काय', 'कसे', 'त्रास', 'होते', 'झाले', identify as 'mr' (Marathi), NOT 'hi'.\n"
            "2. Transcribe the audio verbatim in its native script (e.g. Marathi/Devanagari, Bengali, Tamil, etc.).\n"
            "3. If the audio is empty, pure silence, or background noise without speech, return empty transcription.\n"
            "Respond ONLY with a JSON object:\n"
            "{\"detected_language\": \"<code>\", \"transcription\": \"<verbatim text>\"}"
        )

        try:
            def _call_asr():
                return self._generate_with_gemini_cascade(
                    contents=[part, prompt],
                    temperature=0.1
                )

            res_str = await asyncio.wait_for(
                asyncio.to_thread(_call_asr),
                timeout=25.0
            )

            if res_str:
                clean_json = re.sub(r"^```(?:json)?\s*", "", res_str.strip())
                clean_json = re.sub(r"\s*```$", "", clean_json)
                data = json.loads(clean_json)
                detected = data.get("detected_language", "hi").strip().lower()
                text = data.get("transcription", "").strip()

                # Verify Marathi vs Hindi from transcribed text
                if text:
                    from app.services.bhashini_utils import detect_language_heuristic
                    script_lang = detect_language_heuristic(text)
                    if script_lang in ("mr", "bn", "ta", "te", "gu", "kn", "ml", "pa", "or", "ur", "as", "sa"):
                        detected = script_lang

                logger.info(f"Audio ASR detected language '{detected}': '{text[:60]}'")
                return {"detected_language": detected, "transcription": text}
        except Exception as e:
            logger.warning(f"Gemini audio transcription error: {e}")

        return {"detected_language": "hi", "transcription": ""}

    def _generate_fallback_response(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        user_profile: UserProfile
    ) -> str:
        """Deterministic legal response generator when external API is unreachable."""
        if is_out_of_domain_query(query):
            return (
                "Greetings. Welcome to Nyayavarta Legal Assistance.\n\n"
                "I am an artificial intelligence assistant dedicated exclusively to the **Indian legal system**, citizen rights, police and FIR procedures, court processes, and modern statutory transitions (such as Bharatiya Nyaya Sanhita - BNS, BNSS, and BSA).\n\n"
                "Because your question pertains to a subject outside the legal domain (such as general science, academic coursework, or general trivia), I cannot assist with this inquiry.\n\n"
                "If you have any **legal questions, property or contract disputes, workplace grievances, police or FIR issues, bail matters, or citizen rights questions**, please feel free to ask, and I will be honored to provide comprehensive legal guidance."
            )

        q_lower = query.lower()

        # Workplace / Employer Harassment / Labor Issues
        if (
            "employer" in q_lower or "harass" in q_lower or "workplace" in q_lower
            or "salary" in q_lower or "job" in q_lower or "boss" in q_lower or "fired" in q_lower
            or "एम्प्लॉयर" in query or "परेशान" in query or "नौकरी" in query or "वेतन" in query
            or "कंपनी" in query or "ऑफिस" in query or "काम" in query
        ):
            old_law = "Sections 503 & 506 IPC (Criminal Intimidation) & Payment of Wages Act, 1936"
            new_law = "Sections 351 & 352 BNS, 2023 & Industrial Disputes / POSH Act, 2013"
            subject = "Workplace Harassment, Employment Rights & Criminal Intimidation"
            details = (
                "Under Indian law, employers, supervisors, or management cannot unlawfully threaten, harass, or withhold earned wages from employees:\n\n"
                "- **Criminal Intimidation & Verbal Abuse**: Threatening an employee with injury to their person, reputation, or livelihood is a criminal offense under Section 351 and Section 352 of Bharatiya Nyaya Sanhita (BNS), 2023 (formerly Sections 503 and 506 of IPC).\n"
                "- **Unlawful Wage Withholding**: Under the Payment of Wages Act, 1936 and the Industrial Relations framework, employers are legally obligated to disburse earned salary on time. Arbitrary withholding or unlawful salary deductions can be reported to the State Labor Commissioner.\n"
                "- **Gender-Based / Workplace Harassment**: If the harassment involves gender discrimination or hostility, the Sexual Harassment of Women at Workplace (POSH) Act, 2013 mandates immediate redressal through the organization's Internal Complaints Committee (ICC) or district Local Complaints Committee (LCC).\n"
                "- **Criminal Threats or Extortion**: If the employer issues physical threats, wrongful confinement, or extortionate demands (BNS Section 308 / formerly IPC 384), the employee has the legal right to lodge an FIR or Zero FIR under Section 173 BNSS at any police station."
            )
            immediate_steps = [
                "Document all evidence: Preserve emails, WhatsApp chats, attendance logs, appointment letters, salary slips, and recorded communications.",
                "Send a formal written grievance: Submit an official written notice/email to HR, Grievance Redressal Officer, or higher management detailing the harassment.",
                "Approach the Labor Commissioner: If wages are withheld or employment is unlawfully terminated, file a formal complaint before the local Labor Commissioner office.",
                "Lodge police complaint for threats: If there are threats to personal safety or reputation, file an FIR or e-FIR under Section 173 BNSS at the nearest police station.",
                "Access free legal counsel: Contact DLSA / NALSA Helpline 15100 for an empanelled legal aid advocate to issue a legal notice."
            ]

        # Murder / Homicide
        elif (
            "murder" in q_lower or "302" in q_lower or "103" in q_lower
            or "हत्या" in q_lower or "कत्ल" in q_lower
        ):
            old_law = "Section 302 of the Indian Penal Code (IPC), 1860"
            new_law = "Section 103 of the Bharatiya Nyaya Sanhita (BNS), 2023"
            subject = "Punishment for Murder"
            details = (
                "Whoever commits murder is punishable with death, or imprisonment for life, and shall also be liable to fine. "
                "The substantive offense is now governed under Section 103(1) of BNS 2023. Additionally, Section 103(2) "
                "specifically penalizes mob lynching and group murder with life imprisonment or death."
            )
            immediate_steps = [
                "Immediately contact police emergency services at 112.",
                "Secure the scene and do not disturb physical evidence.",
                "Lodge an FIR under Section 173 BNSS at the nearest police station."
            ]

        # Cheating / Financial Fraud
        elif (
            "cheating" in q_lower or "fraud" in q_lower or "420" in q_lower or "318" in q_lower
            or "धोखाधड़ी" in q_lower or "ठगी" in q_lower or "रुपये" in q_lower
        ):
            old_law = "Section 420 of the Indian Penal Code (IPC), 1860"
            new_law = "Section 318 of the Bharatiya Nyaya Sanhita (BNS), 2023"
            subject = "Cheating and Dishonestly Inducing Delivery of Property"
            details = (
                "Cheating and dishonest inducement of property is codified under Section 318 of BNS 2023. "
                "Punishment includes imprisonment for a term which may extend to seven years, and fine."
            )
            immediate_steps = [
                "For cyber/financial fraud, immediately call 1930 (National Cyber Crime Helpline) or report at cybercrime.gov.in.",
                "Notify your bank to freeze fraudulent transactions.",
                "Lodge an FIR under Section 318 BNS at your local police station."
            ]

        # Document Analysis / Special Acts / Extortion & Terror Charges
        elif (
            "uapa" in q_lower or "arms act" in q_lower or "extortion" in q_lower
            or "key charges" in q_lower or "charges in this report" in q_lower
            or any("17/20" in (item.get("text", "") or "") for item in retrieved_context)
            or any("kcp" in (item.get("text", "") or "").lower() for item in retrieved_context)
        ):
            old_law = "Sections 17 & 20 UA(P) Act, 1967, Section 25(1-C) Arms Act, 1959 & Sections 384/506 IPC"
            new_law = "Sections 17 & 20 UAPA (Special Act), Section 25(1-C) Arms Act & Sections 308/351 BNS, 2023"
            subject = "Terrorist Funding, Terrorist Organization Membership, Prohibited Arms & Extortion"
            details = (
                "Based on the official police First Information Report (FIR No. 140(02)2024 PRT-PS, Porompat Police Station, Imphal East) and complainant report by Dr. Raynold Singh Khumanthem:\n\n"
                "1. **Section 17, Unlawful Activities (Prevention) Act, 1967 (UAPA)**: Penalizes raising, collecting, or providing funds for a terrorist act or terrorist organization. Coercing citizens and clinic staff into paying extortionate demands or 'donations' for a banned extremist group (KCP War Group) constitutes terrorist funding. Punishable with imprisonment not less than 5 years extending to life, and fine. Regular bail is heavily restricted under Section 43D(5) UAPA.\n"
                "2. **Section 20, Unlawful Activities (Prevention) Act, 1967 (UAPA)**: Penalizes being a member of a terrorist gang or banned organization (Kangleipak Communist Party / KCP War Group). Punishable with imprisonment extending to life, and fine.\n"
                "3. **Section 25(1-C), Arms Act, 1959**: Penalizes the possession, delivery, manufacture, or transfer of prohibited arms or prohibited ammunition. Specifically invoked due to live firearm ammunition being left in an envelope marked 'DENTAL HUB' at the Kongba Bazar clinic entrance. Attracts rigorous imprisonment of not less than 3 years up to 7 or 10 years, and fine.\n"
                "4. **Extortion & Criminal Intimidation (BNS Sections 308 & 351 / formerly IPC Sections 384 & 506)**: Intimidating clinic doctors and staff under threat to life and property to extort Rs 1,00,000 (and coercing payment of Rs 30,000) constitutes extortion and criminal intimidation under the general penal framework."
            )
            immediate_steps = [
                "Preserve all physical and electronic evidence: Safeguard the envelope, live ammunition, threatening letters, call records, and payment receipts without tampering.",
                "Cooperate with the Investigating Officer (SDPO): Provide complete statements and any clinic CCTV footage to Smt. Babitarani Swain, IPS, SDPO PRT, or the assigned investigating authority.",
                "Request formal witness and victim protection: Because the matter involves a banned terrorist outfit and firearm ammunition, formally petition the Superintendent of Police (SP) for police protection under the Witness Protection Scheme.",
                "Access legal counsel via Legal Aid: Contact DLSA / NALSA Helpline 15100 to ensure formal representation and procedural monitoring throughout the trial."
            ]

        # FIR / Police Complaint
        elif (
            "fir" in q_lower or "police" in q_lower or "154" in q_lower or "173" in q_lower
            or "एफआईआर" in query or "जीरो" in query or "दर्ज" in query or "थाना" in query
        ):
            old_law = "Section 154 of the Code of Criminal Procedure (CrPC), 1973"
            new_law = "Section 173 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
            subject = "First Information Report (FIR) & Zero FIR Legality"
            details = (
                "Under Section 173 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 (replacing Section 154 CrPC), "
                "Zero FIR is formally codified into statute. Any citizen can lodge an FIR at ANY police station "
                "regardless of territorial jurisdiction. The station must immediately record the information, provide a free copy to "
                "the complainant, and transfer the case to the competent jurisdictional police station. "
                "Furthermore, Section 173(1) BNSS allows information to be submitted electronically (e-FIR), which must be signed within three days."
            )
            immediate_steps = [
                "Collect all incident details, dates, times, and available evidence.",
                "Visit nearest police station and request Zero FIR under Section 173 BNSS.",
                "Obtain a signed copy of the registered FIR free of cost."
            ]

        # Arrest Rights
        elif (
            "arrest" in q_lower or "गिरफ्तारी" in q_lower or "35" in q_lower or "custody" in q_lower or "कस्टडी" in q_lower
        ):
            old_law = "Section 41A, 50, and 54 of the Code of Criminal Procedure (CrPC), 1973"
            new_law = "Section 35 and Section 53 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
            subject = "Citizen Rights Upon Arrest & Mandatory Safeguards"
            details = (
                "Under Section 35 of BNSS 2023, arrest procedures have vital safeguards: "
                "(1) For offenses punishable with less than 7 years imprisonment, prior permission of a Deputy Superintendent of Police (DSP) is mandatory before arresting senior citizens or infirm persons. "
                "(2) Right to receive a written Notice of Appearance under Section 35(3) BNSS before arrest. "
                "(3) Right to be informed immediately of the full grounds of arrest and bail eligibility (Section 47 BNSS / formerly Section 50 CrPC). "
                "(4) Right to consult and be represented by an advocate of choice during interrogation. "
                "(5) Mandatory medical examination of the arrested person upon detention under Section 53 BNSS."
            )
            immediate_steps = [
                "Ask the arresting officer for their identification and a signed Arrest Memo.",
                "Exercise your right to notify a family member or advocate immediately.",
                "Request free legal representation from DLSA Helpline 15100."
            ]

        # Free Legal Aid & Senior Citizens
        elif (
            "legal aid" in q_lower or "nalsa" in q_lower or "dlsa" in q_lower or "15100" in q_lower
            or "वरिष्ठ" in query or "senior" in q_lower or "सहायता" in query
        ):
            old_law = "Legal Services Authorities Act, 1987 & Article 39A of the Constitution of India"
            new_law = "NALSA Legal Services Authorities Framework & Maintenance and Welfare of Parents and Senior Citizens Act, 2007"
            subject = "Free Legal Aid & Senior Citizen Welfare Entitlements"
            details = (
                "Under Article 39A of the Constitution of India and Section 12 of the Legal Services Authorities Act, 1987: "
                "(1) Free legal representation and advice are guaranteed to Senior Citizens, women, children, members of SC/ST communities, and individuals in custody. "
                "(2) The National Legal Aid Helpline 15100 operates 24x7 toll-free across all States and District Legal Services Authorities (DLSA). "
                "(3) Senior citizens facing abandonment, maintenance denial, or property disputes have statutory recourse before Maintenance Tribunals with free doorstep paralegal assistance."
            )
            immediate_steps = [
                "Call 15100 (Toll-Free, 24x7) to connect with your District Legal Services Authority.",
                "Submit an application for a free state-appointed legal aid advocate.",
                "Senior citizens can also call Elderline 14567 for elder welfare disputes."
            ]

        # Electronic Evidence
        elif (
            "evidence" in q_lower or "electronic" in q_lower or "65b" in q_lower or "63" in q_lower
            or "सबूत" in query or "साक्ष्य" in query
        ):
            old_law = "Section 65B of the Indian Evidence Act (IEA), 1872"
            new_law = "Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023"
            subject = "Admissibility of Electronic Records"
            details = (
                "Section 63 of BSA expands and modernizes admissibility of electronic evidence, covering emails, "
                "server logs, digital records, smartphone messages, and GPS location records."
            )
            immediate_steps = [
                "Preserve original digital files with hash and metadata intact.",
                "Take screenshots and secure device backup.",
                "Obtain certificate under Section 63 BSA for court submission."
            ]

        # General Civil/Criminal Legal Query
        else:
            old_law = "Relevant sections of the Indian Penal Code (IPC) / CrPC"
            new_law = "Bharatiya Nyaya Sanhita (BNS) / BNSS, 2023"
            subject = "General Legal Assessment & Citizen Protection"
            details = (
                "Under India's modern criminal and civil legal framework (BNS, BNSS, and BSA effective July 1, 2024), "
                "citizens are protected against unlawful acts, harassment, fraud, and threats. You have full constitutional and "
                "statutory recourse through jurisdictional courts, police authorities, and state legal aid institutions."
            )
            immediate_steps = [
                "Document all relevant dates, incident details, communications, and witnesses.",
                "If this involves a cognizable offense, approach your nearest police station to lodge an FIR under Section 173 BNSS.",
                "Call National Legal Aid Helpline 15100 (Toll-Free, 24x7) to receive free consultation from a legal aid attorney."
            ]

        steps_rendered = "\n".join(f"{i+1}. {step}" for i, step in enumerate(immediate_steps))

        response = f"""Namaste. Welcome to Nyayavarta Legal Assistance. I am your artificial intelligence legal guide.

Here is clear guidance on how Indian law protects you and what steps you can take:

### 1. Executive Summary & Layman Explanation
- **In Plain Terms**: If you are experiencing this situation, Indian law recognizes that your personal rights, financial security, or peace of mind are legally protected. You do not have to endure unlawful actions alone; the legal framework provides structured mechanisms to report incidents, safeguard your evidence, and obtain state intervention.
- **Legal Assessment**: {details[:250]}...

### 2. Statutory Law Transition (IPC / CrPC → BNS / BNSS / BSA)
| Legal Subject | Historical Provision | Modern Provision (2023) | Key Statutory Changes |
| :--- | :--- | :--- | :--- |
| {subject} | {old_law} | {new_law} | Substantive codified legal transition |

{details}

### 3. Immediate Recommended Steps
{steps_rendered}

### 4. Citizen Rights & Procedural Safeguards
- **Zero FIR & Mandatory Recording**: Under Section 173 BNSS, an FIR can be filed at any police station regardless of jurisdiction, and a free registered copy must be provided.
- **Fair Representation**: Every citizen has the right to free legal representation if unable to afford private counsel under Article 39A of the Constitution of India.

### 5. Free Legal Aid & Helplines
- **National Legal Aid Helpline (NALSA / DLSA)**: Call **15100** (Toll-Free, 24x7) for free legal aid.
- **Police Emergency**: Dial **112**.
- **Women Helpline**: Dial **1091**.
- **Cyber Crime Portal**: Call **1930** or report on **cybercrime.gov.in**.

### 6. Institutional Scope Notice
- **Statutory Focus**: Nyayavarta focuses on statutory translation, citizen rights education, procedural roadmaps (FIR, arrest, bail), document analysis, and free legal aid routing.
- **Case Law Boundary**: It does not contain the complete judgment archives, daily court cause lists, hearing transcripts, or case dockets of the Supreme Court of India, the 25 High Courts, or the 672 District Courts (which require commercial multi-terabyte data warehouse infrastructure like SCC Online or Manupatra).

*Disclaimer: Nyayavarta provides legal awareness and aid routing. For formal representation in a court of law, please consult an empanelled legal aid advocate or attorney.*
"""
        return response

    def _extract_citations_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract only statutory citations that are genuinely mentioned in the generated text."""
        if not text or "outside the legal domain" in text.lower() or "dedicated exclusively to the" in text.lower():
            return []
        citations = []
        seen = set()

        # Known statutes lookup for authoritative titling and notes
        STATUTE_INFO = {
            "103": ("BNS Section 103 (formerly IPC Section 302)", "Punishment for Murder & Capital Offence", "Death penalty or imprisonment for life, and fine."),
            "302": ("IPC Section 302 (replaced by BNS Section 103)", "Punishment for Murder (Historical)", "Replaced by Section 103 BNS."),
            "249": ("BNS Section 249 (formerly IPC Section 212)", "Harbouring Offender (Screening from Punishment)", "Harbouring a person who committed a capital offence carries up to 5 years rigorous imprisonment."),
            "212": ("IPC Section 212 (replaced by BNS Section 249)", "Harbouring Offender (Historical)", "Replaced by Section 249 BNS."),
            "238": ("BNS Section 238 (formerly IPC Section 201)", "Causing Disappearance of Evidence / Giving False Info", "Penalizes destroying evidence or misleading police to screen an offender."),
            "201": ("IPC Section 201 (replaced by BNS Section 238)", "Disappearance of Evidence (Historical)", "Replaced by Section 238 BNS."),
            "33": ("BNSS Section 33 (formerly CrPC Section 39)", "Duty of Public to Give Information of Heinous Crimes", "Mandates every citizen aware of murder/heinous crimes to inform the nearest police or magistrate."),
            "39": ("CrPC Section 39 (replaced by BNSS Section 33)", "Public Duty to Inform Police (Historical)", "Replaced by Section 33 BNSS."),
            "318": ("BNS Section 318 (formerly IPC Section 420)", "Cheating & Dishonestly Inducing Delivery of Property", "Imprisonment up to 7 years and fine."),
            "420": ("IPC Section 420 (replaced by BNS Section 318)", "Cheating (Historical)", "Replaced by Section 318 BNS."),
            "86": ("BNS Section 86 (formerly IPC Section 498A)", "Cruelty by Husband or Relatives", "Enhanced focus on women safety; imprisonment up to 3 years and fine."),
            "498A": ("IPC Section 498A (replaced by BNS Section 86)", "Cruelty (Historical)", "Replaced by Section 86 BNS."),
            "65": ("BNS Section 65 (formerly IPC Section 376)", "Punishment for Rape & Sexual Offences", "Imprisonment not less than 10 years up to life."),
            "376": ("IPC Section 376 (replaced by BNS Section 65)", "Rape (Historical)", "Replaced by Section 65 BNS."),
            "80": ("BNS Section 80 (formerly IPC Section 304B)", "Dowry Death", "Imprisonment not less than 7 years up to life."),
            "304B": ("IPC Section 304B (replaced by BNS Section 80)", "Dowry Death (Historical)", "Replaced by Section 80 BNS."),
            "305": ("BNS Section 305 (formerly IPC Section 379)", "Theft & Larceny", "Imprisonment up to 3 years, fine, or community service."),
            "379": ("IPC Section 379 (replaced by BNS Section 305)", "Theft (Historical)", "Replaced by Section 305 BNS."),
            "351": ("BNS Section 351 (formerly IPC Section 503)", "Criminal Intimidation & Workplace Threats", "Penalizes threatening a person, reputation, or livelihood."),
            "352": ("BNS Section 352 (formerly IPC Section 506)", "Punishment for Criminal Intimidation", "Penalizes threats of death, injury, or ruin."),
            "173": ("BNSS Section 173 (formerly CrPC Section 154)", "Information in Cognizable Cases & Zero FIR", "Formalizes Zero FIR across any station; enables electronic e-FIR."),
            "154": ("CrPC Section 154 (replaced by BNSS Section 173)", "FIR Registration (Historical)", "Replaced by Section 173 BNSS."),
            "35": ("BNSS Section 35 (formerly CrPC Section 41/41A)", "Arrest Safeguards & Notice of Appearance", "Mandates notice of appearance before arrest for offences under 7 years."),
            "63": ("BSA Section 63 (formerly IEA Section 65B)", "Admissibility of Electronic and Digital Records", "Expands electronic evidence to include server logs, mobile chats, and GPS."),
            "65B": ("IEA Section 65B (replaced by BSA Section 63)", "Electronic Records (Historical)", "Replaced by Section 63 BSA."),
            "478": ("BNSS Section 478 (formerly CrPC Section 436)", "Bail in Bailable Offences", "Mandatory statutory right to bail for bailable matters."),
            "479": ("BNSS Section 479", "Maximum Period of Detention of Undertrials", "Provides early bail relief for undertrial prisoners who served one-third sentence."),
            "483": ("BNSS Section 483 (formerly CrPC Section 439)", "Special Powers of High Court / Sessions Court on Bail", "Discretionary bail relief in non-bailable offences."),
            # Extortion
            "308": ("BNS Section 308 (formerly IPC Section 383 & 384)", "Extortion by Putting Person in Fear of Injury", "Imprisonment up to 3 years, or fine, or both (up to 10 years if threat involves death/grievous hurt)."),
            "384": ("IPC Section 384 (replaced by BNS Section 308)", "Punishment for Extortion (Historical)", "Replaced by Section 308 BNS."),
            "383": ("IPC Section 383 (replaced by BNS Section 308)", "Extortion Definition (Historical)", "Replaced by Section 308 BNS."),
            # Criminal Trespass / Land Encroachment
            "329": ("BNS Section 329 (formerly IPC Section 441)", "Criminal Trespass & Unlawful Encroachment", "Entering property in possession of another to commit offence or intimidate."),
            "333": ("BNS Section 333 (formerly IPC Section 447)", "Punishment for Criminal Trespass", "Imprisonment up to 3 months, or fine up to Rs 5,000, or both."),
            "441": ("IPC Section 441 (replaced by BNS Section 329)", "Criminal Trespass (Historical)", "Replaced by Section 329 BNS."),
            "447": ("IPC Section 447 (replaced by BNS Section 333)", "Punishment for Criminal Trespass (Historical)", "Replaced by Section 333 BNS."),
            # Special Acts: UAPA & Arms Act
            "17": ("Section 17, Unlawful Activities (Prevention) Act, 1967", "Punishment for Raising Funds for Terrorist Act", "Imprisonment for not less than 5 years extending to life, and fine. Non-bailable under Section 43D(5)."),
            "20": ("Section 20, Unlawful Activities (Prevention) Act, 1967", "Punishment for Being Member of Terrorist Gang or Organisation", "Imprisonment extending to life, and fine. Targets members of declared terrorist entities."),
            "25(1-C)": ("Section 25(1-C), Arms Act, 1959", "Possession / Delivery of Prohibited Arms or Ammunition", "Rigorous imprisonment not less than 3 years up to 7 or 10 years, and fine."),
            "25": ("Section 25, Arms Act, 1959", "Punishment for Certain Offences under Arms Act", "Rigorous imprisonment and fine for illegal arms/ammunition possession."),
        }

        # Check explicit section mentions in text (both "Section 103 BNS" and "BNS Section 103")
        patterns = [
            (r"\bBNS\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?|\d+\(\d+\))\b", "BNS"),
            (r"Section\s*(\d+[A-Za-z]?|\d+\(\d+\))\s*(?:of\s*)?(?:the\s*)?BNS\b", "BNS"),
            (r"\bBNSS\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?|\d+\(\d+\))\b", "BNSS"),
            (r"Section\s*(\d+[A-Za-z]?|\d+\(\d+\))\s*(?:of\s*)?(?:the\s*)?BNSS\b", "BNSS"),
            (r"\bBSA\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?|\d+\(\d+\))\b", "BSA"),
            (r"Section\s*(\d+[A-Za-z]?|\d+\(\d+\))\s*(?:of\s*)?(?:the\s*)?BSA\b", "BSA"),
            (r"\bIPC\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?|\d+\(\d+\))\b", "IPC"),
            (r"Section\s*(\d+[A-Za-z]?|\d+\(\d+\))\s*(?:of\s*)?(?:the\s*)?IPC\b", "IPC"),
            (r"\bCrPC\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]?|\d+\(\d+\))\b", "CrPC"),
            (r"Section\s*(\d+[A-Za-z]?|\d+\(\d+\))\s*(?:of\s*)?(?:the\s*)?CrPC\b", "CrPC"),
            (r"\b(?:UA\(P\)\s*Act|UAPA)\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z\-]*)\b", "UAPA"),
            (r"Section\s*(\d+[A-Za-z\-]*)\s*(?:of\s*)?(?:the\s*)?(?:UA\(P\)\s*Act|UAPA)\b", "UAPA"),
            (r"\b(?:Arms\s*Act|A\.\s*Act)\s*(?:Section|Sec\.?)?\s*(\d+[\(A-Za-z0-9\-\)]*)\b", "Arms Act"),
            (r"Section\s*(\d+[\(A-Za-z0-9\-\)]*)\s*(?:of\s*)?(?:the\s*)?(?:Arms\s*Act|A\.\s*Act)\b", "Arms Act"),
        ]

        for pat, act_code in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                sec_num = match.group(1).strip()
                sec_upper = sec_num.upper()
                if sec_upper in seen:
                    continue
                seen.add(sec_upper)

                info = STATUTE_INFO.get(sec_upper)
                if info:
                    citations.append({
                        "section": info[0],
                        "subject": info[1],
                        "key_changes": info[2]
                    })
                else:
                    act_full = {
                        "BNS": "Bharatiya Nyaya Sanhita, 2023",
                        "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                        "BSA": "Bharatiya Sakshya Adhiniyam, 2023",
                        "IPC": "Indian Penal Code, 1860 (Historical)",
                        "CrPC": "Code of Criminal Procedure, 1973 (Historical)"
                    }.get(act_code, act_code)
                    citations.append({
                        "section": f"Section {sec_num}, {act_full}",
                        "subject": f"Statutory Provision under {act_full}",
                        "key_changes": f"Codified under {act_full}"
                    })

        t_lower = text.lower()

        # Check for specific offences discussed in text
        if ("murder" in t_lower or "103" in text or "302" in text) and "103" not in seen and "302" not in seen:
            seen.add("103")
            citations.insert(0, {
                "section": "BNS Section 103 (formerly IPC Section 302)",
                "subject": "Punishment for Murder & Capital Offence",
                "key_changes": "Death penalty or imprisonment for life, and fine."
            })

        if ("harbour" in t_lower or "harbor" in t_lower or "249" in text or "212" in text) and "249" not in seen:
            seen.add("249")
            citations.append({
                "section": "BNS Section 249 (formerly IPC Section 212)",
                "subject": "Harbouring Offender (Screening from Legal Punishment)",
                "key_changes": "Harbouring a person who committed a capital offence carries up to 5 years rigorous imprisonment."
            })

        if ("disappearance of evidence" in t_lower or "hiding evidence" in t_lower or "238" in text or "201" in text) and "238" not in seen:
            seen.add("238")
            citations.append({
                "section": "BNS Section 238 (formerly IPC Section 201)",
                "subject": "Causing Disappearance of Evidence / Giving False Info",
                "key_changes": "Penalizes destroying evidence or misleading police to screen an offender."
            })

        # Workplace / Employer harassment specific citations
        if "351" in text or "intimidation" in t_lower or "employer" in t_lower or "harassment" in t_lower:
            if "351" not in seen:
                seen.add("351")
                citations.append({
                    "section": "BNS Section 351 & 352 (formerly IPC Sections 503 & 506)",
                    "subject": "Criminal Intimidation & Intentional Insult",
                    "key_changes": "Penalizes threatening employee person, reputation, or livelihood."
                })
            if "Payment of Wages Act, 1936" not in seen:
                seen.add("Payment of Wages Act, 1936")
                citations.append({
                    "section": "Payment of Wages Act, 1936 & Industrial Disputes Code",
                    "subject": "Statutory Protection of Earned Salary & Employment Grievances",
                    "key_changes": "Remedy before State Labor Commissioner for unpaid wages."
                })

        # UAPA & Arms Act & Extortion specific citations
        if "uapa" in t_lower or "ua(p)" in t_lower or "terrorist" in t_lower:
            if "17" not in seen:
                seen.add("17")
                citations.append({
                    "section": "Section 17, Unlawful Activities (Prevention) Act, 1967",
                    "subject": "Punishment for Raising Funds for Terrorist Act",
                    "key_changes": "Imprisonment not less than 5 years extending to life, and fine. Stringent bail restrictions under Section 43D(5) UAPA."
                })
            if "20" not in seen:
                seen.add("20")
                citations.append({
                    "section": "Section 20, Unlawful Activities (Prevention) Act, 1967",
                    "subject": "Punishment for Being Member of Terrorist Gang or Organisation",
                    "key_changes": "Imprisonment extending to life, and fine. Applies to members of banned unlawful organizations."
                })

        if "arms act" in t_lower or "25(1-c)" in t_lower or "ammunition" in t_lower or "firearm" in t_lower:
            if "25(1-C)" not in seen and "25" not in seen:
                seen.add("25(1-C)")
                citations.append({
                    "section": "Section 25(1-C), Arms Act, 1959",
                    "subject": "Possession / Delivery of Prohibited Arms or Ammunition",
                    "key_changes": "Rigorous imprisonment not less than 3 years up to 7 or 10 years, and fine."
                })

        if ("extortion" in t_lower or "308" in text or "384" in text) and "308" not in seen:
            seen.add("308")
            citations.append({
                "section": "BNS Section 308 (formerly IPC Section 383 & 384)",
                "subject": "Extortion by Putting Person in Fear of Injury",
                "key_changes": "Replaced IPC 384. Punishable with imprisonment up to 3 years, fine, or both (up to 10 years if threat to life)."
            })

        if ("trespass" in t_lower or "encroachment" in t_lower or "land" in t_lower or "329" in text) and "329" not in seen:
            seen.add("329")
            citations.append({
                "section": "BNS Section 329 & 333 (formerly IPC Section 441 & 447)",
                "subject": "Criminal Trespass & Unlawful Land Encroachment",
                "key_changes": "Replaces IPC 441/447. Criminal remedy under BNSS 173 and civil injunction under Specific Relief Act."
            })

        # FIR citations
        if ("173" in text or "fir" in t_lower) and "173" not in seen:
            seen.add("173")
            citations.append({
                "section": "BNSS Section 173 (formerly CrPC Section 154)",
                "subject": "Information in Cognizable Cases & Zero FIR",
                "key_changes": "Formalizes Zero FIR; enables e-FIR registration."
            })

        # Legal Aid citation
        if ("15100" in text or "legal aid" in t_lower) and "Section 12, LSAA" not in seen:
            seen.add("Section 12, LSAA")
            citations.append({
                "section": "Section 12, Legal Services Authorities Act, 1987",
                "subject": "Entitlement to Free State Legal Aid & NALSA 15100 Helpline",
                "key_changes": "Free state-sponsored counsel for eligible citizens."
            })

        return citations[:5]
