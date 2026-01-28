from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import re

app = Flask(__name__)

# ==============================
# USER SESSION (TEMP MEMORY)
# ==============================
user_state = {}

# ==============================
# LOAD GOOGLE SHEET
# ==============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1htI7HBmHTMHz9jxQiP2kEoh3v3YydzNt_Xsov84E7Ig/export?format=csv"
df = pd.read_csv(SHEET_URL)

df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

for col in ["project_name", "city", "bhk"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.lower()

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

    # INIT USER
    if from_number not in user_state:
        user_state[from_number] = {}

    state = user_state[from_number]

    # ======================
    # GREETING / START
    # ======================
    if incoming in ["hi", "hello", "hey", "start", "menu"]:
        state.clear()
        state["step"] = "MAIN_MENU"
        msg.body(
            "👋 *Welcome to RealEstate Bot* 🏠\n\n"
            "Please choose an option:\n"
            "1️⃣ Buy Property\n"
            "2️⃣ Rent Property\n"
            "3️⃣ Talk to Agent\n"
            "4️⃣ Help\n\n"
            "Reply with number 👇"
        )
        return str(resp)

    # ======================
    # MAIN MENU
    # ======================
    if state.get("step") == "MAIN_MENU":
        if incoming == "1":
            state["step"] = "CITY"
            msg.body(
                "📍 *Select City*\n\n"
                "1️⃣ Noida\n"
                "2️⃣ Greater Noida\n"
                "3️⃣ Gurgaon\n\n"
                "Reply with number"
            )
            return str(resp)

        if incoming == "3":
            msg.body("📞 Our agent will contact you shortly.\nThank you!")
            return str(resp)

        msg.body("❌ Invalid option. Type *menu* to restart.")
        return str(resp)

    # ======================
    # CITY
    # ======================
    if state.get("step") == "CITY":
        city_map = {"1": "noida", "2": "greater noida", "3": "gurgaon"}
        if incoming in city_map:
            state["city"] = city_map[incoming]
            state["step"] = "BHK"
            msg.body(
                "🏠 *Select BHK*\n\n"
                "1️⃣ 1 BHK\n"
                "2️⃣ 2 BHK\n"
                "3️⃣ 3 BHK\n"
                "4️⃣ 4+ BHK"
            )
            return str(resp)

        msg.body("❌ Please select valid city number.")
        return str(resp)

    # ======================
    # BHK
    # ======================
    if state.get("step") == "BHK":
        bhk_map = {"1": "1", "2": "2", "3": "3", "4": "4"}
        if incoming in bhk_map:
            state["bhk"] = bhk_map[incoming]
            state["step"] = "BUDGET"
            msg.body(
                "💰 *Select Budget*\n\n"
                "1️⃣ Under 50 Lakh\n"
                "2️⃣ Under 75 Lakh\n"
                "3️⃣ Under 1 Crore\n"
                "4️⃣ Above 1 Crore"
            )
            return str(resp)

        msg.body("❌ Invalid BHK option.")
        return str(resp)

    # ======================
    # BUDGET
    # ======================
    if state.get("step") == "BUDGET":
        budget_map = {
            "1": 5000000,
            "2": 7500000,
            "3": 10000000,
            "4": 999999999
        }

        if incoming in budget_map:
            results = filter_projects(
                state["city"],
                state["bhk"],
                budget_map[incoming]
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

        msg.body("❌ Invalid budget option.")
        return str(resp)

    # ======================
    # FALLBACK
    # ======================
    msg.body("🤖 I didn’t understand.\nType *menu* to start again.")
    return str(resp)


if __name__ == "__main__":
    app.run()
