import re

CITIES = [
    "noida",
    "greater noida",
    "gurgaon",
    "gurugram",
    "delhi",
    "ghaziabad"
]

def extract_entities(text: str):
    text = text.lower()

    city = None
    bhk = None
    budget = None

    # -------- CITY ----------
    for c in CITIES:
        if c in text:
            city = c
            break

    # -------- BHK ----------
    bhk_patterns = [
        r"(\d)\s*bhk",
        r"(\d)\s*bedroom",
        r"(\d)\s*bed"
    ]
    for p in bhk_patterns:
        m = re.search(p, text)
        if m:
            bhk = m.group(1)
            break

    # -------- BUDGET ----------
    # examples: 70 lakh, 1 crore, under 80l, below 1.2 cr
    price_patterns = [
        r"(\d+\.?\d*)\s*(lakh|lac|l)",
        r"(\d+\.?\d*)\s*(crore|cr)"
    ]

    for p in price_patterns:
        m = re.search(p, text)
        if m:
            value = float(m.group(1))
            unit = m.group(2)

            if "l" in unit:
                budget = int(value * 100000)
            else:
                budget = int(value * 10000000)
            break

    return city, bhk, budget
