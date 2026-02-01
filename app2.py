from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

from DB.models import init_db, get_user, save_user
from DATA.projects import load_projects
from NLP.extractor import extract_entities
from SERVICES.filter_service import filter_projects

app = Flask(__name__)

# =========================
# INIT DB & LOAD DATA
# =========================
init_db()
df = load_projects()

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    from_number = request.values.get("From", "")
    incoming = request.values.get("Body", "").strip().lower()

    resp = MessagingResponse()
    msg = resp.message()

    # -------------------------
    # LOAD USER STATE
    # -------------------------
    row = get_user(from_number)
    state = {"city": None, "bhk": None, "budget": None}
    if row:
        state["city"], state["bhk"], state["budget"] = row

    # -------------------------
    # NLP EXTRACTION (HUMAN TEXT)
    # -------------------------
    city, bhk, budget = extract_entities(incoming)

    if city:
        state["city"] = city
    if bhk:
        state["bhk"] = bhk
    if budget:
        state["budget"] = budget

    # SAVE USER PROGRESS
    save_user(from_number, state["city"], state["bhk"], state["budget"])

    # -------------------------
    # SMART HUMAN FLOW
    # -------------------------
    if incoming in ["hi", "hello", "hey", "start", "menu"]:
        msg.body(
            "👋 *Welcome to RealEstate Bot*\n\n"
            "Bas normal language me likho 👇\n\n"
            "• Mujhe Noida me 2 bhk chahiye budget 70 lakh\n"
            "• Gurgaon 3 bhk under 1 crore\n"
            "• Flat in Greater Noida 60L\n"
        )

    elif not state["city"]:
        msg.body(
            "📍 Aap kis city me property chahte ho?\n\n"
            "👉 Noida / Gurgaon / Greater Noida"
        )

    elif not state["bhk"]:
        msg.body(
            "🏠 Kitna BHK chahiye?\n\n"
            "👉 1 BHK / 2 BHK / 3 BHK"
        )

    elif not state["budget"]:
        msg.body(
            "💰 Aapka budget kya hai?\n\n"
            "👉 Jaise: 60 lakh, 80L, 1 crore"
        )

    else:
        # -------------------------
        # FILTER PROJECTS
        # -------------------------
        results = filter_projects(
            df,
            state["city"],
            state["bhk"],
            state["budget"]
        )

        if results.empty:
            msg.body(
                "❌ Is criteria me koi project nahi mila.\n\n"
                "Budget ya city change karke try karo 🙂"
            )
        else:
            reply = "🏗 *Matching Projects*\n\n"
            for _, r in results.iterrows():
                reply += (
                    f"🏢 {r['project_name'].title()}\n"
                    f"📍 {r['city'].title()}\n"
                    f"💰 {r['price']}\n"
                    f"🔗 {r['link']}\n\n"
                )

            reply += "🔁 Agar aur options chahiye to budget / bhk change karke likho"
            msg.body(reply)

    return str(resp)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
