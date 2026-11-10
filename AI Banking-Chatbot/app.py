import csv
import io
from datetime import date, timedelta
from flask import make_response

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
import re
import uuid
from loan_data import BANK_LOAN_DATA, BANK_LOAN_TENURES


app = Flask(__name__)

app.secret_key = "replace-this-with-a-long-random-secret"



def get_banking_response(message, customer_id, account_id=None):
    message_lower = message.lower()

    connection = get_connection()

    try:
                # Retrieve the selected account belonging to the logged-in customer.
        if account_id is not None:
            try:
                account_id = int(account_id)
            except (ValueError, TypeError):
                return "Please select a valid account."

            account = connection.execute(
                """
                SELECT id, account_type, balance
                FROM bank_accounts
                WHERE id = ? AND customer_id = ?
                """,
                (account_id, customer_id)
            ).fetchone()
        else:
            # Backward-compatible fallback to the customer's first account.
            account = connection.execute(
                """
                SELECT id, account_type, balance
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
                  AND account_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 5
                """,
                (customer_id, account["id"])
            ).fetchall()

            if not transactions:
                return "You don't have any recorded transactions yet."

            lines = [f"Here are your {len(transactions)} most recent recorded transactions:"]
            for item in transactions:
                lines.append(
                    f"- {item['transaction_type']}: "
                    f"₹{item['amount']:,.2f} — "
                    f"{item['status']} ({item['description']})"
                )

            return "\n".join(lines)
        
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
        if any(phrase in message_lower for phrase in (
            "spent this month",
            "monthly spending",
            "paid this month",
            "payments this month",
            "payment this month",
            "how much have i paid",
            "how much did i pay this month",
            "total payments this month",
            "my payments this month",
            "this month's payments",
            "this months payments",
        )):
            result = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE customer_id = ?
                  AND account_id = ?
                  AND LOWER(transaction_type) LIKE '%payment%'
                  AND LOWER(status) = 'completed'
                  AND created_at >= strftime('%Y-%m-01', 'now', 'localtime')
                  AND created_at < strftime(
                      '%Y-%m-01', 'now', 'localtime', '+1 month'
                  )
                """,
                (customer_id, account["id"])
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
                "Customer-requested simulated transaction",
                account_id=account["id"]
            )

        # 7. Handle loan comparisons and bank-specific EMI requests first.
        bank_response = get_multi_bank_loan_response(message)
        if bank_response:
            return bank_response

        # 8. Generic EMI calculation (amount, rate, and tenure supplied).
        if "emi" in message_lower:
            parsed = parse_emi_inputs(message)
            if parsed is None:
                return (
                    "To calculate a standalone EMI, provide the loan amount, "
                    "annual interest rate, and tenure. Example: Calculate EMI "
                    "for ₹5,00,000 at 9% for 5 years. For a bank comparison, "
                    "ask: Compare home loan EMI for ₹25 lakh over 20 years."
                )

            principal, annual_rate, years = parsed
            emi = calculate_emi(principal, annual_rate, years)
            months = round(years * 12)
            total_payment = emi * months
            total_interest = total_payment - principal

            return (
                "### Estimated Loan EMI\\n\\n"
                f"**Loan amount:** ₹{principal:,.2f}\\n"
                f"**Annual interest rate:** {annual_rate:.2f}%\\n"
                f"**Repayment period:** {years:g} years\\n"
                f"**Monthly EMI:** ₹{emi:,.2f}\\n"
                f"**Total interest:** ₹{total_interest:,.2f}\\n"
                f"**Total repayment:** ₹{total_payment:,.2f}\\n\\n"
                "This is an estimate, not a confirmed bank loan offer."
            )

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
         "money stolen", "someone stole", "suspicious transaction",
        "someone accessed my account", "account accessed",
        "someone has accessed", "unauthorized access", "unauthorised access"
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

    
    # 7. Debit and credit card information and management guidance
    elif "credit card" in message or "credit cards" in message:
        if any(term in message for term in (
            "eligibility", "eligible", "qualify", "qualification",
            "apply", "application", "documents", "requirements"
        )):
            return (
                "### Credit Card Eligibility and Application\n\n"
                "| Area | General guidance |\n"
                "|---|---|\n"
                "| Eligibility | Banks may consider age, income, employment, credit history, existing debt and repayment capacity. |\n"
                "| Documents | Common requirements may include PAN, identity/address proof, income proof and bank statements. Requirements vary. |\n"
                "| Application | Apply through the bank's official website, app or branch. Provide documents only through official channels. |\n"
                "| Approval | These are general guidelines, not guaranteed eligibility or approval. The bank makes the final decision. |\n\n"
                "### Credit Card Features\n\n"
                "| Feature | Explanation |\n"
                "|---|---|\n"
                "| Credit limit | The maximum borrowing limit assigned by the issuer. |\n"
                "| Billing cycle | The period during which card transactions are recorded. |\n"
                "| Payment due date | Pay at least the required amount by the due date; paying the full statement balance can help avoid interest on ordinary purchases. Terms vary. |\n"
                "| Interest and fees | Rates, annual fees, late fees and other charges depend on the card and issuer. |\n\n"
                "Never share your PIN, CVV, OTP or password. This project does not issue real credit or guarantee approval."
            )

        elif any(term in message for term in (
            "manage", "management", "lock", "unlock", "block",
            "lost", "stolen", "safety", "secure", "fraud", "status"
        )):
            return (
                "### Credit Card Safety and Management\n\n"
                "| Action | Guidance |\n"
                "|---|---|\n"
                "| View status | Check the card displayed in your profile. |\n"
                "| Lost or stolen | Immediately lock/block the card using the issuer's official app or helpline. |\n"
                "| Suspicious transaction | Contact the issuer promptly and raise a dispute through its official channel. |\n"
                "| Protect details | Never disclose your PIN, CVV, OTP or password. |\n"
                "| This chatbot | Card records here are simulated; it cannot block a real bank-issued card. |\n\n"
                "For credit-card eligibility, application requirements or features, ask me specifically about that topic."
            )

        else:
            return (
                "### Credit Card Overview\n\n"
                "| Feature | Credit Card |\n"
                "|---|---|\n"
                "| How it works | Uses a credit limit provided by the issuer. |\n"
                "| Repayment | Transactions appear on a statement and must be repaid according to its terms. |\n"
                "| Interest | Interest and fees may apply depending on the balance and card terms. |\n"
                "| Approval | Subject to the bank's eligibility checks and final decision. |\n\n"
                "You can ask about credit-card eligibility, application documents, features or safety."
            )

    elif "debit card" in message or "debit cards" in message:
        if any(term in message for term in (
            "feature", "features", "difference", "compare", "comparison"
        )):
            return (
                "### Debit Card Features\n\n"
                "| Feature | Explanation |\n"
                "|---|---|\n"
                "| Funding | Transactions generally use money in the linked bank account. |\n"
                "| ATM access | May support cash withdrawals, subject to card and account limits. |\n"
                "| Purchases | Can be used for supported online and in-store purchases. |\n"
                "| Spending limit | Depends on bank settings, available balance and card limits. |\n"
                "| Fees | Charges and limits vary by issuer and card type. |\n\n"
                "### Debit Card vs Credit Card\n\n"
                "| Area | Debit Card | Credit Card |\n"
                "|---|---|---|\n"
                "| Money source | Linked account balance | Issuer-provided credit limit |\n"
                "| Repayment | Normally no separate monthly credit bill | Statement repayment required |\n"
                "| Approval | Depends on account/card issuance rules | Subject to credit-card eligibility checks |\n"
            )

        elif any(term in message for term in (
            "manage", "management", "lock", "unlock", "block",
            "lost", "stolen", "safety", "secure", "fraud", "status"
        )):
            return (
                "### Debit Card Safety and Management\n\n"
                "| Action | Guidance |\n"
                "|---|---|\n"
                "| View status | Check the card displayed in your profile. |\n"
                "| Lost or stolen | Immediately lock/block it through your bank's official app or helpline. |\n"
                "| Suspicious transaction | Contact your bank promptly and report unauthorised activity. |\n"
                "| Protect details | Never disclose your PIN, CVV, OTP or password. |\n"
                "| This chatbot | Card records here are simulated; it cannot block a real bank-issued card. |\n"
            )

        else:
            return (
                "A debit card normally uses funds from your linked bank account. "
                "You can view its masked identifier and status in your profile. "
                "Ask about debit-card features, safety, management or the "
                "difference between debit and credit cards."
            )

    # Other card-related questions
    elif "card" in message or "cards" in message:
        return (
            "You can add simulated debit and credit cards from the card section "
            "on your dashboard. Use fictional details only. For lost or stolen "
            "real cards, contact your bank immediately through its official "
            "app or helpline. Never share your PIN, CVV, OTP or password."
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


def process_transaction(
    customer_id,
    transaction_type,
    amount,
    description,
    account_id=None
):
    if amount <= 0:
        return "Please enter an amount greater than zero."

    connection = get_connection()

    try:
        # Prevent simultaneous transactions from corrupting balances.
        connection.execute("BEGIN IMMEDIATE")

        # Retrieve only the selected account belonging to this customer.
        if account_id is not None:
            try:
                account_id = int(account_id)
            except (ValueError, TypeError):
                connection.rollback()
                return "Please select a valid account."

            account = connection.execute(
                """
                SELECT id, balance
                FROM bank_accounts
                WHERE id = ? AND customer_id = ?
                """,
                (account_id, customer_id)
            ).fetchone()
        else:
            # Backward-compatible fallback for existing callers.
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

        # Update only the selected account owned by this customer.
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

def parse_emi_inputs(message):
    """Parse explicit generic EMI inputs, including lakh/crore amounts."""
    amount_and_years = parse_loan_amount_and_years(message)
    rate_match = re.search(r"\b(?:at|rate(?:\s+of)?)\s*(\d+(?:\.\d+)?)\s*%", message.lower())
    if amount_and_years and rate_match:
        amount, years = amount_and_years
        rate = float(rate_match.group(1))
        return amount, rate, years

    # Plain numeric form: ₹500000 at 9% for 5 years.
    text = message.lower().replace(",", "")
    amount_match = re.search(r"(?:₹|rs\.?\s*)\s*(\d+(?:\.\d+)?)", text)
    rate_match = re.search(r"\b(\d+(?:\.\d+)?)\s*%", text)
    years_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", text)
    if amount_match and rate_match and years_match:
        return (
            float(amount_match.group(1)),
            float(rate_match.group(1)),
            float(years_match.group(1)),
        )
    return None


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




def parse_loan_amount_and_years(message):
    """Extract an amount (including lakh/crore) and a tenure in years."""
    text = message.lower().replace(",", "")
    amount_match = re.search(
        r"(?:₹|rs\.?\s*)\s*(\d+(?:\.\d+)?)\s*(lakh| lakhs| lac| lacs|crore|crores|cr)?",
        text
    )
    if not amount_match:
        # Also accept forms such as "25 lakh loan".
        amount_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|crore|crores|cr)\b",
            text
        )
    years_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", text
    )
    if not amount_match or not years_match:
        return None
    amount = float(amount_match.group(1))
    unit = (amount_match.group(2) or "").strip()
    if unit in ("lakh", "lakhs", "lac", "lacs"):
        amount *= 100_000
    elif unit in ("crore", "crores", "cr"):
        amount *= 10_000_000
    years = float(years_match.group(1))
    if amount <= 0 or years <= 0:
        return None
    return amount, years


def get_multi_bank_loan_response(message):
    message_lower = message.lower().strip()

    loan_type_patterns = [
        ("education loan", ("education loan", "student loan")),
        ("home loan", ("home loan", "housing loan")),
        ("car loan", ("car loan", "vehicle loan", "auto loan")),
        ("personal loan", ("personal loan",)),
    ]
    loan_type = next(
        (category for category, phrases in loan_type_patterns
         if any(phrase in message_lower for phrase in phrases)),
        None
    )
    if not loan_type:
        return None

    bank_aliases = {
        "SBI": ("sbi", "state bank of india"),
        "ICICI Bank": ("icici",),
        "Axis Bank": ("axis",),
        "HDFC Bank": ("hdfc",),
        "Kotak Mahindra Bank": ("kotak",),
    }
    selected_banks = [
        bank for bank, aliases in bank_aliases.items()
        if any(re.search(r"\b" + re.escape(alias) + r"\b", message_lower)
               for alias in aliases)
    ]
    compare_requested = any(
        phrase in message_lower
        for phrase in ("compare", "comparison", "all banks", "all bank",
                       "across banks", "across available banks")
    )
    banks_to_check = (
        list(BANK_LOAN_DATA.keys())
        if compare_requested or not selected_banks else selected_banks
    )
    tenure_requested = any(
        phrase in message_lower
        for phrase in ("tenure", "repayment period", "repayment tenure",
                       "repayment duration", "how long", "repay",
                       "repayment", "duration")
    )
    # A loan EMI comparison uses each bank's configured calculation rate.
    if "emi" in message_lower and (compare_requested or len(selected_banks) > 1):
        inputs = parse_loan_amount_and_years(message)
        if inputs is None:
            # Rates are still useful without an amount and tenure.
            lines = [
                f"### {loan_type.title()} — Bank Rate Comparison",
                "",
                "| Bank | Indicative rate |",
                "|---|---|",
            ]
            for bank in banks_to_check:
                details = BANK_LOAN_DATA.get(bank, {}).get(loan_type, {})
                rate = details.get("rate_display")
                if rate:
                    lines.append(f"| {bank} | {rate} |")
            lines.extend([
                "",
                "To calculate EMIs, include the loan amount and tenure, "
                "for example: Compare home loan EMI for ₹25 lakh over 20 years.",
                "Rates are indicative and must be verified with each bank.",
            ])
            return "\n".join(lines)

        amount, years = inputs
        months = round(years * 12)
        lines = [
            f"### {loan_type.title()} — EMI Comparison",
            "",
            f"Loan amount: ₹{amount:,.2f} | Tenure: {years:g} years",
            "",
            "| Bank | Calculation rate | Monthly EMI | Total interest |",
            "|---|---:|---:|---:|",
        ]
        for bank in banks_to_check:
            details = BANK_LOAN_DATA.get(bank, {}).get(loan_type, {})
            rate_value = details.get("emi_rate")
            if rate_value is None:
                # A displayed range is not silently converted into a single rate.
                rate_display = details.get("rate_display", "Not configured")
                lines.append(f"| {bank} | {rate_display} | Not calculated | Not calculated |")
                continue
            rate = float(rate_value)
            emi = calculate_emi(amount, rate, years)
            total_interest = emi * months - amount
            lines.append(
                f"| {bank} | {rate:.2f}% p.a. | ₹{emi:,.2f} | "
                f"₹{total_interest:,.2f} |"
            )
        lines.extend([
            "",
            "**Note:** EMI values are estimates based on the configured "
            "calculation rates, not guaranteed offers. Verify current "
            "rates, eligibility, fees, and terms with the official bank.",
        ])
        return "\n".join(lines)

    if tenure_requested:
        tenure_banks = (
            list(BANK_LOAN_TENURES.keys())
            if compare_requested or not selected_banks else selected_banks
        )
        lines = [
            f"### {loan_type.title()} — Repayment Tenure",
            "",
            "| Bank | Repayment tenure | Official source |",
            "|---|---|---|",
        ]
        for bank in tenure_banks:
            details = BANK_LOAN_DATA.get(bank, {}).get(loan_type, {})
            tenure_details = BANK_LOAN_TENURES.get(bank, {}).get(loan_type, {})
            tenure = (details.get("tenure") or tenure_details.get("tenure")
                      or "Not verified — check official source")
            source = details.get("source") or tenure_details.get("source")
            source_text = f"[Official bank page]({source})" if source else "Not configured"
            lines.append(f"| {bank} | {tenure} | {source_text} |")
        lines.extend([
            "",
            "Tenure depends on the product and bank approval. Confirm the "
            "applicable terms on the official bank page.",
        ])
        return "\n".join(lines)

    # Compact comparison: no repetitive bank-by-bank generic document lists.
    lines = [
        f"### {loan_type.title()} — Bank Comparison",
        "",
        "| Bank | Interest rate | Repayment tenure | Official source |",
        "|---|---|---|---|",
    ]
    any_data = False
    for bank in banks_to_check:
        details = BANK_LOAN_DATA.get(bank, {}).get(loan_type, {})
        tenure_details = BANK_LOAN_TENURES.get(bank, {}).get(loan_type, {})
        if not details and not tenure_details:
            continue
        any_data = True
        rate = details.get("rate_display", "Not verified")
        tenure = details.get("tenure") or tenure_details.get("tenure") or "Not verified"
        source = details.get("source") or tenure_details.get("source")
        source_text = f"[Official bank page]({source})" if source else "Not configured"
        lines.append(f"| {bank} | {rate} | {tenure} | {source_text} |")
    if not any_data:
        return f"No configured {loan_type} information is available. Check official bank websites."

    lines.extend([
        "",
        "### General preparation checklist",
        "- Eligibility may depend on income, age, credit history, repayment capacity, and product-specific conditions.",
        "- Common documents may include PAN, identity/address proof, income proof, and bank statements; loan-specific documents vary.",
        "",
        "These are general pointers, not verified bank-specific eligibility rules or complete document lists. Rates and terms can change; confirm them on the linked official pages.",
    ])
    return "\n".join(lines)


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

        # Load every account belonging to the logged-in customer.
        accounts = connection.execute(
            """
            SELECT id, account_number, account_type, balance
            FROM bank_accounts
            WHERE customer_id = ?
            ORDER BY id
            """,
            (customer_id,)
        ).fetchall()

        # Load every card belonging to the logged-in customer.
        
        cards = connection.execute(
            """
            SELECT
                cards.card_number,
                cards.card_type,
                cards.status,
                cards.expiry_month,
                cards.expiry_year,
                cards.account_id,
                bank_accounts.account_number,
                bank_accounts.account_type
            FROM cards
            JOIN bank_accounts
                ON cards.account_id = bank_accounts.id
            WHERE cards.customer_id = ?
              AND bank_accounts.customer_id = ?
            ORDER BY cards.rowid
            """,
            (customer_id, customer_id)
        ).fetchall()


        # Keep the original variables for backward compatibility.
        account = accounts[0] if accounts else None
        card = cards[0] if cards else None

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

        # Show only complaints owned by the currently logged-in customer.
        complaints = connection.execute(
            """
            SELECT id, category, query, status, created_at
            FROM requests
            WHERE customer_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (customer_id,)
        ).fetchall()

        return render_template(
            "index.html",
            customer=customer,
            account=account,
            card=card,
            accounts=accounts,
            cards=cards,
            transactions=transactions,
            complaints=complaints
        )

    finally:
        connection.close()


@app.route("/statement", methods=["GET"])
def account_statement():
    if "customer_id" not in session:
        return redirect(url_for("login"))

    customer_id = session["customer_id"]

    try:
        start_date = date.fromisoformat(
            request.args.get("start_date", (date.today() - timedelta(days=30)).isoformat())
        )
        end_date = date.fromisoformat(
            request.args.get("end_date", date.today().isoformat())
        )
        account_id = int(request.args.get("account_id", "0"))
    except (ValueError, TypeError):
        return "Invalid account or date.", 400

    if start_date > end_date:
        return "Start date must be before end date.", 400

    connection = get_connection()

    try:
        accounts = connection.execute(
            """
            SELECT id, account_type, account_number, balance
            FROM bank_accounts
            WHERE customer_id = ?
            ORDER BY id
            """,
            (customer_id,)
        ).fetchall()

        if not accounts:
            return "No account found.", 404

        selected = next(
            (a for a in accounts if a["id"] == account_id),
            accounts[0]
        )
        account_id = selected["id"]

        transactions = connection.execute(
            """
            SELECT transaction_type, amount, description,
                   status, reference_number, created_at
            FROM transactions
            WHERE customer_id = ?
              AND account_id = ?
              AND status = 'Completed'
              AND date(created_at) BETWEEN ? AND ?
            ORDER BY created_at, id
            """,
            (customer_id, account_id,
             start_date.isoformat(), end_date.isoformat())
        ).fetchall()

        later = connection.execute(
            """
            SELECT transaction_type, amount
            FROM transactions
            WHERE customer_id = ?
              AND account_id = ?
              AND status = 'Completed'
              AND date(created_at) > ?
            """,
            (customer_id, account_id, end_date.isoformat())
        ).fetchall()

        def movement(txn):
            if txn["transaction_type"] == "Deposit":
                return txn["amount"]
            if txn["transaction_type"] in ("Withdrawal", "Payment"):
                return -txn["amount"]
            return 0

        current_balance = selected["balance"]
        closing_balance = current_balance - sum(
            movement(txn) for txn in later
        )
        opening_balance = closing_balance - sum(
            movement(txn) for txn in transactions
        )

        if request.args.get("download") == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow([
                "SIMULATED PROJECT STATEMENT - NOT AN OFFICIAL BANK STATEMENT"
            ])
            writer.writerow(["Account", selected["account_type"],
                             "Ending", selected["account_number"][-4:]])
            writer.writerow(["Period", start_date, "to", end_date])
            writer.writerow(["Opening Balance", f"{opening_balance:.2f}"])
            writer.writerow([])
            writer.writerow([
                "Date", "Type", "Description", "Reference",
                "Deposit", "Withdrawal/Payment"
            ])

            for txn in transactions:
                is_deposit = txn["transaction_type"] == "Deposit"
                writer.writerow([
                    txn["created_at"],
                    txn["transaction_type"],
                    txn["description"],
                    txn["reference_number"],
                    f'{txn["amount"]:.2f}' if is_deposit else "",
                    f'{txn["amount"]:.2f}' if not is_deposit else ""
                ])

            writer.writerow([])
            writer.writerow(["Closing Balance", f"{closing_balance:.2f}"])

            response = make_response("\ufeff" + output.getvalue())
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = (
                "attachment; filename=simulated_account_statement.csv"
            )
            return response

        return render_template(
            "statement.html",
            accounts=accounts,
            selected=selected,
            transactions=transactions,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            opening_balance=opening_balance,
            closing_balance=closing_balance
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
    account_id = data.get("account_id")

    if not message:
        return jsonify({
            "reply": "Please enter a banking question."
        }), 400

    # Pass the selected account to the banking response engine.
    reply = get_banking_response(
        message,
        customer_id,
        account_id=account_id
    )

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

@app.route("/accounts/add", methods=["POST"])
def add_account():
    if "customer_id" not in session:
        return redirect(url_for("login"))

    account_number = request.form.get("account_number", "").strip()
    account_type = request.form.get("account_type", "").strip()

    # Validate the fictional account identifier.
    if not re.fullmatch(r"[0-9]{8,16}", account_number):
        return "Account identifier must contain 8–16 digits.", 400

    if account_type not in ("Savings", "Current"):
        return "Please select a valid account type.", 400

    connection = get_connection()

    try:
        existing = connection.execute(
            "SELECT id FROM bank_accounts WHERE account_number = ?",
            (account_number,)
        ).fetchone()

        if existing:
            return "This account identifier already exists. Please use another.", 400

        connection.execute(
            """
            INSERT INTO bank_accounts
                (customer_id, account_number, account_type, balance)
            VALUES (?, ?, ?, ?)
            """,
            (
                session["customer_id"],
                account_number,
                account_type,
                0.00
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        app.logger.exception("Could not add account")
        return "Unable to add the account. Please try again.", 500

    finally:
        connection.close()

    return redirect(url_for("home"))


@app.route("/cards/add", methods=["POST"])
def add_card():
    if "customer_id" not in session:
        return redirect(url_for("login"))

    card_number = request.form.get("card_number", "").strip()
    card_type = request.form.get("card_type", "").strip()
    account_id_text = request.form.get("account_id", "").strip()
    expiry_month_text = request.form.get("expiry_month", "").strip()
    expiry_year_text = request.form.get("expiry_year", "").strip()

    if not re.fullmatch(r"[0-9]{4}", card_number):
        return "Card identifier must contain exactly 4 digits.", 400

    if card_type not in ("Debit", "Credit"):
        return "Please select a valid card type.", 400

    try:
        account_id = int(account_id_text)
        expiry_month = int(expiry_month_text)
        expiry_year = int(expiry_year_text)
    except (ValueError, TypeError):
        return "Please enter valid account and expiry details.", 400

    from datetime import datetime
    current_year = datetime.now().year

    if not 1 <= expiry_month <= 12:
        return "Expiry month must be between 1 and 12.", 400

    if not current_year <= expiry_year <= current_year + 15:
        return "Please enter a valid expiry year.", 400

    connection = get_connection()

    try:
        account = connection.execute(
            """
            SELECT id FROM bank_accounts
            WHERE id = ? AND customer_id = ?
            """,
            (account_id, session["customer_id"])
        ).fetchone()

        if not account:
            return "Please select an account belonging to your profile.", 400

        existing_card = connection.execute(
            "SELECT id FROM cards WHERE card_number = ?",
            (card_number,)
        ).fetchone()

        if existing_card:
            return "This card identifier already exists. Please use another.", 400

        connection.execute(
            """
            INSERT INTO cards
                (customer_id, account_id, card_number, card_type,
                 status, expiry_month, expiry_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["customer_id"],
                account_id,
                card_number,
                card_type,
                "Active",
                expiry_month,
                expiry_year
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        app.logger.exception("Could not add card")
        return "Unable to add the card. Please try again.", 500

    finally:
        connection.close()

    return redirect(url_for("home"))

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


@app.route("/credit-eligibility", methods=["GET", "POST"])
def credit_eligibility():
    if "customer_id" not in session:
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        bank = request.form.get("bank", "").strip()
        occupation = request.form.get("occupation", "").strip()
        age_text = request.form.get("age", "").strip()
        income_text = request.form.get("annual_income", "").strip()
        credit_history = request.form.get("credit_history", "").strip()
        repayments = request.form.get("repayments", "").strip()

        errors = []

        if bank not in ("SBI", "HDFC Millennia", "Axis SELECT", "ICICI"):
            errors.append("Please select a valid bank or card.")

        if occupation not in ("Salaried", "Self-employed", "Student", "Other"):
            errors.append("Please select a valid occupation.")

        try:
            age = int(age_text)
            if not 18 <= age <= 100:
                raise ValueError
        except ValueError:
            age = None
            errors.append("Enter a valid age.")

        try:
            annual_income = float(income_text)
            if annual_income < 0:
                raise ValueError
        except ValueError:
            annual_income = None
            errors.append("Enter a valid annual income.")

        if credit_history not in ("Good", "Limited", "Poor", "Unknown"):
            errors.append("Please select your credit history.")

        if repayments not in ("On time", "Missed payments", "None", "Unknown"):
            errors.append("Please select your repayment history.")

        if errors:
            result = {
                "status": "Please check your answers",
                "details": errors
            }
        else:
            checks = []
            criteria_not_met = False

            if bank == "SBI":
                if occupation == "Salaried":
                    checks.append(
                        "SBI Card's published guidance generally lists "
                        "a minimum age of 21 for salaried applicants."
                    )
                    if age < 21:
                        checks.append(
                            "Your age is below that published minimum."
                        )
                elif occupation == "Self-employed":
                    checks.append(
                        "SBI Card's published guidance generally lists "
                        "a minimum age of 25 for self-employed applicants."
                    )
                    if age < 25:
                        checks.append(
                            "Your age is below that published minimum."
                        )
                else:
                    checks.append(
                        "The selected occupation does not establish "
                        "that you meet SBI Card's usual applicant criteria."
                    )

                checks.append(
                    "Income thresholds depend on the specific SBI Card. "
                    "Stable income and positive credit history may be considered."
                )

            elif bank == "HDFC Millennia":
                checks.append(
                    "Published Millennia criteria list an age range "
                    "of 21–40 years."
                )

                if not 21 <= age <= 40:
                    criteria_not_met = True
                    checks.append(
                        "Your age is outside the published range."
                    )
                else:
                    checks.append(
                        "Your age is within the published range."
                    )

                if occupation == "Salaried":
                    checks.append(
                        "Published criteria list gross monthly income "
                        "above ₹35,000 for salaried applicants."
                    )

                    if annual_income <= 420000:
                        criteria_not_met = True
                        checks.append(
                            "Your stated annual income does not exceed "
                            "₹4,20,000, the annual equivalent of ₹35,000 "
                            "per month."
                        )
                    else:
                        checks.append(
                            "Your stated annual income exceeds "
                            "₹4,20,000, the annual equivalent of "
                            "₹35,000 per month."
                        )

                elif occupation == "Self-employed":
                    checks.append(
                        "Published criteria list ITR income above "
                        "₹6 lakh per year for self-employed applicants."
                    )

                    if annual_income <= 600000:
                        criteria_not_met = True
                        checks.append(
                            "Your stated annual income does not exceed "
                            "₹6 lakh."
                        )
                    else:
                        checks.append(
                            "Your stated annual income exceeds ₹6 lakh. "
                            "The bank may also assess your ITR."
                        )

                else:
                    checks.append(
                        "The published salaried and self-employed "
                        "criteria do not establish eligibility for "
                        "your selected employment type."
                    )

            elif bank == "Axis SELECT":
                checks.append(
                    "Published SELECT card criteria list age 18–70 "
                    "and minimum annual net income of ₹6 lakh."
                )
                if not 18 <= age <= 70:
                    checks.append(
                        "Your age is outside the published range."
                    )
                if annual_income < 600000:
                    checks.append(
                        "Your stated annual income is below ₹6 lakh."
                    )

            elif bank == "ICICI":
                checks.append(
                    "ICICI Bank assesses applications using factors "
                    "including income, credit history and repayment records. "
                    "A universal minimum income for every ICICI card "
                    "cannot be established from these general criteria."
                )

            if credit_history == "Poor":
                checks.append(
                    "A poor credit history may reduce approval chances."
                )
            elif credit_history == "Limited":
                checks.append(
                    "Limited credit history may mean the bank needs "
                    "more information."
                )
            elif credit_history == "Unknown":
                checks.append(
                    "Your credit history is unknown, so this checker "
                    "cannot assess that factor."
                )

            if repayments == "Missed payments":
                checks.append(
                    "Missed repayments may affect the bank's assessment."
                )
            elif repayments == "Unknown":
                checks.append(
                    "Your repayment record has not been established."
                )

            if repayments == "None":
                checks.append(
                    "Having no previous loan or card repayments does "
                    "not automatically mean rejection."
                )

            if criteria_not_met:
                result_status = "Some criteria may not be met"
            elif bank in ("HDFC Millennia", "Axis SELECT"):
                result_status = "Checked criteria appear to be met"
            else:
                result_status = "Preliminary guidance only"

            result = {
                "status": result_status,
                "details": checks + [
                    "This is not a credit score check, bank pre-approval "
                    "or guaranteed eligibility decision.",
                    "Verify the latest criteria on the issuer's official "
                    "website before applying."
                ]
            }

    return render_template(
        "credit_eligibility.html",
        result=result
    )

if __name__ == "__main__":
    app.run(debug=True, port=5001)