
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)


def get_banking_response(message):
    message = message.lower()

    if "upi" in message or "payment failed" in message:
        return (
            "For a failed UPI payment, check your transaction status "
            "in your banking app. If money was debited, check the bank's "
            "official guidance before retrying."
        )

    elif "atm" in message or "card" in message:
        return (
            "For ATM or card issues, check your bank's official app "
            "or customer support. If your card is lost, block it "
            "immediately through an official bank channel."
        )

    elif "balance" in message or "account" in message:
        return (
            "For your account balance, use your bank's official app, "
            "website, ATM, or another authorized banking channel."
        )

    elif "fraud" in message or "scam" in message:
        return (
            "If you suspect fraud, contact your bank immediately "
            "using its official support channel and report the "
            "transaction. Never share your PIN, OTP, or password."
        )

    elif "hello" in message or "hi" in message:
        return (
            "Hello! Welcome to the Banking Chatbot. "
            "How can I help you today?"
        )

    else:
        return (
            "I'm here to help with general banking questions. "
            "Try asking about UPI, ATM cards, account balance, or fraud."
        )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please enter a banking question."}), 400

    reply = get_banking_response(message)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
