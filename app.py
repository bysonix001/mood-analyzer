import streamlit as st
import json
import os
from datetime import datetime
from fpdf import FPDF
import stripe

# ---------------- CONFIG ----------------
DATA_FILE = "mood_history.json"
REPORT_DIR = "reports"
REPORT_FILE = os.path.join(REPORT_DIR, "mood_report.pdf")

PRICE_NZD = 700  # Stripe uses cents

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")  # Optional if you later use products

if not STRIPE_SECRET_KEY:
    st.error("Missing STRIPE_SECRET_KEY environment variable.")
    st.stop()

stripe.api_key = STRIPE_SECRET_KEY

os.makedirs(REPORT_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def load_entries():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def save_entries(entries):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

def generate_pdf(entries):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Personal Mood Report", ln=True)
    pdf.ln(5)

    for e in entries[-30:]:
        line = f"{e['timestamp']} | Mood: {e['mood']} | Note: {e['note']}"
        pdf.multi_cell(0, 8, line)
        pdf.ln(1)

    pdf.output(REPORT_FILE)

def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "nzd",
                "product_data": {
                    "name": "Personal Mood Report (PDF)"
                },
                "unit_amount": PRICE_NZD,
            },
            "quantity": 1,
        }],
        success_url="http://localhost:8501/?paid=true",
        cancel_url="http://localhost:8501/",
    )
    return session.url

# ---------------- UI ----------------
st.set_page_config(
    page_title="Mood Analyzer",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Mood Analyzer")

entries = load_entries()

# ---------------- MOOD ENTRY ----------------
st.subheader("Log Your Mood")

mood = st.selectbox(
    "How are you feeling?",
    ["Great", "Good", "Okay", "Low", "Very Low"]
)

note = st.text_area("Notes (optional)")

if st.button("Save Entry"):
    entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mood": mood,
        "note": note
    })
    save_entries(entries)
    st.success("Mood saved.")

# ---------------- PAYMENT + PDF ----------------
st.divider()
st.subheader("📄 Personal Mood Report")

query = st.query_params
paid = query.get("paid", ["false"])[0] == "true"

if paid:
    generate_pdf(entries)

    with open(REPORT_FILE, "rb") as f:
        st.download_button(
            label="⬇️ Download Your PDF",
            data=f,
            file_name="mood_report.pdf",
            mime="application/pdf"
        )
else:
    st.write("Generate a downloadable PDF summary of your recent moods.")
    if st.button("Pay $7 NZD & Download PDF"):
        checkout_url = create_checkout_session()
        st.markdown(f"[Click here to pay]({checkout_url})", unsafe_allow_html=True)

st.caption("Self-reflection tool. Not medical advice.")
