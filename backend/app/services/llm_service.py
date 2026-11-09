"""LLM Service for Nyayavarta using Google Gemini API.

Orchestrates legal prompt engineering, profile-tailored reasoning,
old-to-new Indian law mapping (IPC->BNS, CrPC->BNSS, Evidence Act->BSA),
citation extraction, and legal aid routing (NALSA / DLSA / 15100).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.models.schemas import UserProfile

logger = logging.getLogger(__name__)

# System prompt defining Nyayavarta legal AI persona
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

5. ACCURACY & DISCLAIMER:
   - Maintain strict factual correctness with respect to Indian law.
   - Add a brief, respectful legal disclaimer that this provides legal information and aid routing, not a substitute for formal attorney-client counsel.
"""


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
    """Orchestrates LLM requests via Google Gemini API with fallback capabilities."""

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
                logger.info(f"Initialized Google GenAI client with model: {self.settings.GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")
                self.client = None

    async def generate_legal_response(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        user_profile: UserProfile = UserProfile.GENERAL,
    ) -> Dict[str, Any]:
        """Generate a profile-tailored legal response with citations and old/new law mappings."""
        # 1. Format retrieved RAG context
        context_blocks = []
        citations: List[Dict[str, str]] = []

        if retrieved_context:
            for item in retrieved_context:
                text = item.get("text", "")
                meta = item.get("metadata", {})
                context_blocks.append(f"--- Document [Score: {item.get('score', 0):.2f}] ---\n{text}")

                # Extract citations from metadata
                if meta.get("old_law") or meta.get("new_law"):
                    citations.append({
                        "section": f"{meta.get('new_law', '')} (formerly {meta.get('old_law', '')})".strip(),
                        "subject": meta.get("subject", "Legal Provision"),
                        "key_changes": meta.get("key_changes", "")
                    })
                elif meta.get("filename"):
                    citations.append({
                        "section": f"Uploaded Document: {meta.get('filename')}",
                        "subject": f"Page {meta.get('page', 1)} reference",
                        "key_changes": "User provided document"
                    })
            context_str = "\n\n".join(context_blocks)
        else:
            context_str = (
                "[NOTICE]: No specific documents matching the query were found in the local knowledge base.\n"
                "Please provide a comprehensive response using standard Indian statutes (BNS, BNSS, BSA, Constitution of India), "
                "noting that specific localized case files were not available."
            )

        # 2. Build User Prompt
        profile_guide = get_profile_instructions(user_profile)
        user_prompt = f"""{profile_guide}

RETRIEVED LEGAL CONTEXT FROM KNOWLEDGE BASE:
{context_str}

USER QUERY:
"{query}"

Please answer the query thoroughly in English following the System Directives:
1. Explain the legal position clearly for this {user_profile.value} user profile.
2. Explicitly map old law sections (IPC/CrPC/Evidence Act) to new law sections (BNS/BNSS/BSA).
3. Provide step-by-step actionable advice and legal aid contact info (NALSA DLSA Helpline 15100).
4. List the primary statutory citations at the end.
"""

        # 3. Call Gemini API
        english_text = ""
        if self.client:
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=self.settings.GEMINI_MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    )
                )
                if response and response.text:
                    english_text = response.text.strip()
            except Exception as e:
                logger.error(f"Gemini API call failed ({e}). Falling back to internal legal generator.")

        # 4. Fallback generator if API call didn't return text
        if not english_text:
            english_text = self._generate_fallback_response(query, retrieved_context, user_profile)

        # 5. Deduplicate and ensure citations
        if not citations:
            citations = self._extract_citations_from_text(english_text)

        return {
            "english_response": english_text,
            "citations": citations,
            "user_profile": user_profile.value
        }

    async def translate_with_llm(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text accurately between English and Indian languages using Gemini."""
        if not text or not text.strip() or source_lang == target_lang:
            return text

        if not self.client:
            return text

        lang_names = {
            "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
            "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
            "pa": "Punjabi", "or": "Odia", "ur": "Urdu", "en": "English",
            "as": "Assamese", "sa": "Sanskrit"
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        prompt = (
            f"You are a professional multilingual translator specializing in Indian legal translation.\n"
            f"Translate the following text accurately from {src_name} to {tgt_name}. "
            f"Preserve legal section numbers (BNS, IPC, BNSS, etc.), formatting, and bullet points. "
            f"Output ONLY the translated text without commentary or prefixes.\n\n"
            f"Text to translate:\n{text}"
        )

        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"LLM translation failed ({e}). Returning original text.")

        return text

    def _generate_fallback_response(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        user_profile: UserProfile
    ) -> str:
        """Deterministic legal response generator when external API is unreachable."""
        q_lower = query.lower()

        # Identify subject (supports English and Hindi keywords)
        if (
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
        elif (
            "cheating" in q_lower or "fraud" in q_lower or "420" in q_lower or "318" in q_lower
            or "धोखाधड़ी" in q_lower or "ठगी" in q_lower
        ):
            old_law = "Section 420 of the Indian Penal Code (IPC), 1860"
            new_law = "Section 318 of the Bharatiya Nyaya Sanhita (BNS), 2023"
            subject = "Cheating and Dishonestly Inducing Delivery of Property"
            details = (
                "Cheating and dishonest inducement of property is codified under Section 318 of BNS 2023. "
                "Punishment includes imprisonment for a term which may extend to seven years, and fine."
            )
        elif (
            "fir" in q_lower or "police" in q_lower or "154" in q_lower or "173" in q_lower
            or "एफआईआर" in query or "जीरो" in query or "दर्ज" in query or "थाना" in query
        ):
            old_law = "Section 154 of the Code of Criminal Procedure (CrPC), 1973"
            new_law = "Section 173 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
            subject = "First Information Report (FIR) & Zero FIR Legality"
            details = (
                "Under Section 173 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 (replacing Section 154 CrPC), "
                "the concept of Zero FIR is formally codified into statute. Any citizen can lodge an FIR at ANY police station "
                "regardless of territorial jurisdiction. The station must immediately record the information, provide a free copy to "
                "the complainant, and transfer the case to the competent jurisdictional police station. "
                "Furthermore, Section 173(1) BNSS allows information to be submitted electronically (e-FIR), which must be signed within three days."
            )
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
        else:
            old_law = "Relevant sections of the Indian Penal Code (IPC) / CrPC"
            new_law = "Bharatiya Nyaya Sanhita (BNS) / BNSS, 2023"
            subject = "General Legal Assessment"
            details = (
                "Under India's modern criminal legal framework (BNS, BNSS, and BSA effective July 1, 2024), "
                "citizens are protected against unlawful acts and have full recourse through jurisdictional courts and legal aid authorities."
            )

        profile_intro = {
            UserProfile.STUDENT: "Here is an academic analysis of the applicable Indian statutory framework:",
            UserProfile.PROFESSIONAL: "Regarding the legal compliance and procedural provisions under Indian law:",
            UserProfile.SENIOR_CITIZEN: "We are here to support you. Here is a clear and simple explanation of your rights:",
            UserProfile.GENERAL: "Here is clear guidance on how Indian law protects you and what steps you can take:"
        }.get(user_profile, "Here is the relevant legal guidance:")

        response = f"""{profile_intro}

### 1. Legal Provision & Transition
- **Old Law Reference**: {old_law}
- **New Law Reference**: {new_law}
- **Subject**: {subject}

{details}

### 2. Immediate Recommended Steps
1. Document all evidence, incident details, messages, or relevant records.
2. If this involves a cognizable offense, approach your nearest police station to lodge an FIR under Section 173 BNSS (Zero FIR is fully legal and mandatory to accept).
3. You can also file online grievances via official state police citizen portals or National Cyber Crime Reporting Portal.

### 3. Free Legal Aid & Helplines
- **National Legal Aid Helpline**: Call **15100** (Toll-Free, 24x7) for free legal aid provided by NALSA / DLSA.
- **Emergency Services**: Dial **112**.
- **Women Helpline**: Dial **1091**.
- **Cyber Crime Portal**: Call **1930** or report on cybercrime.gov.in.

*Disclaimer: Nyayavarta provides legal awareness and aid routing. For formal representation in a court of law, please consult an empanelled legal aid advocate or attorney.*
"""
        return response

    def _extract_citations_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract statutory citations mentioned in generated text."""
        citations = []
        # Check BNS / IPC mentions
        patterns = [
            (r"(?:Section|Sec\.)?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?BNS", "Bharatiya Nyaya Sanhita, 2023"),
            (r"(?:Section|Sec\.)?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023"),
            (r"(?:Section|Sec\.)?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?BSA", "Bharatiya Sakshya Adhiniyam, 2023"),
            (r"(?:Section|Sec\.)?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?IPC", "Indian Penal Code, 1860 (Historical)"),
            (r"(?:Section|Sec\.)?\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?CrPC", "Code of Criminal Procedure, 1973 (Historical)"),
        ]
        seen = set()
        for pat, act in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                sec_num = match.group(1)
                entry_key = f"{sec_num}-{act}"
                if entry_key not in seen:
                    seen.add(entry_key)
                    citations.append({
                        "section": f"Section {sec_num}",
                        "subject": f"Statutory Provision under {act}",
                        "key_changes": f"Governed under {act}"
                    })

        # Add context-driven citations if empty
        if not citations:
            t_lower = text.lower()
            if "173" in text or "fir" in t_lower or "एफआईआर" in text:
                citations.append({
                    "section": "Section 173, BNSS 2023",
                    "subject": "Information in cognizable cases & Zero FIR (replaces Section 154 CrPC)",
                    "key_changes": "Formalizes Zero FIR; enables e-FIR registration."
                })
            if "103" in text or "302" in text or "murder" in t_lower:
                citations.append({
                    "section": "Section 103, BNS 2023",
                    "subject": "Punishment for Murder (replaces Section 302 IPC)",
                    "key_changes": "Sub-clause (2) defines group mob lynching."
                })
            if "318" in text or "420" in text or "cheating" in t_lower:
                citations.append({
                    "section": "Section 318, BNS 2023",
                    "subject": "Cheating & Dishonest Inducement (replaces Section 420 IPC)",
                    "key_changes": "Consolidates cheating penalties up to seven years."
                })

        return citations[:5]
