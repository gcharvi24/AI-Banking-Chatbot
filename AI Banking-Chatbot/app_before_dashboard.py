

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
import re


app = Flask(__name__)

app.secret_key = "replace-this-with-a-long-random-secret"


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    account_number = request.form.get("account_number", "").strip()
    card_identifier = request.form.get("card_identifier", "").strip()
    account_type = request.form.get("account_type", "")
    card_type = request.form.get("card_type", "")

    if not full_name or not email or len(password) < 8:
        return render_template(
            "register.html",
            error="Enter your name, a valid email, and a password of at least 8 characters."
        )

    if not re.fullmatch(r"[0-9]{8,16}", account_number):
        return render_template(
            "register.html",
            error="The account identifier must contain 8–16 digits."
        )

    if not re.fullmatch(r"[0-9]{4}", card_identifier):
        return render_template(
            "register.html",
            error="The card identifier must contain exactly 4 digits."
        )

    if account_type not in ("Savings", "Current"):
        return render_template("register.html", error="Choose a valid account type.")

    if card_type not in ("Debit", "Credit"):
        return render_template("register.html", error="Choose a valid card type.")

    connection = get_connection()

    try:
        existing = connection.execute(
            """
            SELECT id FROM customers
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing:
            return render_template(
                "register.html",
                error="An account with this email already exists. Please log in."
            )

        existing_account = connection.execute(
            "SELECT id FROM bank_accounts WHERE account_number = ?",
            (account_number,)
        ).fetchone()

        if existing_account:
            return render_template(
                "register.html",
                error="That account identifier is already in use. Choose another."
            )

        # Store only a hash of the password.
        cursor = connection.execute(
            """
            INSERT INTO customers (full_name, email, password_hash, role)
            VALUES (?, ?, ?, 'customer')
            """,
            (full_name, email, generate_password_hash(password))
        )
        customer_id = cursor.lastrowid

        # Initial balance is assigned by the application, not the customer.
        cursor = connection.execute(
            """
            INSERT INTO bank_accounts
                (customer_id, account_number, account_type, balance)
            VALUES (?, ?, ?, ?)
            """,
            (customer_id, account_number, account_type, 10000.00)
        )
        account_id = cursor.lastrowid

        # Store the fictional four-digit identifier in the existing card_number
        # column. It is not a real card number or a payment credential.
        connection.execute(
            """
            INSERT INTO cards
                (customer_id, account_id, card_number, card_type,
                 status, expiry_month, expiry_year)
            VALUES (?, ?, ?, ?, 'Active', 12, 2030)
            """,
            (customer_id, account_id, card_identifier, card_type)
        )

        connection.commit()

        session.clear()
        session["customer_id"] = customer_id
        session["role"] = "customer"

        return redirect(url_for("home"))

    except Exception:
        connection.rollback()
        app.logger.exception("Registration failed")
        return render_template(
            "register.html",
            error="Registration could not be completed. Check your details and try again."
        )

    finally:
        connection.close()
    
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = get_connection()

    try:
        customer = connection.execute(
            """
            SELECT id, password_hash, role
            FROM customers
            WHERE email = ?
            """,
            (email,)
        ).fetchone()
    finally:
        connection.close()

    if not customer or not check_password_hash(
        customer["password_hash"], password
    ):
        return render_template(
            "login.html",
            error="Incorrect email or password."
        )

    session.clear()
    session["customer_id"] = customer["id"]
    session["role"] = customer["role"]

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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
