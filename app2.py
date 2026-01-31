from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

from DB.models import init_db, get_user, save_user
from DATA.projects import load_projects
from NLP.extractor import extract_entities
from SERVICES.filter_service import filter_projects

app = Flask(__name__)

# Init DB & Data
init_db()
df = load_projects()

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    from_number = request.values.get("From", "")
    incoming = request.values.get("Body", "").strip().lower()

    resp = MessagingResponse()
    msg = resp.message()

    row = get_user(from_number)
    state = {"city": None, "bhk": None, "budget": None}
    if row:
        state["city"], state["bhk"], state["budget"] = row

    city, bhk, budget = extract_entities(incoming)
    if city: state["city"] = city
    if bhk: state["bhk"] = bhk
    if budget: state["budget"] = budget

    save_user(from_number, state["city"], state["bhk"], state["budget"])

    if incoming in ["hi", "hello", "menu", "start"]:
        msg.body(
            "👋 *Welcome to RealEstate Bot*\n\n"
            "• 2 bhk in noida under 75 lakh\n"
            "• 3 bhk gurgaon under 1 crore"
        )
    elif state["city"] and state["bhk"] and state["budget"]:
        results = filter_projects(df, state["city"], state["bhk"], state["budget"])
        if results.empty:
            msg.body("❌ No matching projects found.")
        else:
            reply = "🏗 *Matching Projects*\n\n"
            for _, r in results.iterrows():
                reply += (
                    f"🏢 {r['project_name'].title()}\n"
                    f"💰 {r['price']}\n"
                    f"🔗 {r['link']}\n\n"
                )
            msg.body(reply)
    else:
        msg.body("📍 City → 🏠 BHK → 💰 Budget")

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
