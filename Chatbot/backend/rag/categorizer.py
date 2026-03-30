"""Query intent classification and categorization."""

CATEGORY_KEYWORDS = {
    "operations": [
        "account", "savings", "current", "opening", "closure", "close", "dormant", "inactive",
        "joint", "minor", "nomination", "nominee", "statement", "passbook", "cheque", "deposit",
        "withdrawal", "balance", "transfer", "remittance", "locker", "safe deposit", "fd",
        "fixed deposit", "rd", "recurring", "interest rate", "charges", "fees", "onboarding",
        "employee", "training", "code of conduct", "nri", "nre", "nro", "fcnr",
        "succession", "legal heir", "death claim", "government scheme", "pmjdy", "pmsby",
        "apy", "green banking", "financial literacy", "tds", "tax", "dicgc", "insurance",
    ],
    "loans": [
        "loan", "home loan", "personal loan", "car loan", "education loan", "business loan",
        "msme", "mudra", "emi", "foreclosure", "prepayment", "npa", "recovery", "collateral",
        "mortgage", "gold loan", "interest", "processing fee", "eligibility", "cibil",
        "credit score", "disbursement", "repayment", "overdue", "default", "write-off",
        "lending", "borrower", "guarantee", "ltv",
    ],
    "compliance": [
        "kyc", "aml", "anti-money laundering", "pmla", "fema", "rbi", "regulation",
        "compliance", "audit", "guidelines", "circular", "master direction", "priority sector",
        "psl", "basel", "capital adequacy", "provisioning", "reporting", "str", "ctr",
        "suspicious", "fiu", "data protection", "privacy", "pslc", "digital lending",
        "account aggregator", "fldg",
    ],
    "cards": [
        "credit card", "debit card", "card", "atm", "pos", "contactless", "nfc", "emv",
        "dispute", "chargeback", "fraud", "stolen card", "lost card", "card limit",
        "reward", "cashback", "annual fee", "billing", "minimum due",
    ],
    "digital_banking": [
        "upi", "neft", "rtgs", "imps", "internet banking", "mobile banking", "online",
        "digital", "app", "otp", "password", "phishing", "cyber", "nach", "ecs",
        "auto debit", "standing instruction", "e-mandate", "cts", "cheque truncation",
        "virtual", "fintech", "payment",
    ],
    "risk": [
        "risk", "credit risk", "market risk", "operational risk", "fraud risk", "cyber security",
        "bcp", "disaster recovery", "var", "stress test", "loss", "kri", "rcsa",
        "three lines of defense", "incident", "threat",
    ],
    "customer_service": [
        "complaint", "grievance", "escalation", "ombudsman", "customer service", "dispute",
        "resolution", "tat", "turnaround", "feedback", "redressal", "compensation",
    ],
    "treasury": [
        "letter of credit", "lc", "bank guarantee", "bg", "trade finance", "forex",
        "foreign exchange", "export", "import", "bill of exchange", "treasury",
    ],
}

GREETING_PATTERNS = [
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "greetings", "howdy", "what's up", "how are you", "thanks", "thank you",
    "bye", "goodbye", "see you", "help", "who are you", "what can you do",
]


def categorize_query(query):
    """Classify query intent and return category with confidence."""
    query_lower = query.lower().strip()
    
    # Check for greetings first
    for pattern in GREETING_PATTERNS:
        if pattern in query_lower or query_lower == pattern:
            return {"category": "greeting", "confidence": 0.95, "sub_categories": []}
    
    # Score each category
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        matched = []
        for kw in keywords:
            if kw in query_lower:
                weight = len(kw.split()) * 2  # Multi-word keywords get higher weight
                score += weight
                matched.append(kw)
        if score > 0:
            scores[category] = {"score": score, "matched": matched}
    
    if not scores:
        return {"category": "general", "confidence": 0.3, "sub_categories": []}
    
    # Sort by score
    sorted_cats = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    top_category = sorted_cats[0][0]
    top_score = sorted_cats[0][1]["score"]
    
    # Confidence based on score magnitude
    confidence = min(0.95, 0.5 + (top_score * 0.05))
    
    sub_categories = [cat for cat, _ in sorted_cats[1:3]]
    
    return {
        "category": top_category,
        "confidence": round(confidence, 2),
        "sub_categories": sub_categories,
        "matched_keywords": sorted_cats[0][1]["matched"],
    }


def get_search_categories(categorization):
    """Get categories to search based on categorization."""
    cats = [categorization["category"]]
    cats.extend(categorization.get("sub_categories", []))
    if "general" not in cats:
        cats.append("general")
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result
