"""Production-Grade Guardrails Engine for Nyayavarta Legal AI.

Implements three critical defensive layers:
1. Prompt Injection & Jailbreak Defense (Input Sanitization)
2. Data Leak Prevention (DLP / PII Redaction: Aadhaar, PAN, Phone, Banking, Email)
3. Harmful & Illegal Query Defense (Refusal of criminal conspiracy / illicit assistance)
"""

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("guardrails")

# -----------------------------------------------------------------------------
# 1. PII Regular Expressions for Indian Citizens (DLP Compliance)
# -----------------------------------------------------------------------------
PII_PATTERNS = [
    # Indian Aadhaar Card (12 digits, optional space/dash)
    (
        "AADHAAR",
        re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        "[AADHAAR_REDACTED]"
    ),
    # Indian Permanent Account Number (PAN)
    (
        "PAN",
        re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
        "[PAN_REDACTED]"
    ),
    # Indian Mobile Phone Number (+91 or 10-digit starting with 6-9)
    (
        "PHONE",
        re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{4}[\s\-]?\d{5}\b"),
        "[PHONE_REDACTED]"
    ),
    # Credit / Debit Card Numbers (16 digits)
    (
        "PAYMENT_CARD",
        re.compile(r"\b(?:\d{4}[\-\s]?){3}\d{4}\b"),
        "[CARD_REDACTED]"
    ),
    # Email Addresses
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL_REDACTED]"
    ),
]

# -----------------------------------------------------------------------------
# 2. Prompt Injection & Jailbreak Heuristics
# -----------------------------------------------------------------------------
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|former)\s+(instructions|directives|prompts|rules)",
    r"disregard\s+(all\s+)?(previous|prior|above|former)\s+(instructions|directives|prompts|rules)",
    r"you\s+are\s+now\s+(in\s+)?(dan|jailbreak|developer|god|unrestricted|unfiltered)\s+mode",
    r"bypass\s+(all\s+)?(ethical|legal|safety|system|content)\s+(guidelines|restrictions|rules|filters)",
    r"(reveal|show|print|output|display|share)\s+(me\s+)?(your\s+)?(system\s+prompt|initial\s+prompt|hidden\s+instructions|developer\s+prompt)",
    r"system\s*:\s*you\s+are\s+",
    r"<\s*script\b",
    r"DROP\s+TABLE|DELETE\s+FROM|UNION\s+SELECT",
    r"base64\s+(decode|encoded)",
    r"pretend\s+you\s+have\s+no\s+(rules|restrictions|limits)",
    r"act\s+as\s+(an\s+unfiltered|an\s+unrestricted|a\s+jailbroken)\s+ai",
]

COMPILED_INJECTIONS = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]

# -----------------------------------------------------------------------------
# 3. Harmful & Illicit Intent Patterns
# -----------------------------------------------------------------------------
HARMFUL_INTENT_PATTERNS = [
    r"how\s+to\s+(forge|counterfeit|fake|falsify)\s+(a\s+|an\s+)?(stamp\s+paper|signature|property\s+deed|deed|will|currency|document|affidavit|court\s+order)",
    r"how\s+to\s+(bribe|pay\s+bribe\s+to|pay\s+off|corrupt)\s+(a\s+|an\s+)?(police|magistrate|judge|inspector|officer|official)",
    r"how\s+to\s+(murder|kill|poison|assassinate|harm)\s+",
    r"how\s+to\s+(manufacture|smuggle|procure|traffic)\s+(illegal\s+arms|prohibited\s+weapons|narcotics|drugs|heroin|contraband)",
    r"how\s+to\s+(evade|escape|run\s+away\s+from|flee)\s+(police\s+arrest|warrant|custody|investigation)",
    r"how\s+to\s+(hack|steal\s+money\s+from|phish|defraud)\s+(a\s+|an\s+)?(bank\s+account|upi|atm|citizen)",
]

COMPILED_HARMFUL = [re.compile(p, re.IGNORECASE) for p in HARMFUL_INTENT_PATTERNS]


class GuardrailsResult:
    def __init__(
        self,
        is_safe: bool,
        sanitized_text: str,
        violation_type: str = "NONE",
        reason: str = "",
        redactions: List[str] = None
    ):
        self.is_safe = is_safe
        self.sanitized_text = sanitized_text
        self.violation_type = violation_type  # "NONE" | "PROMPT_INJECTION" | "HARMFUL_INTENT" | "PII_REDACTED"
        self.reason = reason
        self.redactions = redactions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "sanitized_text": self.sanitized_text,
            "violation_type": self.violation_type,
            "reason": self.reason,
            "redactions": self.redactions,
        }


class GuardrailsEngine:
    """Enterprise safety and privacy guardrails for legal queries."""

    @classmethod
    def sanitize_input(cls, text: str) -> GuardrailsResult:
        """Sanitizes user input: checks prompt injection, blocks illicit intent, and redacts PII."""
        if not text or not text.strip():
            return GuardrailsResult(is_safe=True, sanitized_text=text)

        # Step 1: Detect Prompt Injection / Jailbreaks
        for pattern in COMPILED_INJECTIONS:
            if pattern.search(text):
                logger.warning(f"Guardrail triggered: Prompt injection detected matching '{pattern.pattern}'")
                return GuardrailsResult(
                    is_safe=False,
                    sanitized_text="",
                    violation_type="PROMPT_INJECTION",
                    reason="System Prompt Exfiltration or Jailbreak instruction detected. Request denied for safety."
                )

        # Step 2: Detect Harmful / Criminal Intent
        for pattern in COMPILED_HARMFUL:
            if pattern.search(text):
                logger.warning(f"Guardrail triggered: Harmful intent detected matching '{pattern.pattern}'")
                return GuardrailsResult(
                    is_safe=False,
                    sanitized_text="",
                    violation_type="HARMFUL_INTENT",
                    reason="Assistance with the commission or concealment of criminal acts violates institutional guidelines and Bharatiya Nyaya Sanhita provisions."
                )

        # Step 3: PII Masking / DLP Sanitization
        sanitized = text
        redacted_labels = []

        for label, pattern, replacement in PII_PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                redacted_labels.append(f"{label} ({len(matches)} found)")
                sanitized = pattern.sub(replacement, sanitized)

        if redacted_labels:
            logger.info(f"DLP Guardrail redacted sensitive citizen PII: {', '.join(redacted_labels)}")

        return GuardrailsResult(
            is_safe=True,
            sanitized_text=sanitized,
            violation_type="PII_REDACTED" if redacted_labels else "NONE",
            reason=f"Sanitized: {', '.join(redacted_labels)}" if redacted_labels else "",
            redactions=redacted_labels
        )

    @classmethod
    def get_security_refusal_response(cls, violation_type: str, language: str = "en") -> str:
        """Generates standard constitutional refusal for blocked queries."""
        if violation_type == "PROMPT_INJECTION":
            return (
                "### Security & Integrity Notice\n\n"
                "Nyayavarta operates strictly as a legal literacy and citizen assistance assistant bound by ethical guidelines and statutory law. "
                "Adversarial prompts, system prompt override commands, or jailbreak attempts are blocked to ensure system integrity and citizen security."
            )
        elif violation_type == "HARMFUL_INTENT":
            return (
                "### Legal & Ethical Boundary Notice\n\n"
                "Nyayavarta is an artificial intelligence legal guide built to empower Indian citizens with knowledge of their constitutional rights, procedural safeguards, and access to free legal aid.\n\n"
                "- **Statutory Restriction**: We cannot provide instructions, assistance, or strategies for committing, facilitating, or concealing criminal offences, forgery, or corruption under the Bharatiya Nyaya Sanhita (BNS, 2023) or Prevention of Corruption Act, 1988.\n"
                "- **Legal Recourse**: If you are experiencing coercion, false accusations, or procedural distress, you have the right to seek fair inquiry under Section 173 BNSS and contact the National Legal Aid Helpline (**15100**) for free counsel."
            )
        return "Your query could not be processed due to safety constraints."
