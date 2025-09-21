# razorpay_handler.py
import os
import time
import razorpay
from dotenv import load_dotenv

load_dotenv()

# --- RAZORPAY CONFIGURATION ---
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")


def create_payment_link(user_id: int):
    """
    Creates a ONE-TIME Razorpay Payment Link for ₹999 for 30 days of access.
    """
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        # The amount is now hardcoded to ₹999
        amount_in_paise = 999 * 100

        link_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": "30-Day Access to Telegram Bot",
            "notes": {
                # This is the most important part for tracking the user
                "telegram_user_id": str(user_id)
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
            # Link expires after 1 day
            "expire_by": int(time.time()) + 86400
        }
        payment_link = client.payment_link.create(link_data)

        return payment_link.get('short_url')

    except Exception as e:
        print(f"Error creating Razorpay one-time payment link: {e}")
        return None