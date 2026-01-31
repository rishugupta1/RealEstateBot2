import re

def extract_entities(text):
    text = text.lower()
    city = bhk = budget = None

    if "greater noida" in text:
        city = "greater noida"
    elif "noida" in text:
        city = "noida"
    elif "gurgaon" in text:
        city = "gurgaon"

    bhk_match = re.search(r"(\d)\s*bhk", text)
    if bhk_match:
        bhk = bhk_match.group(1)

    price_match = re.search(r"(\d+)\s*(lakh|lac|crore|cr)", text)
    if price_match:
        value = int(price_match.group(1))
        unit = price_match.group(2)
        budget = value * 100000 if "l" in unit else value * 10000000

    return city, bhk, budget
