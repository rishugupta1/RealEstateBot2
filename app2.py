from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import re

app = Flask(__name__)

# ==============================
# LOAD GOOGLE SHEET AS DATABASE
# ==============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1htI7HBmHTMHz9jxQiP2kEoh3v3YydzNt_Xsov84E7Ig/export?format=csv"
df = pd.read_csv(SHEET_URL)

# ==============================
# CLEAN COLUMN NAMES
# ==============================
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# ==============================
# NORMALIZE TEXT COLUMNS
# ==============================
TEXT_COLS = ["project_name", "city", "bhk"]

for col in TEXT_COLS:
    if col in df.columns:
        df[col] = df[col].astype(str).str.lower()

# ==============================
# CLEAN PRICE COLUMN
# ==============================
def clean_price(val):
    try:
        val = str(val).lower()
        val = val.replace("₹", "").replace(",", "").strip()

        if "cr" in val or "crore" in val:
            return float(re.findall(r"\d+\.?\d*", val)[0]) * 10000000
        if "l" in val or "lakh" in val:
            return float(re.findall(r"\d+\.?\d*", val)[0]) * 100000
        return None
    except:
        return None

df["price_numeric"] = df["price"].apply(clean_price)

# ==============================
# INTENT DETECTION
# ==============================
def detect_intent(text):
    text = text.lower()

    if re.search(r"\b(hi|hello|hey)\b", text):
        return "greeting"

    if re.search(r"\b(help|menu|start)\b", text):
        return "help"

    if re.search(r"\b(buy|flat|project|bhk|noida|gurgaon)\b", text):
        return "search"

    return "unknown"

# ==============================
# FILTER ENGINE
# ==============================
def filter_projects(question):
    q = question.lower()
    data = df.copy()

    # City filter
    for city in data["city"].dropna().unique():
        if city in q:
            data = data[data["city"] == city]

    # BHK filter
    bhk_match = re.search(r"(\d)\s*bhk", q)
    if bhk_match:
        data = data[data["bhk"].str.contains(bhk_match.group(1), na=False)]

    # Budget filter
    price_match = re.search(r"(\d+(\.\d+)?)\s*(cr|crore|l|lakh)", q)
    if price_match:
        value = float(price_match.group(1))
        unit = price_match.group(3)

        max_price = value * 10000000 if unit in ["cr", "crore"] else value * 100000
        data = data[data["price_numeric"] <= max_price]

    return data.head(5)

# ==============================
# WHATSAPP BOT
# ==============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming = request.values.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    intent = detect_intent(incoming)

    # GREETING
    if intent == "greeting":
        msg.body(
            "👋 Welcome to RealEstate Bot 🤖\n\n"
            "You can ask like:\n"
            "• Noida projects under 1 crore\n"
            "• 2 BHK flats in Noida\n"
            "• 3 BHK under 80 lakh\n"
            "• Gurgaon commercial projects\n\n"
            "Type your requirement 👇"
        )
        return str(resp)

    # HELP
    if intent == "help":
        msg.body(
            "ℹ️ I can help you find properties.\n\n"
            "Just type:\n"
            "City + BHK + Budget\n\n"
            "Example:\n"
            "👉 2 bhk in noida under 75 lakh"
        )
        return str(resp)

    # SEARCH
    if intent == "search":
        results = filter_projects(incoming)

        if results.empty:
            msg.body(
                "❌ No matching projects found.\n\n"
                "Try changing:\n"
                "• City\n"
                "• Budget\n"
                "• BHK"
            )
            return str(resp)

        reply = "🏗 *Matching Projects*:\n\n"
        for _, row in results.iterrows():
            reply += (
                f"🏢 *{row['project_name'].title()}*\n"
                f"📍 {row['city'].title()}\n"
                f"🏠 {row['bhk']}\n"
                f"💰 {row['price']}\n"
                f"🔗 {row['link']}\n\n"
            )

        msg.body(reply)
        return str(resp)

    # UNKNOWN
    msg.body(
        "🤖 Sorry, I didn’t understand that.\n\n"
        "Try typing:\n"
        "• 2 bhk in noida\n"
        "• projects under 1 crore\n"
        "• help"
    )
    return str(resp)

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app.run()
