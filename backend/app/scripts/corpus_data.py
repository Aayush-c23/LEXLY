"""
Statutory Legal Corpus Data for LEXLY (Phase 2).

Defines:
1. Statutory Acts (Bharatiya Nyaya Sanhita, 2023 and Indian Penal Code, 1860).
2. Fact Questions Catalog covering Body and Property offences with EN & HI templates.
3. 20 High-Precision Legal Provisions with facts mappings and BNSS First Schedule procedural booleans.
4. Provision Hierarchy relations (LESSER_INCLUDED).
"""

from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 1. Statutory Acts
# -----------------------------------------------------------------------------
ACTS_DATA: List[Dict[str, Any]] = [
    {
        "name": "Bharatiya Nyaya Sanhita, 2023",
        "short_name": "BNS",
        "enacted_year": 2023,
        "is_active": True,
    },
    {
        "name": "Indian Penal Code, 1860",
        "short_name": "IPC",
        "enacted_year": 1860,
        "is_active": True,
    },
]

# -----------------------------------------------------------------------------
# 2. Fact Questions Catalog (EN & HI)
# -----------------------------------------------------------------------------
FACT_QUESTIONS_DATA: List[Dict[str, Any]] = [
    # 1. physical_contact
    {
        "fact_key": "physical_contact",
        "locale": "en",
        "question_text": "Did the accused make physical contact or apply force to any person?",
        "observable_proxy_hint": "Slapping, hitting, pushing, pulling, or touching violently.",
        "category": "body",
    },
    {
        "fact_key": "physical_contact",
        "locale": "hi",
        "question_text": "क्या आरोपी ने किसी व्यक्ति के साथ शारीरिक संपर्क या बल का प्रयोग किया?",
        "observable_proxy_hint": "थप्पड़ मारना, पीटना, धक्का देना, खींचना या हिंसक रूप से छूना।",
        "category": "body",
    },
    # 2. bodily_pain_or_infirmity
    {
        "fact_key": "bodily_pain_or_infirmity",
        "locale": "en",
        "question_text": "Did the victim suffer bodily pain, disease, or physical infirmity as a result?",
        "observable_proxy_hint": "Bruises, swelling, cuts, localized body pain, or dizziness.",
        "category": "body",
    },
    {
        "fact_key": "bodily_pain_or_infirmity",
        "locale": "hi",
        "question_text": "क्या इसके परिणामस्वरूप पीड़ित को शारीरिक दर्द, चोट या अस्वस्थता हुई?",
        "observable_proxy_hint": "नील पड़ना, सूजन, कट लगना, शरीर में दर्द या चक्कर आना।",
        "category": "body",
    },
    # 3. grievous_injury_type
    {
        "fact_key": "grievous_injury_type",
        "locale": "en",
        "question_text": "Did the injury cause bone fracture, tooth dislocation, loss of sight/hearing, or severe pain lasting 20+ days?",
        "observable_proxy_hint": "Hospitalization, permanent disfiguration, fractured bone, or bed-rest for 20 days.",
        "category": "body",
    },
    {
        "fact_key": "grievous_injury_type",
        "locale": "hi",
        "question_text": "क्या चोट से हड्डी टूटना, दांत उखड़ना, दृष्टि/श्रवण हानि या 20 से अधिक दिनों तक गंभीर दर्द हुआ?",
        "observable_proxy_hint": "अस्पताल में भर्ती, स्थायी विकृति, हड्डी का फ्रैक्चर या 20 दिनों का बेड रेस्ट।",
        "category": "body",
    },
    # 4. dangerous_weapon_or_means
    {
        "fact_key": "dangerous_weapon_or_means",
        "locale": "en",
        "question_text": "Was the act committed using a deadly weapon, fire, heated substance, poison, corrosive fluid, or explosive?",
        "observable_proxy_hint": "Knives, iron rods, acid, firearms, petrol, or dangerous sharp tools.",
        "category": "body",
    },
    {
        "fact_key": "dangerous_weapon_or_means",
        "locale": "hi",
        "question_text": "क्या यह कृत्य किसी घातक हथियार, आग, तेजाब, विषैले पदार्थ या विस्फोटक से किया गया था?",
        "observable_proxy_hint": "चाकू, लोहे की रॉड, एसिड, आग्नेयास्त्र, पेट्रोल या धारदार हथियार।",
        "category": "body",
    },
    # 5. grave_and_sudden_provocation
    {
        "fact_key": "grave_and_sudden_provocation",
        "locale": "en",
        "question_text": "Did the accused act on grave and sudden provocation without premeditation?",
        "observable_proxy_hint": "Immediate spontaneous response to extreme insult or provocation without prior planning.",
        "category": "body",
    },
    {
        "fact_key": "grave_and_sudden_provocation",
        "locale": "hi",
        "question_text": "क्या आरोपी ने बिना किसी पूर्व योजना के गंभीर और अचानक उकसावे पर यह कदम उठाया?",
        "observable_proxy_hint": "अत्यधिक अपमान या उकसावे पर बिना सोचे-समझे तुरंत की गई प्रतिक्रिया।",
        "category": "body",
    },
    # 6. victim_is_public_servant
    {
        "fact_key": "victim_is_public_servant",
        "locale": "en",
        "question_text": "Was the victim a public servant acting in the lawful discharge of their official duty?",
        "observable_proxy_hint": "Police officers, municipal inspectors, government doctors, or duty officers.",
        "category": "body",
    },
    {
        "fact_key": "victim_is_public_servant",
        "locale": "hi",
        "question_text": "क्या पीड़ित कोई लोक सेवक (सरकारी कर्मचारी) था जो अपने आधिकारिक कर्तव्य का निर्वहन कर रहा था?",
        "observable_proxy_hint": "पुलिसकर्मी, नगर निगम निरीक्षक, सरकारी डॉक्टर या ड्यूटी पर तैनात अधिकारी।",
        "category": "body",
    },
    # 7. intent_to_outrage_modesty
    {
        "fact_key": "intent_to_outrage_modesty",
        "locale": "en",
        "question_text": "Was criminal force or assault used against a woman with the intention to outrage her modesty?",
        "observable_proxy_hint": "Inappropriate grabbing, pulling clothes, or sexually offensive physical advances.",
        "category": "body",
    },
    {
        "fact_key": "intent_to_outrage_modesty",
        "locale": "hi",
        "question_text": "क्या किसी महिला के खिलाफ उसकी लज्जा भंग करने के इरादे से हमला या आपराधिक बल का प्रयोग किया गया था?",
        "observable_proxy_hint": "अनुचित तरीके से छूना, कपड़े खींचना या यौन रूप से आपत्तिजनक शारीरिक हरकतें।",
        "category": "body",
    },
    # 8. wrongful_restraint
    {
        "fact_key": "wrongful_restraint",
        "locale": "en",
        "question_text": "Was a person obstructed from proceeding in any direction in which they had a lawful right to proceed?",
        "observable_proxy_hint": "Blocking a doorway, physically holding someone from walking along a public path.",
        "category": "body",
    },
    {
        "fact_key": "wrongful_restraint",
        "locale": "hi",
        "question_text": "क्या किसी व्यक्ति को उस दिशा में आगे बढ़ने से रोका गया जहां जाने का उसे कानूनी अधिकार था?",
        "observable_proxy_hint": "रास्ता रोकना, किसी को सड़क या दरवाजे से आगे जाने से शारीरिक रूप से रोकना।",
        "category": "body",
    },
    # 9. wrongful_confinement
    {
        "fact_key": "wrongful_confinement",
        "locale": "en",
        "question_text": "Was the person restrained within certain circumscribing limits (prevented from leaving completely)?",
        "observable_proxy_hint": "Locking inside a room, tying to a chair, or barricading all exits.",
        "category": "body",
    },
    {
        "fact_key": "wrongful_confinement",
        "locale": "hi",
        "question_text": "क्या उस व्यक्ति को किसी निश्चित चारदीवारी/सीमा के भीतर पूरी तरह कैद रखा गया?",
        "observable_proxy_hint": "कमरे में ताला बंद करना, कुर्सी से बांधना या बाहर निकलने के सभी रास्ते बंद करना।",
        "category": "body",
    },
    # 10. movable_property_taken
    {
        "fact_key": "movable_property_taken",
        "locale": "en",
        "question_text": "Was any movable property (cash, jewelry, phone, vehicle, goods) moved or taken away?",
        "observable_proxy_hint": "Carrying away personal items, pocketing cash, taking possession of an object.",
        "category": "property",
    },
    {
        "fact_key": "movable_property_taken",
        "locale": "hi",
        "question_text": "क्या कोई चल संपत्ति (नकदी, गहने, फोन, वाहन, सामान) हटाई या छीन ली गई?",
        "observable_proxy_hint": "सामान ले जाना, जेब में पैसे डालना या किसी वस्तु पर जबरन कब्जा करना।",
        "category": "property",
    },
    # 11. without_consent
    {
        "fact_key": "without_consent",
        "locale": "en",
        "question_text": "Was the property taken out of the possession of the owner without their consent?",
        "observable_proxy_hint": "Taken secretly, snatched, or taken while the owner was absent or protesting.",
        "category": "property",
    },
    {
        "fact_key": "without_consent",
        "locale": "hi",
        "question_text": "क्या संपत्ति मालिक की सहमति के बिना उसके कब्जे से निकाली गई?",
        "observable_proxy_hint": "चुपके से ले जाना, झपटना या मालिक की अनुपस्थिति अथवा विरोध के बावजूद ले जाना।",
        "category": "property",
    },
    # 12. dishonest_intention
    {
        "fact_key": "dishonest_intention",
        "locale": "en",
        "question_text": "Was the property taken with the intent to cause wrongful gain to someone or wrongful loss to the owner?",
        "observable_proxy_hint": "Keeping, selling, or appropriating someone else's property for personal gain.",
        "category": "property",
    },
    {
        "fact_key": "dishonest_intention",
        "locale": "hi",
        "question_text": "क्या संपत्ति किसी को अनुचित लाभ या मालिक को अनुचित नुकसान पहुंचाने के इरादे से ली गई थी?",
        "observable_proxy_hint": "व्यक्तिगत लाभ के लिए किसी अन्य की संपत्ति को अपने पास रखना या बेचना।",
        "category": "property",
    },
    # 13. inside_building_or_dwelling
    {
        "fact_key": "inside_building_or_dwelling",
        "locale": "en",
        "question_text": "Did the incident occur inside a building, tent, or vessel used as a human dwelling or for custody of property?",
        "observable_proxy_hint": "Residential home, apartment, office warehouse, shop, or inhabited room.",
        "category": "property",
    },
    {
        "fact_key": "inside_building_or_dwelling",
        "locale": "hi",
        "question_text": "क्या यह घटना मानव आवास या संपत्ति की सुरक्षा के लिए उपयोग की जाने वाली किसी इमारत, घर या दुकान में हुई?",
        "observable_proxy_hint": "आवासीय मकान, फ्लैट, गोदाम, दुकान या रहने का कमरा।",
        "category": "property",
    },
    # 14. instant_fear_of_death_or_hurt
    {
        "fact_key": "instant_fear_of_death_or_hurt",
        "locale": "en",
        "question_text": "In committing the theft or extortion, was the victim put in fear of instant death, instant hurt, or instant wrongful restraint?",
        "observable_proxy_hint": "Threatening at knifepoint/gunpoint, physically tackling, or menacing with imminent death/injury.",
        "category": "property",
    },
    {
        "fact_key": "instant_fear_of_death_or_hurt",
        "locale": "hi",
        "question_text": "क्या चोरी या वसूली करते समय पीड़ित के मन में तत्काल मृत्यु, तत्काल चोट या तत्काल बंधक बनाए जाने का डर पैदा किया गया?",
        "observable_proxy_hint": "चाकू या बंदूक तानना, मारपीट करना या तुरंत जान से मारने की धमकी देना।",
        "category": "property",
    },
    # 15. five_or_more_offenders
    {
        "fact_key": "five_or_more_offenders",
        "locale": "en",
        "question_text": "Were there five or more persons conjointly committing or attempting to commit the robbery?",
        "observable_proxy_hint": "Gang of 5 or more attackers acting together.",
        "category": "property",
    },
    {
        "fact_key": "five_or_more_offenders",
        "locale": "hi",
        "question_text": "क्या डकैती या लूट करने में संयुक्त रूप से पांच या अधिक व्यक्ति शामिल थे?",
        "observable_proxy_hint": "एक साथ हमला करने वाले 5 या उससे अधिक लोगों का गिरोह।",
        "category": "property",
    },
    # 16. unlawful_entry_into_property
    {
        "fact_key": "unlawful_entry_into_property",
        "locale": "en",
        "question_text": "Did the offender enter into or remain on property in the possession of another with intent to commit an offence or intimidate/insult?",
        "observable_proxy_hint": "Entering private compound, climbing walls, or breaking gates unlawfully.",
        "category": "property",
    },
    {
        "fact_key": "unlawful_entry_into_property",
        "locale": "hi",
        "question_text": "क्या अपराधी ने किसी अपराध, धमकी या अपमान के इरादे से किसी अन्य के कब्जे वाली संपत्ति में अवैध प्रवेश किया?",
        "observable_proxy_hint": "निजी परिसर में घुसना, दीवार फांदना या गैरकानूनी रूप से गेट तोड़कर प्रवेश करना।",
        "category": "property",
    },
]

# -----------------------------------------------------------------------------
# 3. 20 High-Precision Legal Provisions Data
# -----------------------------------------------------------------------------
PROVISIONS_DATA: List[Dict[str, Any]] = [
    # ---------------- BODY OFFENCES (1-11) ----------------
    # 1. BNS 115(2) - Simple Hurt
    {
        "section_number": "115(2)",
        "bns_equivalent": "Section 115(2) BNS",
        "ipc_equivalent": "Section 323 IPC",
        "title": "Voluntarily causing hurt",
        "statutory_text": "Whoever voluntarily causes hurt shall be punished with imprisonment of either description for a term which may extend to one year, or with fine which may extend to ten thousand rupees, or with both.",
        "plain_summary": "Intentionally causing bodily pain, injury, or sickness to another person without deadly weapons or grave bone injury.",
        "punishment": "Imprisonment up to 1 year, or fine up to 10,000 rupees, or both.",
        "is_cognizable": False,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "FALSE",
            "dangerous_weapon_or_means": "FALSE",
            "grave_and_sudden_provocation": "FALSE",
        },
    },
    # 2. BNS 117(2) - Grievous Hurt
    {
        "section_number": "117(2)",
        "bns_equivalent": "Section 117(2) BNS",
        "ipc_equivalent": "Section 325 IPC",
        "title": "Voluntarily causing grievous hurt",
        "statutory_text": "Whoever, except in the case provided for by sub-section (2) of section 122, voluntarily causes grievous hurt, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
        "plain_summary": "Intentionally causing serious bodily injury such as permanent loss of sight/hearing, fracture/dislocation of bone/tooth, or severe bodily pain for 20+ days.",
        "punishment": "Imprisonment up to 7 years, and fine.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "TRUE",
            "dangerous_weapon_or_means": "FALSE",
            "grave_and_sudden_provocation": "FALSE",
        },
    },
    # 3. BNS 118(1) - Hurt by Dangerous Weapon
    {
        "section_number": "118(1)",
        "bns_equivalent": "Section 118(1) BNS",
        "ipc_equivalent": "Section 324 IPC",
        "title": "Voluntarily causing hurt by dangerous weapons or means",
        "statutory_text": "Whoever, except in the case provided for by sub-section (1) of section 122, voluntarily causes hurt by means of any instrument for shooting, stabbing or cutting, or any instrument which, used as a weapon of offence, is likely to cause death, or by means of fire or any heated substance, or by means of any poison or any corrosive substance, or by means of any explosive substance, or by means of any substance which it is deleterious to the human body to inhale, to swallow, or to receive into the blood, or by means of any animal, shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
        "plain_summary": "Causing simple bodily hurt using sharp cutting tools, blades, iron rods, fire, hot liquid, or poisonous/corrosive fluids.",
        "punishment": "Imprisonment up to 3 years, or fine, or both.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "FALSE",
            "dangerous_weapon_or_means": "TRUE",
            "grave_and_sudden_provocation": "FALSE",
        },
    },
    # 4. BNS 118(2) - Grievous Hurt by Dangerous Weapon
    {
        "section_number": "118(2)",
        "bns_equivalent": "Section 118(2) BNS",
        "ipc_equivalent": "Section 326 IPC",
        "title": "Voluntarily causing grievous hurt by dangerous weapons or means",
        "statutory_text": "Whoever, except in the case provided for by sub-section (2) of section 122, voluntarily causes grievous hurt by any means mentioned in sub-section (1), shall be punished with imprisonment for life, or with imprisonment of either description for a term which shall not be less than one year but which may extend to ten years, and shall also be liable to fine.",
        "plain_summary": "Causing fracture, disfigurement, or permanent grievous bodily harm using weapons, fire, blades, or corrosive substances.",
        "punishment": "Imprisonment for life, or imprisonment from 1 to 10 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Magistrate of the first class",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "TRUE",
            "dangerous_weapon_or_means": "TRUE",
            "grave_and_sudden_provocation": "FALSE",
        },
    },
    # 5. BNS 122(1) - Hurt on Provocation
    {
        "section_number": "122(1)",
        "bns_equivalent": "Section 122(1) BNS",
        "ipc_equivalent": "Section 334 IPC",
        "title": "Voluntarily causing hurt on grave and sudden provocation",
        "statutory_text": "Whoever voluntarily causes hurt on grave and sudden provocation, if he neither intends nor knows himself to be likely to cause hurt to any person other than the person who gave the provocation, shall be punished with imprisonment of either description for a term which may extend to one month, or with fine which may extend to five thousand rupees, or with both.",
        "plain_summary": "Causing simple bodily hurt spontaneously upon sudden and severe provocation without premeditation.",
        "punishment": "Imprisonment up to 1 month, or fine up to 5,000 rupees, or both.",
        "is_cognizable": False,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "FALSE",
            "grave_and_sudden_provocation": "TRUE",
        },
    },
    # 6. BNS 122(2) - Grievous Hurt on Provocation
    {
        "section_number": "122(2)",
        "bns_equivalent": "Section 122(2) BNS",
        "ipc_equivalent": "Section 335 IPC",
        "title": "Voluntarily causing grievous hurt on grave and sudden provocation",
        "statutory_text": "Whoever voluntarily causes grievous hurt on grave and sudden provocation, if he neither intends nor knows himself to be likely to cause grievous hurt to any person other than the person who gave the provocation, shall be punished with imprisonment of either description for a term which may extend to four years, or with fine which may extend to ten thousand rupees, or with both.",
        "plain_summary": "Causing serious fracture or grievous injury due to sudden and grave provocation without prior intention.",
        "punishment": "Imprisonment up to 4 years, or fine up to 10,000 rupees, or both.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Magistrate of the first class",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "grievous_injury_type": "TRUE",
            "grave_and_sudden_provocation": "TRUE",
        },
    },
    # 7. BNS 126(2) - Wrongful Restraint
    {
        "section_number": "126(2)",
        "bns_equivalent": "Section 126(2) BNS",
        "ipc_equivalent": "Section 341 IPC",
        "title": "Punishment for wrongful restraint",
        "statutory_text": "Whoever wrongfully restrains any person shall be punished with simple imprisonment for a term which may extend to one month, or with fine which may extend to five thousand rupees, or with both.",
        "plain_summary": "Obstructing a person so as to prevent them from moving in a direction they have a legal right to proceed.",
        "punishment": "Simple imprisonment up to 1 month, or fine up to 5,000 rupees, or both.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "wrongful_restraint": "TRUE",
            "wrongful_confinement": "FALSE",
        },
    },
    # 8. BNS 127(2) - Wrongful Confinement
    {
        "section_number": "127(2)",
        "bns_equivalent": "Section 127(2) BNS",
        "ipc_equivalent": "Section 342 IPC",
        "title": "Punishment for wrongful confinement",
        "statutory_text": "Whoever wrongfully confines any person shall be punished with imprisonment of either description for a term which may extend to one year, or with fine which may extend to five thousand rupees, or with both.",
        "plain_summary": "Detaining or locking up a person within circumscribing boundaries so they cannot leave at all.",
        "punishment": "Imprisonment up to 1 year, or fine up to 5,000 rupees, or both.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "wrongful_restraint": "TRUE",
            "wrongful_confinement": "TRUE",
        },
    },
    # 9. BNS 131 - Assault or Criminal Force without provocation
    {
        "section_number": "131",
        "bns_equivalent": "Section 131 BNS",
        "ipc_equivalent": "Section 352 IPC",
        "title": "Punishment for assault or criminal force otherwise than on grave provocation",
        "statutory_text": "Whoever assaults or uses criminal force to any person otherwise than on grave and sudden provocation given by that person, shall be punished with imprisonment of either description for a term which may extend to three months, or with fine which may extend to one thousand rupees, or with both.",
        "plain_summary": "Threatening or using offensive physical force against someone without causing physical hurt or injury.",
        "punishment": "Imprisonment up to 3 months, or fine up to 1,000 rupees, or both.",
        "is_cognizable": False,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "FALSE",
            "victim_is_public_servant": "FALSE",
            "intent_to_outrage_modesty": "FALSE",
            "grave_and_sudden_provocation": "FALSE",
        },
    },
    # 10. BNS 132 - Assault on Public Servant
    {
        "section_number": "132",
        "bns_equivalent": "Section 132 BNS",
        "ipc_equivalent": "Section 353 IPC",
        "title": "Assault or criminal force to deter public servant from discharge of his duty",
        "statutory_text": "Whoever assaults or uses criminal force to any person being a public servant in the execution of his duty as such public servant, or with intent to prevent or deter that person from discharging his duty as such public servant, or in consequence of anything done or attempted to be done by such person in the lawful discharge of his duty as such public servant, shall be punished with imprisonment of either description for a term which may extend to seven years, or with fine, or with both.",
        "plain_summary": "Assaulting or pushing a police officer or public official to prevent or obstruct them from performing official duties.",
        "punishment": "Imprisonment up to 7 years, or fine, or both.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Magistrate of the first class",
        "facts": {
            "physical_contact": "TRUE",
            "victim_is_public_servant": "TRUE",
        },
    },
    # 11. BNS 74 - Assault with intent to outrage modesty of a woman
    {
        "section_number": "74",
        "bns_equivalent": "Section 74 BNS",
        "ipc_equivalent": "Section 354 IPC",
        "title": "Assault or use of criminal force to woman with intent to outrage her modesty",
        "statutory_text": "Whoever assaults or uses criminal force to any woman, intending to outrage or knowing it to be likely that he will thereby outrage her modesty, shall be punished with imprisonment of either description for a term which shall not be less than one year but which may extend to five years, and shall also be liable to fine.",
        "plain_summary": "Using criminal physical force or assault against a woman with the specific intent or knowledge that it will outrage her modesty.",
        "punishment": "Imprisonment from 1 to 5 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "physical_contact": "TRUE",
            "intent_to_outrage_modesty": "TRUE",
        },
    },

    # ---------------- PROPERTY OFFENCES (12-20) ----------------
    # 12. BNS 303(2) - Simple Theft
    {
        "section_number": "303(2)",
        "bns_equivalent": "Section 303(2) BNS",
        "ipc_equivalent": "Section 379 IPC",
        "title": "Punishment for theft",
        "statutory_text": "Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both; and in case of second or subsequent conviction of any person under this section, he shall be punished with rigorous imprisonment for a term which shall not be less than one year but which may extend to five years and with fine.",
        "plain_summary": "Dishonestly moving or taking movable property out of someone's possession without their consent.",
        "punishment": "Imprisonment up to 3 years, or fine, or both.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "movable_property_taken": "TRUE",
            "without_consent": "TRUE",
            "dishonest_intention": "TRUE",
            "inside_building_or_dwelling": "FALSE",
            "instant_fear_of_death_or_hurt": "FALSE",
        },
    },
    # 13. BNS 305 - Theft in dwelling house, etc.
    {
        "section_number": "305",
        "bns_equivalent": "Section 305 BNS",
        "ipc_equivalent": "Section 380 IPC",
        "title": "Theft in dwelling house, etc.",
        "statutory_text": "Whoever commits theft in any building, tent or vessel, which building, tent or vessel is used as a human dwelling, or used for the custody of property, or in any place of worship, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
        "plain_summary": "Committing theft inside a residential house, apartment, tent, shop, or building used for keeping property.",
        "punishment": "Imprisonment up to 7 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "movable_property_taken": "TRUE",
            "without_consent": "TRUE",
            "dishonest_intention": "TRUE",
            "inside_building_or_dwelling": "TRUE",
            "instant_fear_of_death_or_hurt": "FALSE",
        },
    },
    # 14. BNS 304(2) - Snatching
    {
        "section_number": "304(2)",
        "bns_equivalent": "Section 304(2) BNS",
        "ipc_equivalent": "Section 379A IPC",
        "title": "Snatching",
        "statutory_text": "Theft is snatching if, in order to commit theft, the offender suddenly or quickly or forcibly seizes, secures, grabs or takes away from any person or from his possession any movable property. Whoever commits snatching shall be punished with imprisonment of either description for a term which may extend to three years, and shall also be liable to fine.",
        "plain_summary": "Quickly or forcibly grabbing or snatching movable property (like mobile phone or chain) directly from a person.",
        "punishment": "Imprisonment up to 3 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "movable_property_taken": "TRUE",
            "without_consent": "TRUE",
            "dishonest_intention": "TRUE",
            "instant_fear_of_death_or_hurt": "FALSE",
        },
    },
    # 15. BNS 308(2) - Extortion
    {
        "section_number": "308(2)",
        "bns_equivalent": "Section 308(2) BNS",
        "ipc_equivalent": "Section 384 IPC",
        "title": "Punishment for extortion",
        "statutory_text": "Whoever commits extortion shall be punished with imprisonment of either description for a term which may extend to seven years, or with fine, or with both.",
        "plain_summary": "Intentionally putting a person in fear of injury and thereby dishonestly inducing them to deliver property or money.",
        "punishment": "Imprisonment up to 7 years, or fine, or both.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Magistrate of the first class",
        "facts": {
            "movable_property_taken": "TRUE",
            "dishonest_intention": "TRUE",
            "without_consent": "FALSE",
            "instant_fear_of_death_or_hurt": "FALSE",
        },
    },
    # 16. BNS 309(4) - Robbery
    {
        "section_number": "309(4)",
        "bns_equivalent": "Section 309(4) BNS",
        "ipc_equivalent": "Section 392 IPC",
        "title": "Punishment for robbery",
        "statutory_text": "Whoever commits robbery shall be punished with rigorous imprisonment for a term which may extend to ten years, and shall also be liable to fine; and, if the robbery be committed on the highway between sunset and sunrise, the imprisonment may be extended to fourteen years.",
        "plain_summary": "Theft or extortion accomplished by causing or threatening instant death, instant hurt, or instant wrongful restraint.",
        "punishment": "Rigorous imprisonment up to 10 years (14 years on highway at night), and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Magistrate of the first class",
        "facts": {
            "movable_property_taken": "TRUE",
            "dishonest_intention": "TRUE",
            "instant_fear_of_death_or_hurt": "TRUE",
            "five_or_more_offenders": "FALSE",
            "physical_contact": "FALSE",
        },
    },
    # 17. BNS 309(6) - Voluntarily causing hurt in committing robbery
    {
        "section_number": "309(6)",
        "bns_equivalent": "Section 309(6) BNS",
        "ipc_equivalent": "Section 394 IPC",
        "title": "Voluntarily causing hurt in committing robbery",
        "statutory_text": "If any person, in committing or in attempting to commit robbery, voluntarily causes hurt, such person, and any other person jointly concerned in committing or attempting to commit such robbery, shall be punished with imprisonment for life, or with rigorous imprisonment for a term which may extend to ten years, and shall also be liable to fine.",
        "plain_summary": "Causing physical injury, bleeding, or beating a victim while carrying out or attempting a robbery.",
        "punishment": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Court of Session",
        "facts": {
            "movable_property_taken": "TRUE",
            "dishonest_intention": "TRUE",
            "instant_fear_of_death_or_hurt": "TRUE",
            "physical_contact": "TRUE",
            "bodily_pain_or_infirmity": "TRUE",
            "five_or_more_offenders": "FALSE",
        },
    },
    # 18. BNS 310(2) - Dacoity
    {
        "section_number": "310(2)",
        "bns_equivalent": "Section 310(2) BNS",
        "ipc_equivalent": "Section 395 IPC",
        "title": "Punishment for dacoity",
        "statutory_text": "Whoever commits dacoity shall be punished with imprisonment for life, or with rigorous imprisonment for a term which may extend to ten years, and shall also be liable to fine.",
        "plain_summary": "Robbery committed or attempted conjointly by five or more persons acting together.",
        "punishment": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine.",
        "is_cognizable": True,
        "is_bailable": False,
        "compoundable_type": "NON_COMPOUNDABLE",
        "triable_by": "Court of Session",
        "facts": {
            "movable_property_taken": "TRUE",
            "dishonest_intention": "TRUE",
            "instant_fear_of_death_or_hurt": "TRUE",
            "five_or_more_offenders": "TRUE",
        },
    },
    # 19. BNS 329(3) - Criminal Trespass
    {
        "section_number": "329(3)",
        "bns_equivalent": "Section 329(3) BNS",
        "ipc_equivalent": "Section 447 IPC",
        "title": "Punishment for criminal trespass",
        "statutory_text": "Whoever commits criminal trespass shall be punished with imprisonment of either description for a term which may extend to three months, or with fine which may extend to five thousand rupees, or with both.",
        "plain_summary": "Entering onto property in possession of another with intent to commit an offence, or intimidate, insult, or annoy.",
        "punishment": "Imprisonment up to 3 months, or fine up to 5,000 rupees, or both.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "unlawful_entry_into_property": "TRUE",
            "inside_building_or_dwelling": "FALSE",
        },
    },
    # 20. BNS 331(1) - House-Trespass
    {
        "section_number": "331(1)",
        "bns_equivalent": "Section 331(1) BNS",
        "ipc_equivalent": "Section 448 IPC",
        "title": "Punishment for house-trespass",
        "statutory_text": "Whoever commits house-trespass shall be punished with imprisonment of either description for a term which may extend to one year, or with fine which may extend to five thousand rupees, or with both.",
        "plain_summary": "Committing criminal trespass by entering into or remaining in any building, tent, or vessel used as human dwelling or place for worship or custody of property.",
        "punishment": "Imprisonment up to 1 year, or fine up to 5,000 rupees, or both.",
        "is_cognizable": True,
        "is_bailable": True,
        "compoundable_type": "COMPOUNDABLE",
        "triable_by": "Any Magistrate",
        "facts": {
            "unlawful_entry_into_property": "TRUE",
            "inside_building_or_dwelling": "TRUE",
        },
    },
]

# -----------------------------------------------------------------------------
# 4. Provision Hierarchy (LESSER_INCLUDED parent -> child relations)
# -----------------------------------------------------------------------------
HIERARCHY_DATA: List[Dict[str, str]] = [
    # Grievous Hurt includes Simple Hurt
    {"parent_section": "117(2)", "child_section": "115(2)", "relation_type": "LESSER_INCLUDED"},
    # Hurt with Weapon includes Simple Hurt
    {"parent_section": "118(1)", "child_section": "115(2)", "relation_type": "LESSER_INCLUDED"},
    # Grievous Hurt with Weapon includes Grievous Hurt
    {"parent_section": "118(2)", "child_section": "117(2)", "relation_type": "LESSER_INCLUDED"},
    # Grievous Hurt with Weapon includes Hurt with Weapon
    {"parent_section": "118(2)", "child_section": "118(1)", "relation_type": "LESSER_INCLUDED"},
    # Wrongful Confinement includes Wrongful Restraint
    {"parent_section": "127(2)", "child_section": "126(2)", "relation_type": "LESSER_INCLUDED"},
    # Theft in Dwelling includes Simple Theft
    {"parent_section": "305", "child_section": "303(2)", "relation_type": "LESSER_INCLUDED"},
    # Robbery includes Simple Theft
    {"parent_section": "309(4)", "child_section": "303(2)", "relation_type": "LESSER_INCLUDED"},
    # Robbery with Hurt includes Robbery
    {"parent_section": "309(6)", "child_section": "309(4)", "relation_type": "LESSER_INCLUDED"},
    # Dacoity includes Robbery
    {"parent_section": "310(2)", "child_section": "309(4)", "relation_type": "LESSER_INCLUDED"},
    # House-trespass includes Criminal Trespass
    {"parent_section": "331(1)", "child_section": "329(3)", "relation_type": "LESSER_INCLUDED"},
]
