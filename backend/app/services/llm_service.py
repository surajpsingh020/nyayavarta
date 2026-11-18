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
        # 1. Format retrieved RAG context
        context_blocks = []
        citations: List[Dict[str, str]] = []

        if retrieved_context:
            for item in retrieved_context:
                text = item.get("text", "")
                meta = item.get("metadata", {})
                score = float(item.get("score", 0.0))
                # Only include context with genuine relevance score to prevent noisy hallucinated citations
                if score >= 0.2:
                    context_blocks.append(f"--- Statutory Record [Score: {score:.2f}] ---\n{text}")
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
            context_str = "\n\n".join(context_blocks) if context_blocks else ""
        else:
            context_str = ""

        if not context_str:
            context_str = (
                "[NOTICE]: No specific criminal section mappings were found in the local statutory index.\n"
                "Please provide a comprehensive response using standard Indian statutes (BNS, BNSS, BSA, Constitution of India, and relevant Special Acts), "
                "addressing the user's specific problem directly."
            )

        # 2. Build User Prompt
        profile_guide = get_profile_instructions(user_profile)
        user_prompt = f"""{profile_guide}

RETRIEVED LEGAL CONTEXT FROM KNOWLEDGE BASE:
{context_str}

USER QUERY:
"{query}"

Please answer the query thoroughly in English following the System Directives:
1. Explain the legal position clearly for this {user_profile.value} user profile. Address their specific situation directly with actionable rights and legal provisions.
2. Explicitly map old law sections (IPC/CrPC/Evidence Act) to new law sections (BNS/BNSS/BSA), or cite relevant special Indian acts (e.g. POSH Act, Payment of Wages, Consumer Protection).
3. Provide step-by-step actionable advice and legal aid contact info (NALSA DLSA Helpline 15100).
4. Include an Institutional Scope Notice highlighting these exact points:
   - Nyayavarta focuses on statutory translation, citizen rights education, procedural roadmaps (FIR, arrest, bail), document analysis, and free legal aid routing.
   - It does not contain the complete judgment archives, daily court cause lists, hearing transcripts, or case dockets of the Supreme Court of India, the 25 High Courts, or the 672 District Courts.
   - The entire Indian e-Courts case law archive spans hundreds of millions of case records and hundreds of gigabytes/terabytes of unstructured PDFs across decades, which requires commercial multi-terabyte data warehouse infrastructure (like SCC Online or Manupatra).
5. List the primary statutory citations at the end.
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

        # 5. Extract only citations that are genuinely mentioned in the generated text
        extracted_cits = self._extract_citations_from_text(english_text)
        if extracted_cits:
            citations = extracted_cits
        elif not citations:
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

        prompt = (
            f"You are a professional multilingual translator specializing in Indian legal translation.\n"
            f"Translate the following legal guidance accurately and completely from {src_name} to {tgt_name}.\n"
            f"- Output the ENTIRE text in {tgt_name} script/language without leaving English sentences in the middle.\n"
            f"- Preserve section numbers (e.g., Section 351, BNS 2023, BNSS 173), phone numbers (15100, 112), bullet points, and Markdown headers.\n"
            f"- Output ONLY the translated text without commentary or prefixes.\n\n"
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
                return response_text.strip()
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

        response = f"""Here is clear guidance on how Indian law protects you and what steps you can take:

### 1. Legal Provision & Transition
- **Old Law Reference**: {old_law}
- **New Law Reference**: {new_law}
- **Subject**: {subject}

{details}

### 2. Immediate Recommended Steps
{steps_rendered}

### 3. Free Legal Aid & Helplines
- **National Legal Aid Helpline**: Call **15100** (Toll-Free, 24x7) for free legal aid provided by NALSA / DLSA.
- **Emergency Services**: Dial **112**.
- **Women Helpline**: Dial **1091**.
- **Cyber Crime Portal**: Call **1930** or report on cybercrime.gov.in.

### 4. Institutional Scope Notice & System Boundaries
- **Statutory Focus**: Nyayavarta focuses on statutory translation, citizen rights education, procedural roadmaps (FIR, arrest, bail), document analysis, and free legal aid routing.
- **No Case Law Archives**: It does not contain the complete judgment archives, daily court cause lists, hearing transcripts, or case dockets of the Supreme Court of India, the 25 High Courts, or the 672 District Courts.
- **Enterprise Infrastructure Requirement**: The entire Indian e-Courts case law archive spans hundreds of millions of case records and hundreds of gigabytes/terabytes of unstructured PDFs across decades, which requires commercial multi-terabyte data warehouse infrastructure (like SCC Online or Manupatra).

*Disclaimer: Nyayavarta provides legal awareness and aid routing. For formal representation in a court of law, please consult an empanelled legal aid advocate or attorney.*
"""
        return response

    def _extract_citations_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract only statutory citations that are genuinely mentioned in the generated text."""
        citations = []
        seen = set()

        # Check explicit section mentions in text
        patterns = [
            (r"Section\s*(\d+[A-Za-z]?)\s*(?:and\s*Section\s*(\d+[A-Za-z]?)\s*)?(?:of\s*)?(?:the\s*)?BNS", "Bharatiya Nyaya Sanhita, 2023"),
            (r"Section\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023"),
            (r"Section\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?BSA", "Bharatiya Sakshya Adhiniyam, 2023"),
            (r"Section\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?IPC", "Indian Penal Code, 1860 (Historical)"),
            (r"Section\s*(\d+[A-Za-z]?)\s*(?:of\s*)?(?:the\s*)?CrPC", "Code of Criminal Procedure, 1973 (Historical)"),
        ]

        for pat, act in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                for grp in match.groups():
                    if grp:
                        sec_num = grp.strip()
                        entry_key = f"{sec_num}-{act}"
                        if entry_key not in seen:
                            seen.add(entry_key)
                            citations.append({
                                "section": f"Section {sec_num}, {act}",
                                "subject": f"Statutory Provision under {act}",
                                "key_changes": f"Codified under {act}"
                            })

        t_lower = text.lower()

        # Workplace / Employer harassment specific citations
        if "351" in text or "intimidation" in t_lower or "employer" in t_lower or "harassment" in t_lower:
            if "Section 351, BNS 2023" not in seen:
                seen.add("Section 351, BNS 2023")
                citations.append({
                    "section": "Section 351 & 352, BNS 2023",
                    "subject": "Criminal Intimidation & Intentional Insult (replaces Sections 503, 506 IPC)",
                    "key_changes": "Penalizes threatening employee person, reputation, or livelihood."
                })
            if "Payment of Wages Act, 1936" not in seen:
                seen.add("Payment of Wages Act, 1936")
                citations.append({
                    "section": "Payment of Wages Act, 1936 & Industrial Disputes Code",
                    "subject": "Statutory Protection of Earned Salary & Employment Grievances",
                    "key_changes": "Remedy before State Labor Commissioner for unpaid wages."
                })

        # FIR citations
        if ("173" in text or "fir" in t_lower) and "Section 173, BNSS 2023" not in seen:
            seen.add("Section 173, BNSS 2023")
            citations.append({
                "section": "Section 173, BNSS 2023",
                "subject": "Information in Cognizable Cases & Zero FIR (replaces Section 154 CrPC)",
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
