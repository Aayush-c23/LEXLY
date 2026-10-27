"""
Crisis & Emergency Interception Engine for LEXLY (BE-301).

Pre-routing safety classifier detecting immediate threats to life, active domestic violence,
crimes against children, sexual assault in progress, or immediate harm.
Short-circuits before statutory retrieval with verified Indian emergency helplines in <15ms.
"""

import re
from typing import List, Optional, Tuple
from backend.app.schemas.analyze import HelplineInfo

# Verified Indian Statutory Emergency Helplines
VERIFIED_HELPLINES: List[HelplineInfo] = [
    HelplineInfo(
        name="National Emergency Helpline",
        number="112",
        description="All-in-one unified emergency response for Police, Fire, and Ambulance.",
    ),
    HelplineInfo(
        name="Women Helpline (Domestic Violence / Safety)",
        number="181",
        description="24/7 dedicated toll-free emergency response for women in distress.",
    ),
    HelplineInfo(
        name="Childline India (Crimes against Children)",
        number="1098",
        description="24-hour emergency phone outreach service for children in need of care and protection.",
    ),
    HelplineInfo(
        name="National Cyber Crime Reporting Helpline",
        number="1930",
        description="Immediate cyber financial fraud and emergency cyber crime reporting.",
    ),
]

# High-precision emergency patterns (case-insensitive)
CRISIS_REGEX_PATTERNS = [
    # Kidnapping / Abduction in progress
    r"\b(kidnap(?:ped|ping)?|abduct(?:ed|ion|ing)?)\s+(?:my|a|our)?\s*(?:child|daughter|son|kid|baby|wife|sister|brother)\b",
    r"\bholding\s+(?:my|a|our)?\s*(?:child|kid|baby|daughter|son)\s+hostage\b",
    r"\bchild\s+(?:is\s+)?kidnapped\s+right\s+now\b",
    
    # Active threats to life / murder / weapon Menace
    r"\bthreatened\s+to\s+kill\s+me\b",
    r"\bgoing\s+to\s+kill\s+me\b",
    r"\bkill\s+me\s+in\s+\d+\s*(?:minutes|mins|hours)\b",
    r"\bgun\s+(?:is\s+)?pointed\s+at\s+me\b",
    r"\bholding\s+a\s+(?:gun|knife|pistol|revolver)\s+at\s+(?:me|my\s+neck|my\s+head)\b",
    r"\b(someone|they)\s+(?:are\s+)?trying\s+to\s+murder\s+me\b",
    r"\barmed\s+(?:attackers|robbers|men)\s+inside\s+my\s+house\s+right\s+now\b",

    # Active Domestic Violence / Physical Assault in progress
    r"\bdomestic\s+violence\s+emergency\b",
    r"\b(?:husband|father|brother|partner|in-laws|wife)\s+(?:is|are)\s+beating\s+me\s+(?:up\s+)?right\s+now\b",
    r"\blocked\s+in\s+(?:the\s+)?(?:bathroom|room)\s+(?:trying\s+to\s+escape|escaping)\b",
    r"\bactively\s+assaulting\s+me\b",
    r"\bbeing\s+beaten\s+mercilessly\s+right\s+now\b",

    # Active Sexual Assault
    r"\b(?:attempting\s+to\s+rape|rape\s+in\s+progress|sexually\s+assaulting\s+me\s+right\s+now)\b",
    r"\bforced\s+into\s+a\s+(?:car|room)\s+and\s+(?:molesting|assaulting)\b",

    # Severe Medical / Bleeding Emergency
    r"\bbleeding\s+profusely\s+need\s+ambulance\b",
    r"\bstabbed\s+(?:and\s+)?dying\b",

    # Suicide / Self-Harm
    r"\b(?:going\s+to|want\s+to)\s+(?:commit\s+suicide|end\s+my\s+life|kill\s+myself)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CRISIS_REGEX_PATTERNS]


def detect_emergency_crisis(scenario: str) -> Tuple[bool, Optional[str], List[HelplineInfo]]:
    """
    Rapidly evaluates scenario text for urgent emergency tokens.

    Returns
    -------
    Tuple[bool, Optional[str], List[HelplineInfo]]
        - is_emergency: True if scenario contains active life threat or emergency.
        - advisory: Contextual statutory advisory.
        - helplines: List of verified Indian statutory helplines.
    """
    if not scenario:
        return False, None, []

    for pattern in COMPILED_PATTERNS:
        match = pattern.search(scenario)
        if match:
            matched_phrase = match.group(0)
            advisory = (
                f"EMERGENCY ADVISORY: Your narrative indicates an immediate life-safety crisis or active crime "
                f"involving '{matched_phrase}'. LEXLY is an informational statutory analysis assistant and NOT an emergency dispatcher. "
                f"Please immediately call 112 (National Emergency) or the specialized helplines listed below."
            )
            return True, advisory, VERIFIED_HELPLINES

    return False, None, []

