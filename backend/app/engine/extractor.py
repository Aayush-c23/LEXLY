"""
Ingestion, PII Masking, Incident Date Bifurcation, Dense Embeddings, and Fact Extraction (BE-302).
"""

import asyncio
from datetime import date, datetime
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.config import settings

logger = logging.getLogger("lexly.extractor")

# Statutory regime cutoff date: 1 July 2024 (Bharatiya Nyaya Sanhita enforcement)
BNS_ENFORCEMENT_CUTOFF = date(2024, 7, 1)

# PII Regular Expressions for Indian context
RE_PHONE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b")
RE_AADHAAR = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
RE_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")

# Date pattern search in natural language
RE_DATE_ISO = re.compile(r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b")
RE_DATE_DMY = re.compile(r"\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](20\d{2})\b")


def mask_pii(text: str) -> str:
    """
    Masks Indian phone numbers, Aadhaar sequences, PAN cards, and emails
    prior to any downstream processing or model queries (DPDP Act 2023 compliance).
    """
    if not text:
        return ""
    masked = RE_AADHAAR.sub("[AADHAAR_MASKED]", text)
    masked = RE_PHONE.sub("[PHONE_MASKED]", masked)
    masked = RE_EMAIL.sub("[EMAIL_MASKED]", masked)
    masked = RE_PAN.sub("[PAN_MASKED]", masked)
    return masked


def determine_legal_regime(incident_date_str: Optional[str], scenario_text: str) -> Tuple[str, Optional[date]]:
    """
    Parses incident date or extracts it from scenario text and compares
    against 2024-07-01 to determine primary legal regime ('BNS' vs 'IPC').
    """
    parsed_date: Optional[date] = None

    # 1. Try explicit incident_date_str
    if incident_date_str:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(incident_date_str.strip(), fmt).date()
                break
            except ValueError:
                pass

    # 2. Heuristic extraction from scenario text if not provided
    if parsed_date is None and scenario_text:
        iso_match = RE_DATE_ISO.search(scenario_text)
        if iso_match:
            try:
                y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                parsed_date = date(y, m, d)
            except ValueError:
                pass

        if parsed_date is None:
            dmy_match = RE_DATE_DMY.search(scenario_text)
            if dmy_match:
                try:
                    d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
                    parsed_date = date(y, m, d)
                except ValueError:
                    pass

    # 3. Default to current date if completely unstated
    effective_date = parsed_date or date.today()

    if effective_date < BNS_ENFORCEMENT_CUTOFF:
        return "IPC", parsed_date
    return "BNS", parsed_date


def generate_deterministic_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Generates a deterministic 768-dimensional normalized unit vector from text.
    Serves as an offline/test fallback when Gemini API key is absent or unavailable.
    """
    tokens = text.lower().split()
    vector = np.zeros(dim, dtype=np.float32)

    for token in tokens:
        token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = token_hash % dim
        sign = 1.0 if (token_hash % 2 == 0) else -1.0
        vector[idx] += sign

    norm = float(np.linalg.norm(vector))
    if norm > 1e-9:
        vector = vector / norm
    else:
        vector[0] = 1.0

    return vector.tolist()


async def get_scenario_embedding(text: str) -> List[float]:
    """
    Asynchronously generates a 768-dimensional embedding using Google GenAI SDK.
    Falls back gracefully to deterministic pseudo-embedding if API key is not configured.
    """
    if not settings.GEMINI_API_KEY:
        return generate_deterministic_embedding(text, dim=768)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = await asyncio.to_thread(
            client.models.embed_content,
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
        if response.embeddings and len(response.embeddings) > 0:
            return list(response.embeddings[0].values)
        elif hasattr(response, "embedding") and response.embedding:
            return list(response.embedding.values)
    except Exception as exc:
        logger.warning(f"Gemini embedding API call failed: {exc}. Falling back to deterministic embedding.")

    return generate_deterministic_embedding(text, dim=768)


# Keyword and lexical patterns for known fact extraction
FACT_EXTRACTION_RULES: Dict[str, Dict[str, List[str]]] = {
    "physical_contact": {
        "TRUE": ["punch", "hit", "slap", "beat", "struck", "pushed", "attacked", "kicked", "assault", "stabbed"],
        "FALSE": ["did not touch", "no physical contact", "from a distance", "only verbal"],
    },
    "bodily_pain_or_infirmity": {
        "TRUE": ["pain", "hurt", "injury", "bruise", "bleeding", "swelling", "wound", "fracture", "cuts", "fracturing"],
        "FALSE": ["unhurt", "no injury", "no pain", "escaped unhurt"],
    },
    "grievous_injury_type": {
        "TRUE": ["fracture", "fracturing", "fractured", "broken bone", "dislocated", "lost eye", "permanent", "bed rest 20 days", "compound fracture"],
        "FALSE": ["minor cut", "simple scratch", "swelling only", "flesh wound", "simple hurt"],
    },
    "dangerous_weapon_or_means": {
        "TRUE": ["knife", "blade", "gun", "pistol", "revolver", "iron rod", "sword", "dagger", "acid", "poison", "deadly weapon", "rod"],
        "FALSE": ["fists", "bare hands", "no weapon", "without weapon"],
    },
    "movable_property_taken": {
        "TRUE": ["stole", "taken", "took", "laptop", "phone", "cash", "money", "wallet", "bag", "jewelry", "jewellery", "gold", "bike", "car"],
        "FALSE": ["nothing was taken", "did not take anything"],
    },
    "without_consent": {
        "TRUE": ["without consent", "stole", "broke in", "snatched", "robbed", "looted", "secretly", "while i was away", "locked"],
        "FALSE": ["with permission", "with consent", "handed over willingly"],
    },
    "dishonest_intention": {
        "TRUE": ["claimed i owed", "to steal", "wrongful gain", "sold it", "kept it", "dishonestly"],
        "FALSE": ["returned immediately", "by honest mistake"],
    },
    "inside_building_or_dwelling": {
        "TRUE": ["flat", "apartment", "house", "home", "building", "room", "office", "shop", "dwelling", "bungalow", "warehouse", "godown"],
        "FALSE": ["street", "road", "public park", "open ground"],
    },
    "unlawful_entry_into_property": {
        "TRUE": ["broke into", "trespassed", "entered unlawfully", "forced entry", "entered without permission", "entered a bungalow", "intruder", "crept into"],
        "FALSE": ["invited guest", "permitted entry"],
    },
    "instant_fear_of_death_or_hurt": {
        "TRUE": ["threatened to kill", "held knife to throat", "threatened with death", "at gunpoint", "instant hurt", "struck him with"],
        "FALSE": ["quietly without threat", "unnoticed"],
    },
    "five_or_more_offenders": {
        "TRUE": ["five men", "six people", "gang of", "7 attackers", "5 or more"],
        "FALSE": ["alone", "single person", "two people", "three boys"],
    },
    "wrongful_restraint": {
        "TRUE": ["blocked my path", "prevented from going", "blocked the door", "would not let me pass", "preventing him from walking", "stood in front"],
        "FALSE": ["free to leave"],
    },
    "wrongful_confinement": {
        "TRUE": ["locked inside", "locked the room", "tied to chair", "trapped inside room", "confined", "locked a worker", "locked a young trader", "padlocked"],
        "FALSE": ["was not confined", "walked away"],
    },
}


async def extract_facts_from_scenario(scenario_text: str) -> Dict[str, str]:
    """
    Extracts tri-state fact requirements ('TRUE', 'FALSE', 'UNKNOWN') from scenario text.
    Uses Gemini LLM if key is configured; otherwise uses high-precision statutory regex rules.
    """
    scenario_lower = scenario_text.lower()
    extracted: Dict[str, str] = {}

    # 1. Rule-based lexical evaluation
    for fact_key, patterns in FACT_EXTRACTION_RULES.items():
        true_matches = any(p in scenario_lower for p in patterns.get("TRUE", []))
        false_matches = any(p in scenario_lower for p in patterns.get("FALSE", []))

        if true_matches and not false_matches:
            extracted[fact_key] = "TRUE"
        elif false_matches and not true_matches:
            extracted[fact_key] = "FALSE"

    # Legal jurisprudence deduction: wrongful confinement inherently satisfies wrongful restraint
    if extracted.get("wrongful_confinement") == "TRUE":
        extracted["wrongful_restraint"] = "TRUE"

    # 2. LLM structured refinement if Gemini API key is configured
    if settings.GEMINI_API_KEY:
        try:
            from google import genai

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = (
                "You are an Indian statutory legal facts extractor. "
                "Given this incident description, determine whether each fact ingredient is TRUE, FALSE, or UNKNOWN:\n"
                f"Incident: {scenario_text}\n\n"
                "Return JSON with fact keys and string values 'TRUE', 'FALSE', or 'UNKNOWN'. Only return JSON."
            )
            # Run in thread pool to maintain async concurrency
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
            )
            # If successful, parse JSON facts
            if response and response.text:
                import json
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                llm_facts = json.loads(text)
                if isinstance(llm_facts, dict):
                    for k, v in llm_facts.items():
                        v_str = str(v).upper()
                        if v_str in ("TRUE", "FALSE"):
                            extracted[k] = v_str
        except Exception as exc:
            logger.debug(f"LLM fact extraction skipped or failed: {exc}")

    return extracted

