

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
import re
import uuid
from loan_data import BANK_LOAN_DATA, BANK_LOAN_TENURES


app = Flask(__name__)

app.secret_key = "replace-this-with-a-long-random-secret"



def get_banking_response(message, customer_id):
    message_lower = message.lower()

    connection = get_connection()

    try:
        # Always retrieve data belonging to the logged-in customer.
        account = connection.execute(
            """
            SELECT account_type, balance
            FROM bank_accounts
            WHERE customer_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

        if not account:
            return "I couldn't find an account linked to your profile."
              
                # Handle complaint registration and tracking.
       
        complaint_response = handle_complaint_request(
            message,
            customer_id
        )

        if complaint_response is not None:
            return complaint_response

        # 1. Current account balance
        if "balance" in message_lower:
            return (
                f"Your current simulated account balance is "
                f"₹{account['balance']:,.2f}."
            )

        # 2. Account type
        if "account type" in message_lower or "which account" in message_lower:
            return f"Your account type is {account['account_type']}."

        # 3. Recent transaction history
        if "transaction" in message_lower or "recent activity" in message_lower:
            transactions = connection.execute(
                """
                SELECT transaction_type, amount, description,
                       status, created_at
                FROM transactions
                WHERE customer_id = ?
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (customer_id,)
            ).fetchall()

            if not transactions:
                return "You don't have any recorded transactions yet."

            lines = ["Here are your 5 most recent recorded transactions:"]
            for item in transactions:
                lines.append(
                    f"- {item['transaction_type']}: "
                    f"₹{item['amount']:,.2f} — "
                    f"{item['status']} ({item['description']})"
                )

            return "\n".join(lines)

        # 4. Spending this month
        if "spent this month" in message_lower or "monthly spending" in message_lower:
            result = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE customer_id = ?
                  AND LOWER(transaction_type) LIKE '%payment%'
                  AND LOWER(status) = 'completed'
                  AND created_at >= strftime('%Y-%m-01', 'now', 'localtime')
                  AND created_at < strftime('%Y-%m-01', 'now', 'localtime', '+1 month')
                """,
                (customer_id,)
            ).fetchone()

            return (
                f"Your recorded completed payments this month total "
                f"₹{result['total']:,.2f}. This counts transactions "
                f"labelled as payments in the app."
            )

        # 5. Calculate a hypothetical purchase without deducting money
        if any(phrase in message_lower for phrase in (
            "what remains", "if i spend", "if i pay",
            "after spending", "remaining after"
        )):
            amounts = re.findall(
                r"(?:₹|rs\.?\s*)?\s*([\d,]+(?:\.\d{1,2})?)",
                message_lower
            )

            if not amounts:
                return "Please include the amount, for example: What remains if I spend ₹2,500?"

            amount = float(amounts[0].replace(",", ""))

            if amount <= 0:
                return "Please enter an amount greater than zero."

            remaining = account["balance"] - amount

            if remaining < 0:
                return (
                    f"Your current balance is ₹{account['balance']:,.2f}. "
                    f"A payment of ₹{amount:,.2f} would exceed that balance "
                    f"by ₹{abs(remaining):,.2f}. No money has been deducted."
                )

            return (
                f"Your current balance is ₹{account['balance']:,.2f}. "
                f"After a hypothetical payment of ₹{amount:,.2f}, "
                f"you would have ₹{remaining:,.2f} remaining. "
                f"This is only a calculation; no payment was made."
            )

        
        # 6. Process simulated transactions
        if any(word in message_lower for word in (
            "deposit", "withdraw", "make a payment", "pay ₹",
            "pay rs", "transfer"
        )):
            amounts = re.findall(
                r"(?:₹|rs\.?\s*)?\s*([\d,]+(?:\.\d{1,2})?)",
                message_lower
            )

            if not amounts:
                return (
                    "Please specify an amount. For example: "
                    "Deposit ₹1,000, Withdraw ₹500, or Make a payment of ₹200."
                )

            amount = float(amounts[0].replace(",", ""))

            if "deposit" in message_lower:
                transaction_type = "Deposit"
            elif "withdraw" in message_lower:
                transaction_type = "Withdrawal"
            else:
                transaction_type = "Payment"

            return process_transaction(
                customer_id,
                transaction_type,
                amount,
                "Customer-requested simulated transaction"
            )

        # 7. Calculate loan EMI
        if "emi" in message_lower:
            emi_message = message_lower.replace(",", "")
            numbers = re.findall(r"\d+(?:\.\d+)?", emi_message)

            if len(numbers) < 3:
                return (
                    "Please provide the loan amount, annual interest rate, "
                    "and repayment period in years. Example: "
                    "Calculate EMI for a ₹5,00,000 loan at 9% for 5 years."
                )

            principal = float(numbers[0].replace(",", ""))
            annual_rate = float(numbers[1].replace(",", ""))
            years = float(numbers[2].replace(",", ""))

            if principal <= 0 or annual_rate < 0 or years <= 0:
                return (
                    "Please enter a loan amount greater than zero, "
                    "a non-negative interest rate, and a repayment "
                    "period greater than zero."
                )

            emi = calculate_emi(principal, annual_rate, years)
            total_payment = emi * years * 12
            total_interest = total_payment - principal

            return (
                "Estimated Loan EMI\n"
                f"Loan Amount: ₹{principal:,.2f}\n"
                f"Annual Interest Rate: {annual_rate}%\n"
                f"Repayment Period: {years:g} years\n"
                f"Monthly EMI: ₹{emi:,.2f}\n"
                f"Total Interest: ₹{total_interest:,.2f}\n"
                f"Total Repayment: ₹{total_payment:,.2f}\n\n"
                "This is an estimate, not a confirmed bank loan offer."
            )

                # 8. Multi-bank loan information
        bank_response = get_multi_bank_loan_response(message)

        if bank_response:
            return bank_response

        # 9. Keep the existing general banking responses
        return get_general_banking_response(message)

    finally:
        connection.close()
    
def handle_complaint_request(message, customer_id):
    message_lower = message.lower().strip()

    # Check whether the customer wants to track an existing complaint.
    reference_match = re.search(
        r"\bCMP-(\d{6,})\b",
        message,
        re.IGNORECASE
    )

    tracking_requested = reference_match or any(
        phrase in message_lower
        for phrase in (
            "track complaint",
            "complaint status",
            "status of my complaint",
            "check my complaint",
            "track my complaint"
        )
    )

    connection = get_connection()

    try:
        # Track a complaint using its reference number.
        if tracking_requested:
            if reference_match:
                complaint_id = int(reference_match.group(1))

                complaint = connection.execute(
                    """
                    SELECT id, category, query, status, created_at
                    FROM requests
                    WHERE id = ? AND customer_id = ?
                    """,
                    (complaint_id, customer_id)
                ).fetchone()

                if not complaint:
                    return (
                        "I couldn't find a complaint with that reference "
                        "under your account. Check the reference number "
                        "and try again."
                    )

                return (
                    f"Complaint Reference: CMP-{complaint['id']:06d}\n"
                    f"Category: {complaint['category']}\n"
                    f"Status: {complaint['status']}\n"
                    f"Submitted: {complaint['created_at']}\n"
                    "This status belongs to the project's local complaint "
                    "database; it is not a real bank complaint status."
                )

            complaints = connection.execute(
                """
                SELECT id, category, status, created_at
                FROM requests
                WHERE customer_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (customer_id,)
            ).fetchall()

            if not complaints:
                return (
                    "You don't have any complaints registered in this "
                    "chatbot yet. You can say: Register a complaint about "
                    "a failed UPI payment."
                )

            lines = ["Your 5 most recent chatbot complaints:"]
            for complaint in complaints:
                lines.append(
                    f"- CMP-{complaint['id']:06d} | "
                    f"{complaint['category']} | "
                    f"{complaint['status']} | "
                    f"{complaint['created_at']}"
                )

            lines.append(
                "\nTo check one, enter: Track complaint CMP-000001 "
                "(use your actual reference number)."
            )
            return "\n".join(lines)

        # Register a complaint only when the customer asks to do so.
        registration_requested = any(
            phrase in message_lower
            for phrase in (
                "register a complaint",
                "raise a complaint",
                "file a complaint",
                "submit a complaint",
                "lodge a complaint",
                "make a complaint",
                "register complaint",
                "raise complaint",
                "file complaint",
                "submit complaint",
                "lodge complaint",
                "i want to complain",
                "i want to complaint"
            )
        )

        if not registration_requested:
            return None

        # Assign a category based on the issue described.
        if any(word in message_lower for word in ("upi", "payment", "transfer")):
            category = "UPI/Payments"
        elif any(word in message_lower for word in ("card", "debit card", "credit card")):
            category = "Card"
        elif any(word in message_lower for word in ("atm", "cash withdrawal")):
            category = "ATM"
        elif any(word in message_lower for word in ("fraud", "scam", "unauthorised", "unauthorized")):
            category = "Fraud/Security"
        elif "loan" in message_lower or "emi" in message_lower:
            category = "Loans"
        else:
            category = "General Banking"

        cursor = connection.execute(
            """
            INSERT INTO requests (
                customer_id, category, query, ai_response, status
            )
            VALUES (?, ?, ?, ?, 'Pending')
            """,
            (
                customer_id,
                category,
                message.strip(),
                "Complaint saved in the chatbot's local database."
            )
        )

        complaint_id = cursor.lastrowid
        connection.commit()

        return (
            "Your complaint has been registered in the chatbot successfully.\n"
            f"Complaint Reference: CMP-{complaint_id:06d}\n"
            f"Category: {category}\n"
            "Status: Pending\n\n"
            "Save your reference number. You can check the recorded status "
            f"by typing: Track complaint CMP-{complaint_id:06d}\n\n"
            "Important: This is a local project record, not a complaint "
            "submitted to a real bank. Do not include your PIN, OTP, CVV, "
            "password, or other banking credentials in complaint messages."
        )

    except Exception:
        connection.rollback()
        app.logger.exception("Complaint handling failed")
        return (
            "I couldn't process that complaint request right now. "
            "Please try again. For an urgent banking or fraud issue, "
            "contact your bank through its official channel."
        )

    finally:
        connection.close()





def get_general_banking_response(message):
    message = message.lower().strip()

    # 1. Fraud and suspicious activity
    if any(word in message for word in (
        "fraud", "scam", "phishing", "account hacked",
        "unauthorised transaction", "unauthorized transaction",
        "money stolen", "someone stole", "suspicious transaction"
    )):
        return (
            "URGENT: If you suspect banking fraud, contact your bank "
            "immediately through its official helpline or app and ask "
            "them to secure your account and block affected payment "
            "methods. In India, report financial cyber fraud by calling "
            "1930 or visiting https://www.cybercrime.gov.in/. Keep your "
            "transaction reference and evidence. Never share your OTP, "
            "PIN, CVV, or password. This chatbot cannot report fraud "
            "to your bank."
        )

    # 2. KYC guidance
    elif any(word in message for word in (
        "kyc", "know your customer", "update my kyc",
        "kyc update", "kyc documents"
    )):
        return (
            "For KYC updates, use your bank's official app, website, "
            "or branch. Accepted identity and address documents depend "
            "on your bank and the type of update required. Confirm the "
            "requirements through an official channel. Never share "
            "document images, OTPs, PINs, or passwords in this chatbot."
        )

    # 3. Complaint registration and tracking guidance
    elif any(word in message for word in (
        "complaint", "grievance", "track complaint",
        "complaint status", "register a complaint",
        "raise a complaint", "file a complaint"
    )):
        return (
            "This chatbot does not yet register or track real complaints. "
            "Contact your bank through its official grievance-redressal "
            "channel and keep the complaint reference number. If the "
            "issue remains unresolved, follow the bank's escalation "
            "procedure. In India, eligible unresolved complaints may "
            "be escalated through the RBI's official Complaint "
            "Management System: https://cms.rbi.org.in/."
        )

    # 4. Pending or disputed payments
    elif any(word in message for word in (
        "pending", "money debited but",
        "debited but not received", "double charged",
        "duplicate payment", "wrong transaction",
        "disputed transaction", "dispute transaction",
        "payment not received", "amount deducted",
        "amount was deducted", "deducted twice"
    )):
        return (
            "For a pending or disputed payment, check the transaction "
            "status in your official banking or payment app. Record "
            "the amount, date, and transaction reference. If money was "
            "debited but the payment failed or the recipient did not "
            "receive it, follow your bank's official complaint process. "
            "Avoid repeating the payment until you confirm its status. "
            "Reversal times depend on the transaction type and bank."
        )

    # 5. Lost or stolen cards
    elif any(word in message for word in (
        "lost card", "card lost", "stolen card", "card stolen",
        "block card", "block my card", "card missing",
        "lost my atm card", "lost my debit card",
        "lost my credit card"
    )):
        return (
            "If your card is lost or stolen, immediately block it using "
            "your bank's official app, helpline, or branch. Check recent "
            "transactions and report any unauthorised activity. Request "
            "a replacement through your bank. This chatbot cannot block "
            "or replace a real card."
        )

    # 6. ATM problems
    elif any(word in message for word in (
        "atm", "cash not received", "cash not dispensed",
        "atm deducted", "atm withdrawal failed",
        "atm swallowed", "cash withdrawal"
    )):
        return (
            "For an ATM problem, check your account and transaction "
            "status. If money was debited but cash was not dispensed, "
            "record the date, amount, ATM location, and transaction "
            "reference, then report it through your bank's official "
            "channel. If the ATM retained your card, contact your "
            "bank immediately. This chatbot cannot reverse ATM "
            "transactions."
        )

    # 7. Other card questions
    elif any(word in message for word in (
        "card", "debit card", "credit card",
        "replace card", "card replacement",
        "card blocked", "card declined"
    )):
        return (
            "For card declines, blocking, or replacement requests, "
            "check your card status and follow the instructions in "
            "your bank's official app or contact its helpline. Never "
            "share your card PIN, CVV, OTP, or full card details here. "
            "This chatbot cannot change the status of a real card."
        )

    # 8. UPI failures
    elif any(word in message for word in (
        "upi", "payment failed", "failed payment",
        "upi transfer", "upi id", "gpay", "google pay",
        "phonepe", "paytm"
    )):
        return (
            "For a failed UPI payment, check the transaction status "
            "in your official UPI or banking app. If money was debited, "
            "check whether the payment is pending, failed, or completed "
            "before retrying. Save the transaction reference and use "
            "the app's official help or dispute option if needed. "
            "Never share your UPI PIN or OTP."
        )

    # 9. Password, PIN and OTP safety
    elif any(word in message for word in (
        "password", "otp", "one-time password", "pin",
        "cvv", "forgot password", "reset password"
    )):
        return (
            "Never share your OTP, PIN, CVV, password, or banking "
            "credentials with anyone, including people claiming to "
            "be bank staff. To reset a password, use your bank's "
            "official recovery process. If you shared credentials "
            "or suspect someone has access to your account, contact "
            "your bank immediately through an official channel."
        )

    # 10. Digital banking and login problems
    elif any(word in message for word in (
        "internet banking", "mobile banking", "net banking",
        "online banking", "login issue", "login problem",
        "can't log in", "cannot log in", "unable to login",
        "app not working", "banking app not working"
    )):
        return (
            "For digital banking problems, check your internet "
            "connection and ensure you are using your bank's official "
            "app or website. Update the app if needed and use the "
            "official password-recovery process for login issues. "
            "Never share your password or OTP. If the issue continues, "
            "contact your bank's official support team."
        )

    # 11. Bank statements
    elif any(word in message for word in (
        "statement", "bank statement", "account statement",
        "download statement", "transaction history statement"
    )):
        return (
            "You can usually download or view bank statements through "
            "your bank's official app or internet banking, or request "
            "one at a branch. Available periods and formats depend on "
            "your bank. This chatbot does not fetch official bank "
            "statements; it only displays limited simulated account "
            "information and transaction history."
        )

    # 12. Education loans
    elif any(word in message for word in (
        "education loan", "student loan"
    )):
        return (
            "Education loans can help eligible students fund approved "
            "education expenses. Eligibility, interest rates, collateral "
            "requirements, repayment holidays, and repayment periods "
            "vary by bank and scheme. Ask me to compare available bank "
            "information or calculate an estimated EMI. Confirm current "
            "terms with the bank before applying."
        )

    # 13. Home loans
    elif "home loan" in message:
        return (
            "Home-loan interest rates, eligibility, fees, and repayment "
            "periods depend on the bank and product. You can ask me to "
            "compare home loans across supported banks or calculate an "
            "estimated EMI. Figures are indicative, not a loan offer."
        )

    # 14. Personal loans
    elif "personal loan" in message:
        return (
            "Personal-loan rates, eligible amounts, fees, and repayment "
            "periods depend on the bank and applicant. You can ask me "
            "about available bank information or request an estimated "
            "EMI. Confirm the latest terms with the bank before applying."
        )

    # 15. Car and vehicle loans
    elif any(word in message for word in (
        "car loan", "vehicle loan", "auto loan"
    )):
        return (
            "Vehicle-loan rates, eligibility, fees, and repayment "
            "periods vary by bank and vehicle. Ask me about available "
            "bank information or an estimated EMI. Check the bank's "
            "official product terms before applying."
        )

    # 16. General loan categories
    elif "loan" in message and any(word in message for word in (
        "type", "types", "available loans"
    )):
        return (
            "Common loan categories include home loans, personal loans, "
            "education loans, and car loans. Interest rates, eligibility, "
            "fees, and repayment periods depend on the specific bank "
            "and product. You can ask me about a particular loan type."
        )

    # 17. Greetings
    elif message in ("hi", "hello", "hey", "good morning",
                     "good afternoon", "good evening"):
        return (
            "Hello! I can help with simulated account information, "
            "transactions, EMI calculations, bank loan comparisons, "
            "UPI payments, cards, ATM issues, KYC, statements, "
            "digital banking, and banking security."
        )

    # 18. Default response
    else:
        return (
            "I can help with account information, simulated transactions, "
            "loan comparisons and EMI calculations, UPI payments, cards, "
            "ATM issues, fraud guidance, KYC, statements, digital banking, "
            "complaint guidance, and account security. Please ask about "
            "one of these topics."
        )


def process_transaction(customer_id, transaction_type, amount, description):
    if amount <= 0:
        return "Please enter an amount greater than zero."

    connection = get_connection()

    try:
        # Start a transaction to protect the balance from partial updates.
        connection.execute("BEGIN IMMEDIATE")

        account = connection.execute(
            """
            SELECT id, balance
            FROM bank_accounts
            WHERE customer_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

        if not account:
            connection.rollback()
            return "No account was found for your profile."

        current_balance = account["balance"]

        if transaction_type in ("Payment", "Withdrawal"):
            if amount > current_balance:
                connection.rollback()
                return (
                    f"Insufficient balance. Your current balance is "
                    f"₹{current_balance:,.2f}. No money was deducted."
                )

            new_balance = current_balance - amount

        elif transaction_type == "Deposit":
            new_balance = current_balance + amount

        else:
            connection.rollback()
            return "Invalid transaction type."

        # Update only this customer's account.
        connection.execute(
            """
            UPDATE bank_accounts
            SET balance = ?
            WHERE id = ? AND customer_id = ?
            """,
            (new_balance, account["id"], customer_id)
        )

        reference_number = "TXN" + uuid.uuid4().hex[:12].upper()

        connection.execute(
            """
            INSERT INTO transactions (
                customer_id, account_id, transaction_type,
                amount, description, status, reference_number
            )
            VALUES (?, ?, ?, ?, ?, 'Completed', ?)
            """,
            (
                customer_id,
                account["id"],
                transaction_type,
                amount,
                description,
                reference_number
            )
        )

        connection.commit()

        return (
            f"Simulated {transaction_type.lower()} completed successfully! "
            f"Amount: ₹{amount:,.2f}. "
            f"Updated balance: ₹{new_balance:,.2f}. "
            f"Reference: {reference_number}. "
            f"No real money was transferred."
        )

    except Exception:
        connection.rollback()
        app.logger.exception("Transaction processing failed")
        return "The transaction could not be completed. No change was saved."

    finally:
        connection.close()

def calculate_emi(principal, annual_rate, years):
    if principal <= 0 or annual_rate < 0 or years <= 0:
        return None

    months = round(years * 12)
    monthly_rate = annual_rate / (12 * 100)

    if monthly_rate == 0:
        return principal / months

    factor = (1 + monthly_rate) ** months

    emi = principal * monthly_rate * factor / (factor - 1)

    return emi


def get_multi_bank_loan_response(message):
    message_lower = message.lower().strip()

    loan_types = [
        "personal loan",
        "home loan",
        "education loan",
        "student loan",
        "car loan",
        "vehicle loan",
    ]

    loan_type = next(
        (item for item in loan_types if item in message_lower),
        None,
    )

    if not loan_type:
        return None

    if loan_type == "student loan":
        loan_type = "education loan"
    elif loan_type == "vehicle loan":
        loan_type = "car loan"

    bank_aliases = {
        "SBI": ["sbi", "state bank of india"],
        "ICICI Bank": ["icici"],
        "Axis Bank": ["axis"],
        "HDFC Bank": ["hdfc"],
        "Kotak Mahindra Bank": ["kotak"],
    }

    selected_banks = [
        bank
        for bank, aliases in bank_aliases.items()
        if any(alias in message_lower for alias in aliases)
    ]

    compare_requested = any(
        word in message_lower
        for word in ("compare", "comparison", "all banks")
    )

    # Handle loan repayment-tenure questions first.
    tenure_requested = any(
        phrase in message_lower
        for phrase in (
            "tenure",
            "repayment period",
            "repayment tenure",
            "repayment duration",
            "how long",
            "repay",
            "repayment",
        )
    )

    if tenure_requested and loan_type:
        # Compare all banks when requested or when no bank is specified.
        banks_to_check = (
            list(BANK_LOAN_TENURES.keys())
            if compare_requested or not selected_banks
            else selected_banks
        )

        lines = [
            f"Repayment tenure information for {loan_type.title()}:"
        ]

        for bank in banks_to_check:
            details = BANK_LOAN_TENURES.get(bank, {}).get(loan_type)

            if not details or not details.get("tenure"):
                lines.append(
                    f"\n{bank}: A verified tenure is not available "
                    "in the chatbot's current data."
                )
                continue

            lines.append(
                f"\n{bank}: {details['tenure']}"
            )

            source = details.get("source")
            if source:
                lines.append(f"Official source: {source}")

        lines.append(
            "\nNote: Actual repayment tenure depends on the specific "
            "loan scheme, eligibility, and bank approval. Please "
            "confirm the terms with the bank."
        )

        return "\n".join(lines)


    # Compare home-loan EMIs when amount and tenure are provided.
    
    # Compare home-loan EMIs when amount and tenure are provided.
    if loan_type == "home loan" and compare_requested:
        loan_text = message_lower.replace(",", "")

        amount_match = re.search(
            r"(?:₹|rs\.?\s*)?\s*(\d+(?:\.\d+)?)\s*"
            r"(crores?|cr|lakhs?|lacs?|lac|l|k)?\b",
            loan_text,
        )
        years_match = re.search(r"(\d+(?:\.\d+)?)\s*years?\b", loan_text)

        if not amount_match or not years_match:
            return (
                "To compare home-loan EMIs, include the loan amount "
                "and repayment period. Example: "
                "Compare home loans for ₹30 lakh over 20 years."
            )

        principal = float(amount_match.group(1))
        unit = (amount_match.group(2) or "").lower()
        years = float(years_match.group(1))

        if unit in ("lakh", "lakhs", "lac", "lacs", "l"):
            principal *= 100000
        elif unit in ("crore", "crores", "cr"):
            principal *= 10000000
        elif unit == "k":
            principal *= 1000

        if principal <= 0 or years <= 0:
            return "Please enter a loan amount and repayment period greater than zero."

        comparisons = []

        for bank, products in BANK_LOAN_DATA.items():
            details = products.get("home loan")

            if not details or details.get("emi_rate") is None:
                continue

            rate = float(details["emi_rate"])
            emi = calculate_emi(principal, rate, years)

            if emi is None:
                continue

            months = round(years * 12)
            total_payment = round(emi * months, 2)
            total_interest = round(total_payment - principal, 2)

            comparisons.append({
                "bank": bank,
                "rate": rate,
                "emi": emi,
                "interest": total_interest,
                "repayment": total_payment,
                "source": details["source"],
            })

        if not comparisons:
            return "No home-loan rates are configured for comparison yet. Please check loan_data.py."

        comparisons.sort(key=lambda item: item["emi"])

        results = [
            "## HOME LOAN EMI COMPARISON",
            f"**Loan Amount:** ₹{principal:,.2f}",
            f"**Repayment Period:** {years:g} years",
            "",
            "| Bank | Rate (% p.a.) | Monthly EMI | Total Interest | Total Repayment |",
            "|:--|--:|--:|--:|--:|",
        ]

        for item in comparisons:
            results.append(
                f"| {item['bank']} "
                f"| {item['rate']:.2f}% "
                f"| ₹{item['emi']:,.2f} "
                f"| ₹{item['interest']:,.2f} "
                f"| ₹{item['repayment']:,.2f} |"
            )

        results.extend([
            "",
            f"**Lowest estimated EMI:** {comparisons[0]['bank']} "
            f"(₹{comparisons[0]['emi']:,.2f}/month)",
            "",
            "**Note:** This is an estimate based on configured interest "
            "rates, not a confirmed loan offer. Actual rates, fees, "
            "eligibility, and repayment amounts may differ.",
            "",
            "### Official Sources",
        ])

        for item in comparisons:
            results.append(f"- [{item['bank']}]({item['source']})")

        return "\n".join(results)


    if compare_requested or not selected_banks:
        selected_banks = list(BANK_LOAN_DATA.keys())

    responses = []

    for bank in selected_banks:
        details = BANK_LOAN_DATA.get(bank, {}).get(loan_type)

        if details is None:
            continue

        responses.append(
            f"{bank} — {loan_type.title()}\n"
            f"Published rate: {details['rate_display']}\n"
            f"Rate period/notes: {details['effective_period']}\n"
            f"Repayment tenure: "
            f"{details.get('tenure') or 'Not yet verified'}\n"
            f"Official source: {details['source']}"
        )

    if not responses:
        return (
            f"I don't yet have configured {loan_type} information "
            "for the requested bank. Please check the bank's "
            "official website."
        )

    return (
        "\n\n".join(responses)
        + "\n\nRates and eligibility depend on the product and "
        "customer profile. Verify current terms with the bank."
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
            SELECT id, password_hash, role, is_active
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

    # Prevent disabled customers from logging in.
    if not customer["is_active"]:
        return render_template(
            "login.html",
            error="Your account has been disabled. Please contact the administrator."
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
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    connection = get_connection()

    try:
        customer = connection.execute(
            """
            SELECT id, full_name, email, is_active
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not customer or not customer["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        account = connection.execute(
            """
            SELECT id, account_number, account_type, balance
            FROM bank_accounts
            WHERE customer_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

        card = connection.execute(
            """
            SELECT card_number, card_type, status, expiry_month, expiry_year
            FROM cards
            WHERE customer_id = ?
            ORDER BY rowid
            LIMIT 1
            """,
            (customer_id,)
        ).fetchone()

        transactions = connection.execute(
            """
            SELECT transaction_type, amount, description,
                   status, reference_number, created_at
            FROM transactions
            WHERE customer_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
            (customer_id,)
        ).fetchall()


        
        return render_template(
            "index.html",
            customer=customer,
            account=account,
            card=card,
            transactions=transactions
        )

    finally:
        connection.close()



@app.route("/chat", methods=["POST"])
def chat():
    customer_id = session.get("customer_id")

    # Require login before accessing the chatbot.
    if not customer_id:
        return jsonify({
            "reply": "Your session has expired. Please log in again."
        }), 401

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "reply": "Please enter a banking question."
        }), 400

    reply = get_banking_response(message, customer_id)
    return jsonify({"reply": reply})


@app.route("/admin/complaints", methods=["GET"])
def admin_complaints():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied. Administrator login required.", 403

    connection = get_connection()

    try:
        complaints = connection.execute(
            """
            SELECT
                requests.id,
                requests.customer_id,
                customers.full_name,
                customers.email,
                requests.category,
                requests.query,
                requests.status,
                requests.created_at
            FROM requests
            JOIN customers
                ON customers.id = requests.customer_id
            ORDER BY requests.id DESC
            """
        ).fetchall()

        return render_template(
            "admin_complaints.html",
            complaints=complaints,
            statuses=("Pending", "In Progress", "Resolved")
        )

    finally:
        connection.close()


@app.route(
    "/admin/complaints/<int:complaint_id>/status",
    methods=["POST"]
)
def update_complaint_status(complaint_id):
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied. Administrator login required.", 403

    new_status = request.form.get("status", "").strip()
    allowed_statuses = ("Pending", "In Progress", "Resolved")

    if new_status not in allowed_statuses:
        return "Invalid complaint status.", 400

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE requests
            SET status = ?
            WHERE id = ?
            """,
            (new_status, complaint_id)
        )

        connection.commit()

        if cursor.rowcount == 0:
            return "Complaint not found.", 404

        return redirect(url_for("admin_complaints"))

    except Exception:
        connection.rollback()
        app.logger.exception("Complaint status update failed")
        return "Could not update the complaint status.", 500

    finally:
        connection.close()



def get_current_admin(connection):
    """Verify admin permissions against the database, not just the session."""
    customer_id = session.get("customer_id")

    if not customer_id:
        return None

    return connection.execute(
        """
        SELECT id, email, role, is_active, is_primary_admin
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()


def record_admin_activity(
    connection, admin, action, target_customer_id=None, details=""
):
    """Record an administrator action in the local activity log."""
    connection.execute(
        """
        INSERT INTO admin_activity_log (
            admin_id, admin_email, action,
            target_customer_id, details
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            admin["id"],
            admin["email"],
            action,
            target_customer_id,
            details
        )
    )


@app.route("/admin/customers", methods=["GET"])
def admin_customers():
    if not session.get("customer_id"):
        return redirect(url_for("login"))

    connection = get_connection()

    try:
        admin = get_current_admin(connection)

        if not admin or not admin["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if admin["role"] != "admin":
            session["role"] = admin["role"]
            return "Access denied. Administrator login required.", 403

        session["role"] = admin["role"]

        customers = connection.execute(
            """
            SELECT
                customers.id,
                customers.full_name,
                customers.email,
                customers.phone_number,
                customers.role,
                customers.is_active,
                customers.is_primary_admin,
                cards.id AS card_id,
                cards.card_type,
                cards.status AS card_status,
                cards.card_number
            FROM customers
            LEFT JOIN cards
                ON cards.customer_id = customers.id
            ORDER BY customers.id, cards.id
            """
        ).fetchall()

        return render_template(
            "admin_customers.html",
            customers=customers
        )

    finally:
        connection.close()


@app.route(
    "/admin/customers/<int:customer_id>/update",
    methods=["POST"]
)
def update_customer_access(customer_id):
    if not session.get("customer_id"):
        return redirect(url_for("login"))

    action = request.form.get("action", "").strip()
    allowed_actions = {
        "disable", "enable", "grant_admin", "revoke_admin"
    }

    if action not in allowed_actions:
        return "Invalid action.", 400

    connection = get_connection()

    try:
        admin = get_current_admin(connection)

        if not admin or not admin["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if admin["role"] != "admin":
            session["role"] = admin["role"]
            return "Access denied. Administrator login required.", 403

        target = connection.execute(
            """
            SELECT id, full_name, email, role, is_active,
                   is_primary_admin
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not target:
            return "Customer not found.", 404

        if target["is_primary_admin"]:
            return "The primary administrator account is protected.", 403

        # Prevent an administrator from accidentally removing their own access.
        if target["id"] == admin["id"] and action in (
            "disable", "revoke_admin"
        ):
            return "You cannot disable or remove your own admin access.", 403

        if action == "disable":
            connection.execute(
                "UPDATE customers SET is_active = 0 WHERE id = ?",
                (customer_id,)
            )
            details = f"Disabled access for {target['email']}."

        elif action == "enable":
            connection.execute(
                "UPDATE customers SET is_active = 1 WHERE id = ?",
                (customer_id,)
            )
            details = f"Enabled access for {target['email']}."

        elif action == "grant_admin":
            connection.execute(
                "UPDATE customers SET role = 'admin' WHERE id = ?",
                (customer_id,)
            )
            details = f"Granted admin permission to {target['email']}."

        else:  # revoke_admin
            connection.execute(
                "UPDATE customers SET role = 'customer' WHERE id = ?",
                (customer_id,)
            )
            details = f"Revoked admin permission from {target['email']}."

        record_admin_activity(
            connection,
            admin,
            action,
            customer_id,
            details
        )

        connection.commit()
        return redirect(url_for("admin_customers"))

    except Exception:
        connection.rollback()
        app.logger.exception("Customer management update failed")
        return "Could not update the customer.", 500

    finally:
        connection.close()


@app.route(
    "/admin/customers/<int:customer_id>/card",
    methods=["POST"]
)
def update_customer_card(customer_id):
    if not session.get("customer_id"):
        return redirect(url_for("login"))

    action = request.form.get("action", "").strip()

    if action not in ("lock_card", "unlock_card"):
        return "Invalid card action.", 400

    connection = get_connection()

    try:
        admin = get_current_admin(connection)

        if not admin or not admin["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if admin["role"] != "admin":
            session["role"] = admin["role"]
            return "Access denied. Administrator login required.", 403

        target = connection.execute(
            """
            SELECT id, email, is_primary_admin
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not target:
            return "Customer not found.", 404

        card_status = "Blocked" if action == "lock_card" else "Active"

        cards = connection.execute(
            """
            SELECT id, status
            FROM cards
            WHERE customer_id = ?
            """,
            (customer_id,)
        ).fetchall()

        if not cards:
            return "No card is registered for this customer.", 404

        # Do not unlock expired cards or cards in an unknown status.
        if action == "unlock_card":
            invalid_cards = [
                card for card in cards
                if card["status"] not in ("Blocked", "Active")
            ]

            if invalid_cards:
                return (
                    "One or more cards have a different status and "
                    "cannot be automatically unlocked."
                ), 400

        connection.execute(
            """
            UPDATE cards
            SET status = ?
            WHERE customer_id = ?
            """,
            (card_status, customer_id)
        )

        record_admin_activity(
            connection,
            admin,
            action,
            customer_id,
            f"Set card status to {card_status} for {target['email']}."
        )

        connection.commit()
        return redirect(url_for("admin_customers"))

    except Exception:
        connection.rollback()
        app.logger.exception("Card status update failed")
        return "Could not update the card status.", 500

    finally:
        connection.close()


@app.route("/admin/activity", methods=["GET"])
def admin_activity():
    if not session.get("customer_id"):
        return redirect(url_for("login"))

    connection = get_connection()

    try:
        admin = get_current_admin(connection)

        if not admin or not admin["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if admin["role"] != "admin":
            session["role"] = admin["role"]
            return "Access denied. Administrator login required.", 403

        activities = connection.execute(
            """
            SELECT
                admin_activity_log.id,
                admin_activity_log.admin_email,
                admin_activity_log.action,
                admin_activity_log.target_customer_id,
                admin_activity_log.details,
                admin_activity_log.created_at
            FROM admin_activity_log
            ORDER BY admin_activity_log.id DESC
            LIMIT 200
            """
        ).fetchall()

        return render_template(
            "admin_activity.html",
            activities=activities
        )

    finally:
        connection.close()


@app.route("/profile", methods=["GET", "POST"])
def profile():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    connection = get_connection()

    try:
        customer = connection.execute(
            """
            SELECT id, full_name, email, phone_number, is_active
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not customer or not customer["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone_number = request.form.get("phone_number", "").strip()

            if not full_name or not email:
                return render_template(
                    "profile.html",
                    customer=customer,
                    error="Name and email are required."
                )

            if len(full_name) > 100 or len(email) > 254:
                return render_template(
                    "profile.html",
                    customer=customer,
                    error="Name or email is too long."
                )

            if phone_number and not re.fullmatch(r"[0-9+() -]{7,20}", phone_number):
                return render_template(
                    "profile.html",
                    customer=customer,
                    error="Enter a valid phone number."
                )

            try:
                connection.execute(
                    """
                    UPDATE customers
                    SET full_name = ?, email = ?, phone_number = ?
                    WHERE id = ?
                    """,
                    (full_name, email, phone_number, customer_id)
                )
                connection.commit()
            except Exception as error:
                connection.rollback()
                if "UNIQUE constraint failed: customers.email" in str(error):
                    return render_template(
                        "profile.html",
                        customer=customer,
                        error="That email address is already registered."
                    )
                raise

            return redirect(url_for("profile"))

        return render_template("profile.html", customer=customer)

    finally:
        connection.close()


@app.route("/change-password", methods=["POST"])
def change_password():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    connection = get_connection()

    try:
        customer = connection.execute(
            """
            SELECT password_hash, is_active
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not customer or not customer["is_active"]:
            session.clear()
            return redirect(url_for("login"))

        if not current_password or not new_password or not confirm_password:
            return render_template(
                "profile.html",
                customer=connection.execute(
                    """
                    SELECT id, full_name, email, phone_number, is_active
                    FROM customers
                    WHERE id = ?
                    """,
                    (customer_id,)
                ).fetchone(),
                error="Please fill in all three password fields."
            )

        if not check_password_hash(
            customer["password_hash"], current_password
        ):
            error_message = "Your current password is incorrect."

        elif len(new_password) < 8:
            error_message = "Your new password must be at least 8 characters."

        elif len(new_password) > 128:
            error_message = "Your new password must not exceed 128 characters."

        elif new_password != confirm_password:
            error_message = "The new password and confirmation do not match."

        elif new_password == current_password:
            error_message = "Your new password must differ from your current password."

        else:
            error_message = None

        if error_message:
            profile_customer = connection.execute(
                """
                SELECT id, full_name, email, phone_number, is_active
                FROM customers
                WHERE id = ?
                """,
                (customer_id,)
            ).fetchone()

            return render_template(
                "profile.html",
                customer=profile_customer,
                error=error_message
            )

        new_password_hash = generate_password_hash(new_password)

        connection.execute(
            """
            UPDATE customers
            SET password_hash = ?
            WHERE id = ?
            """,
            (new_password_hash, customer_id)
        )
        connection.commit()

        return render_template(
            "profile.html",
            customer=connection.execute(
                """
                SELECT id, full_name, email, phone_number, is_active
                FROM customers
                WHERE id = ?
                """,
                (customer_id,)
            ).fetchone(),
            success="Your password has been changed successfully."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

if __name__ == "__main__":
    app.run(debug=True, port=5001)