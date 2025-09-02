# database_handler.py
import os
import sqlite3
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_FILE = 'bot_database.db'


def get_user_status(user_id: int):
    """Checks a user's status in the local SQLite database. Very fast."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT subscription_status, subscription_expiry_date FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return {"status": "not_found"}

        current_status, expiry_date_str = user_data

        # Auto-expiry logic
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        if datetime.now() > expiry_date and current_status != "expired":
            cursor.execute("UPDATE users SET subscription_status = 'expired' WHERE user_id = ?", (user_id,))
            conn.commit()
            current_status = "expired"

        conn.close()
        return {"status": current_status, "expiry_date": expiry_date_str}

    except Exception as e:
        print(f"Error getting user status from SQLite: {e}")
        return {"status": "error", "message": str(e)}


def register_new_user(user_id: int, username: str):
    """Adds a new user to the SQLite database with a 30-day trial."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        trial_start_date = datetime.now()
        trial_expiry_date = trial_start_date + timedelta(days=30)

        cursor.execute('''
            INSERT INTO users (user_id, username, trial_start_date, subscription_status, subscription_expiry_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (
        user_id, username, trial_start_date.strftime("%Y-%m-%d"), "trial", trial_expiry_date.strftime("%Y-%m-%d")))

        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.IntegrityError:
        # This happens if the user_id (primary key) already exists. Safe to ignore.
        conn.close()
        return {"status": "exists"}
    except Exception as e:
        print(f"Error registering new user in SQLite: {e}")
        conn.close()
        return {"status": "error", "message": str(e)}


def log_activity(letter_type: str, recipient_name: str, recipient_email: str, sent_by: str, status: str):
    """Logs a record to the activity_log table in SQLite."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO activity_log (timestamp, letter_type, recipient_name, recipient_email, sent_by, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, letter_type, recipient_name, recipient_email, sent_by, status))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging activity to SQLite: {e}")
        return False


CLIENT_SCRIPT_URL = os.environ.get("CLIENT_SCRIPT_URL")


def fetch_student_from_client_sheet(name: str):
    """
    Fetches intern details by calling the client's Google Apps Script URL.
    """
    try:
        params = {'action': 'findStudent', 'name': name}
        response = requests.get(CLIENT_SCRIPT_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return data
        else:
            print(f"Client's Sheet API Error: {data.get('message')}")
            return None
    except Exception as e:
        print(f"HTTP Request to client's sheet failed: {e}")
        return None