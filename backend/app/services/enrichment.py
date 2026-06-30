KEYWORDS = {
    "Artificial Intelligence": {"ai", "machine learning", "llm", "neural", "model", "automation"},
    "Cybersecurity": {"security", "phishing", "ransomware", "malware", "threat", "privacy"},
    "Business": {"sales", "market", "revenue", "customer", "strategy", "growth"},
    "Education": {"lecture", "course", "student", "learning", "curriculum", "workshop"},
    "Healthcare": {"patient", "clinical", "health", "medical", "care", "diagnosis"},
}


def categorize(text: str, title: str) -> tuple[str, float]:
    haystack = f"{title}\n{text}".lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in haystack)
        for category, keywords in KEYWORDS.items()
    }
    category, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return "General", 0.35
    return category, min(0.95, 0.45 + score * 0.12)


def summarize(text: str, title: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return f"{title} was discovered, but no extractable text is available yet."
    return clean[:700] + ("..." if len(clean) > 700 else "")

