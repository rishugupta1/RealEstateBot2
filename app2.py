from flask import Flask, request
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import psycopg2
import os
import re

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)

# ==============================
# DATABASE (Supabase Postgres ONLY)
# ==============================
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL not set. Check .env (local) or Render env vars")

conn = psycopg2.connect(
    DATABASE_URL,
    sslmode="require"
)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    phone TEXT PRIMARY KEY,
    city TEXT,
    bhk TEXT,
    budget INTEGER,
    updated_at TIMESTAMP DEFAULT now()
)
""")
conn.commit()

# ==============================
# LOAD GOOGLE SHEET
# ==============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1htI7HBmHTMHz9jxQiP2kEoh3v3YydzNt_Xsov84E7Ig/export?format=csv"
df = pd.read_csv(SHEET_URL)

df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df["project_name"] = df["project_name"].astype(str).str.lower()
df["city"] = df["city"].astype(str).str.lower()
df["bhk"] = df["bhk"].astype(str).str.lower()

# ==============================
# PRICE CLEAN
# ==============================
def clean_price(val):
    try:
        val = str(val).lower().replace("₹", "").replace(",", "")
        if "cr" in val:
            return float(re.findall(r"\d+\.?\d*", val)[0]) * 10000000
        if "l" in val:
            return float(re.findall(r"\d+\.?\d*", val)[0]) * 100000
    except:
        return None

df["price_numeric"] = df["price"].apply(clean_price)

# ==============================
# NLP ENTITY EXTRACTION
# ==============================
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

# ==============================
# FILTER ENGINE
# ==============================
def filter_projects(city, bhk, budget):
    data = df.copy()

    if city:
        data = data[data["city"] == city]
    if bhk:
        data = data[data["bhk"].str.contains(bhk, na=False)]
    if budget:
        data = data[data["price_numeric"] <= budget]

    return data.head(5)

# ==============================
# WHATSAPP BOT
# ==============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    from_number = request.values.get("From")
    incoming = request.values.get("Body", "").strip().lower()

    resp = MessagingResponse()
    msg = resp.message()

    # Load user state
    cursor.execute(
        "SELECT city, bhk, budget FROM users WHERE phone=%s",
        (from_number,)
    )
    row = cursor.fetchone()

    state = {"city": None, "bhk": None, "budget": None}
    if row:
        state["city"], state["bhk"], state["budget"] = row

    # NLP update
    city, bhk, budget = extract_entities(incoming)

    if city:
        state["city"] = city
    if bhk:
        state["bhk"] = bhk
    if budget:
        state["budget"] = budget

    # Save state
    cursor.execute("""
        INSERT INTO users (phone, city, bhk, budget)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (phone)
        DO UPDATE SET
            city = EXCLUDED.city,
            bhk = EXCLUDED.bhk,
            budget = EXCLUDED.budget,
            updated_at = now();
    """, (from_number, state["city"], state["bhk"], state["budget"]))
    conn.commit()

    # Greeting
    if incoming in ["hi", "hello", "hey", "menu", "start"]:
        msg.body(
            "👋 *Welcome to RealEstate Bot* 🏠\n\n"
            "Example:\n"
            "• 2 bhk in noida under 75 lakh\n"
            "• 3 bhk gurgaon under 1 crore"
        )
        return str(resp)

    # Auto search
    if state["city"] and state["bhk"] and state["budget"]:
        results = filter_projects(
            state["city"], state["bhk"], state["budget"]
        )

        if results.empty:
            msg.body("❌ No matching projects found.\nType *menu* to restart.")
            return str(resp)

        reply = "🏗 *Matching Projects*\n\n"
        for _, row in results.iterrows():
            reply += (
                f"🏢 *{row['project_name'].title()}*\n"
                f"📍 {row['city'].title()}\n"
                f"🏠 {row['bhk']}\n"
                f"💰 {row['price']}\n"
                f"🔗 {row['link']}\n\n"
            )

        reply += "🔁 Type *menu* for new search"
        msg.body(reply)
        return str(resp)

    # Ask missing info
    if not state["city"]:
        msg.body("📍 Which city? (Noida / Gurgaon / Greater Noida)")
    elif not state["bhk"]:
        msg.body("🏠 How many BHK? (1 / 2 / 3 bhk)")
    elif not state["budget"]:
        msg.body("💰 Budget? (75 lakh / 1 crore)")

    return str(resp)

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
