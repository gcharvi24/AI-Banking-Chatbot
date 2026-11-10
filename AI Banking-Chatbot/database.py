
import sqlite3

DATABASE_NAME = "banking.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_number TEXT NOT NULL UNIQUE,
                account_type TEXT NOT NULL DEFAULT 'Savings',
                balance REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                card_number TEXT NOT NULL UNIQUE,
                card_type TEXT NOT NULL DEFAULT 'Debit',
                status TEXT NOT NULL DEFAULT 'Active',
                expiry_month INTEGER NOT NULL,
                expiry_year INTEGER NOT NULL,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id)
                    REFERENCES bank_accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                loan_type TEXT NOT NULL,
                principal REAL NOT NULL,
                annual_interest_rate REAL NOT NULL,
                tenure_months INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Illustration',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                query TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Completed',
                reference_number TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id)
                    REFERENCES bank_accounts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_account
            ON transactions(account_id, created_at);

            CREATE TABLE IF NOT EXISTS banking_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                annual_rate REAL NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                effective_date TEXT,
                verified_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                admin_email TEXT NOT NULL,
                action TEXT NOT NULL,
                target_customer_id INTEGER,
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Safely add customer-management fields to existing databases.
        customer_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(customers)"
            ).fetchall()
        }

        if "phone_number" not in customer_columns:
            connection.execute(
                "ALTER TABLE customers ADD COLUMN "
                "phone_number TEXT NOT NULL DEFAULT ''"
            )

        if "is_active" not in customer_columns:
            connection.execute(
                "ALTER TABLE customers ADD COLUMN "
                "is_active INTEGER NOT NULL DEFAULT 1"
            )

        if "is_primary_admin" not in customer_columns:
            connection.execute(
                "ALTER TABLE customers ADD COLUMN "
                "is_primary_admin INTEGER NOT NULL DEFAULT 0"
            )

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
