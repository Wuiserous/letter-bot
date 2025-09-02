# razorpay_handler.py
import os

import razorpay
from dotenv import load_dotenv

load_dotenv()

# --- RAZORPAY CONFIGURATION ---
# IMPORTANT: Replace with your actual keys from the Razorpay Dashboard
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

# IMPORTANT: Replace with the Plan ID you created in your Razorpay Dashboard
PLAN_ID = "plan_RCa5DBhCUQgZFS"  # e.g., plan_ABC123xyz


def create_one_time_payment_link(user_id: int, amount_in_inr: float, reason: str):
    """
    Creates a ONE-TIME Razorpay Payment Link.
    This is perfect for the initial payment or while waiting for mandate approval.
    """
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        amount_in_paise = int(amount_in_inr * 100)

        link_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": reason,
            "notes": {
                # The critical piece for tracking who paid
                "telegram_user_id": str(user_id)
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False
        }
        payment_link = client.payment_link.create(link_data)
        return payment_link.get('short_url')
    except Exception as e:
        print(f"Error creating Razorpay one-time payment link: {e}")
        return None


def create_subscription_link(user_id: int):
    """
    Creates a Razorpay Subscription for a user and returns the authorization link.
    """
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        subscription_data = {
            "plan_id": PLAN_ID,
            "total_count": 120,  # Authorize for 10 years of monthly payments
            "quantity": 1,
            "notes": {
                # This is the most important part for tracking who paid.
                "telegram_user_id": str(user_id)
            },
            "customer_notify": 1,
            "notify_info": {
                "notify_phone": False,
                "notify_email": False
            }
        }

        subscription = client.subscription.create(subscription_data)

        # The 'short_url' is the link the user needs to click to authorize the mandate
        return subscription.get('short_url')

    except Exception as e:
        print(f"Error creating Razorpay subscription link: {e}")
        return None