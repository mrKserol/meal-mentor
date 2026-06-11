MEDICAL_RISK_KEYWORDS = [
    "болит",
    "боль",
    "анализ",
    "анализы",
    "лекарство",
    "лекарства",
    "таблетки",
    "дозировка",
    "беременность",
    "диабет",
    "давление",
    "сердце",
    "почки",
    "печень",
    "рвота",
    "обморок",
    "резко похудел",
    "резко похудела",
    "резко набрал",
    "резко набрала",
    "плохо себя чувствую",
    "плохое самочувствие",
    "расстройство пищевого поведения",
    "рпп",
]


def detect_medical_risk(message: str) -> dict:
    text = (message or "").lower()
    matched = [keyword for keyword in MEDICAL_RISK_KEYWORDS if keyword in text]

    return {
        "medical_risk_detected": bool(matched),
        "matched_keywords": matched,
        "instruction": (
            "Give general support only and recommend a qualified specialist. "
            "Do not diagnose, treat, prescribe medications or supplement dosages."
            if matched
            else None
        ),
    }
