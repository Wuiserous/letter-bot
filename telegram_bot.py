# telegram_bot.py

import os
import re
from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, filters, ContextTypes, CallbackQueryHandler
)

from email_sender import send_personalized_email
import pdf_generator
import database_handler
import razorpay_handler
import os
from dotenv import load_dotenv

# This line reads the .env file and loads the variables into the environment
load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


# State Definitions
(
    CHOOSING_ACTION, AWAITING_PAYMENT_CONFIRMATION,
    GET_CA_NAME, GET_CA_EMAIL, CONFIRM_CA,
    GET_INTERN_NAME, CONFIRM_INTERN,
    GET_OFFER_NAME, GET_OFFER_EMAIL, GET_OFFER_TRAINING_DATE, CONFIRM_OFFER,
) = range(11)


# --- THE GATEKEEPER ---
async def gatekeeper_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Checks the user's subscription status. Returns True if they can proceed,
    False if they are blocked by the paywall.
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    status_data = database_handler.get_user_status(user_id)
    status = status_data.get("status")

    # --- THIS IS THE KEY CHANGE ---
    # If the user is new, register them and immediately show the paywall.
    if status == "not_found":
        database_handler.register_new_user(user_id, username)
        await context.bot.send_message(
            chat_id=user_id,
            text="Welcome! To get started and access all features, please subscribe for ₹999/month."
        )
        # Immediately direct them to the payment flow
        await show_paywall(update, context)
        return False # Block access until payment

    if status == "active":
        return True # User is subscribed and can proceed

    # This will now catch both expired users and newly registered users.
    if status == "expired":
        await show_paywall(update, context)
        return False

    # Handle any script or connection errors
    await context.bot.send_message(chat_id=user_id,
                                   text=f"There was an error checking your account status: {status_data.get('message', 'Unknown error')}. Please try again later.")
    return False


# --- Paywall and Payment Confirmation ---
async def show_paywall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the one-time payment message and link to the user."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.message.chat_id

    # --- THIS IS THE CORRECTED FUNCTION CALL ---
    # It now calls our new, clean function with no extra arguments.
    payment_url = razorpay_handler.create_payment_link(user_id)

    if payment_url:
        # --- TEXT AND BUTTONS ARE NOW CORRECT ---
        keyboard = [
            # The button now clearly states the action and price
            [InlineKeyboardButton("Pay ₹999 for 30 Days Access", url=payment_url)],
            [InlineKeyboardButton("✅ I've Paid, Check My Status", callback_data="check_payment_status")]
        ]
        # The message is now clear about what the payment is for
        await context.bot.send_message(
            chat_id=chat_id,
            text="Your access has expired. Please click the button below to make a one-time payment for 30 days of full access.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_PAYMENT_CONFIRMATION
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Could not create a payment link right now. Please try again later."
        )
        return CHOOSING_ACTION


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'I've Paid' button click."""
    query = update.callback_query
    await query.answer(text="Checking your status, please wait...")

    database_handler.clear_user_cache(update.effective_user.id)
    status_data = database_handler.get_user_status(update.effective_user.id)

    if status_data.get("status") == "active":
        # Remove the paywall buttons and show a confirmation.
        await query.edit_message_text(
            text=f"✅ Payment confirmed! Your subscription is now active until {status_data.get('expiry_date')}.\n\nWhat would you like to do?"
        )
        # Show the main action keyboard.
        return await show_main_options(update, context)
    else:
        # Inform the user and keep them in the payment confirmation state.
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Your subscription is not active yet. Please complete the payment. It can take a minute for our system to update after you've paid. Please try checking again shortly."
        )
        return AWAITING_PAYMENT_CONFIRMATION

# --- Bot Helper Functions ---
async def show_main_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the main action buttons to the user."""
    chat_id = update.effective_chat.id
    # If the update is from a button click, get the chat_id from the message context
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id

    keyboard = [["Campus Ambassador Letter"], ["Internship Acceptance Letter"], ["Offer Letter"]]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Please choose an action:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_ACTION


# --- Main Handlers (start, cancel, and refresh) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the /start command, running the gatekeeper first."""
    if await gatekeeper_check(update, context):
        return await show_main_options(update, context)
    else:
        # If gatekeeper fails, user is already in the payment flow.
        return AWAITING_PAYMENT_CONFIRMATION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Universal cancel command for text input."""
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    # Re-run the start command to check status and show appropriate menu/paywall
    return await start(update, context)


async def refresh_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manually clears the user's cache and re-runs the gatekeeper."""
    user_id = update.effective_user.id
    database_handler.clear_user_cache(user_id)
    await update.message.reply_text("🔄 Your account status has been refreshed from the Google Sheet.")
    return await start(update, context)


# --- Gatekeeper-wrapped Main Action Router ---
async def route_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """The central router. Runs the gatekeeper and directs the user."""
    if not await gatekeeper_check(update, context):
        return AWAITING_PAYMENT_CONFIRMATION

    user_choice = update.message.text
    if user_choice == "Campus Ambassador Letter":
        return await start_ca_flow(update, context)
    elif user_choice == "Internship Acceptance Letter":
        return await start_intern_flow(update, context)
    elif user_choice == "Offer Letter":
        return await start_offer_letter_flow(update, context)
    # If text doesn't match, just show the main options again.
    return await show_main_options(update, context)


# --- Helper to get user's name for logging ---
def get_user_display_name(update: Update) -> str:
    user = update.effective_user
    return user.full_name or user.username or f"ID:{user.id}"


# --- UNIFIED FINAL PROCESSING FUNCTION ---
async def process_and_send_letter(update: Update, context: ContextTypes.DEFAULT_TYPE, letter_type: str):
    """A single function to email the pre-generated PDF and log the activity."""
    query = update.callback_query
    await query.answer()

    # Final Authorization Check before sending
    if not await gatekeeper_check(update, context):
        await query.edit_message_text(
            text="Sorry, your subscription status changed. Please complete the payment to send letters.")
        # Clean up temporary files
        if 'pdf_path' in context.user_data and os.path.exists(context.user_data['pdf_path']):
            os.remove(context.user_data['pdf_path'])
        if 'preview_path' in context.user_data and os.path.exists(context.user_data['preview_path']):
            os.remove(context.user_data['preview_path'])
        context.user_data.clear()
        return AWAITING_PAYMENT_CONFIRMATION

    await query.edit_message_text(text="Processing and sending...")

    user_display_name = get_user_display_name(update)
    data = context.user_data
    pdf_path = data.get('pdf_path')
    email_sent = False
    recipient_data = {}

    try:
        if not pdf_path or not os.path.exists(pdf_path):
            raise FileNotFoundError("The generated PDF file could not be found. Please restart the process.")

        if letter_type == "CA":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": "Community", "letter_type": "Campus Ambassador"}
            email_sent = send_personalized_email(pdf_path, recipient_data)
        elif letter_type == "Intern":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": data['domain'], "letter_type": "Internship Acceptance"}
            email_sent = send_personalized_email(pdf_path, recipient_data)
        elif letter_type == "Offer":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": "General", "letter_type": "Offer Letter"}
            email_sent = send_personalized_email(pdf_path, recipient_data, sender_account='hr')

        if email_sent:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Success! The letter has been sent to {data['name']}.")
            database_handler.log_activity(recipient_data['letter_type'], data['name'], data['email'], user_display_name, "✅ Sent")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Failure! The email to {data['name']} could not be sent. Please check credentials and console logs.")
            database_handler.log_activity(recipient_data['letter_type'], data['name'], data['email'], user_display_name, "⚠️ Failed")

    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"An unexpected error occurred: {e}")
        database_handler.log_activity(data.get('letter_type', 'Unknown'), data.get('name', 'N/A'), data.get('email', 'N/A'), user_display_name, f"❌ Error: {e}")

    finally:
        # Clean up temporary files
        if 'pdf_path' in data and os.path.exists(data['pdf_path']):
            os.remove(data['pdf_path'])
        if 'preview_path' in data and os.path.exists(data['preview_path']):
            os.remove(data['preview_path'])
        context.user_data.clear()
        # After sending, show the main menu again.
        return await show_main_options(update, context)


# --- Conversational Flow Steps ---
async def start_ca_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Let's create a Campus Ambassador Letter. What is the candidate's full name?", reply_markup=ReplyKeyboardRemove())
    return GET_CA_NAME

async def get_ca_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Got it. What is their email address?")
    return GET_CA_EMAIL

async def get_ca_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("Generating preview...")
    try:
        pdf_path, preview_path = pdf_generator.generate_campus_ambassador_pdf_with_preview(context.user_data['name'])
        context.user_data['pdf_path'] = pdf_path
        context.user_data['preview_path'] = preview_path
        with open(preview_path, 'rb') as photo_file:
            await update.message.reply_photo(photo=photo_file)
        summary = (f"This is a preview. Shall I proceed and send the full letter to **{context.user_data['email']}**?")
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_ca")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_CA
    except Exception as e:
        await update.message.reply_text(f"An error occurred while generating the preview: {e}")
        return await show_main_options(update, context)


async def start_intern_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Let's create an Internship Acceptance Letter. What is the intern's full name?", reply_markup=ReplyKeyboardRemove())
    return GET_INTERN_NAME


async def process_intern_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    await update.message.reply_text(f"Searching for '{name}'...")
    student_data = database_handler.fetch_student_from_client_sheet(name)
    if not student_data:
        await update.message.reply_text(f"Could not find '{name}' in the Onboarding sheet.")
        return await show_main_options(update, context)
    context.user_data.update(student_data)
    await update.message.reply_text("Generating preview...")
    try:
        pdf_path, preview_path = pdf_generator.generate_internship_acceptance_pdf_with_preview(
            name=student_data['name'], month=student_data['month'], domain=student_data['domain']
        )
        context.user_data['pdf_path'] = pdf_path
        context.user_data['preview_path'] = preview_path
        with open(preview_path, 'rb') as photo_file:
            await update.message.reply_photo(photo=photo_file)
        summary = (f"This is a preview. Shall I proceed and send the full letter to **{student_data['email']}**?")
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_intern")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_INTERN
    except Exception as e:
        await update.message.reply_text(f"An error occurred while generating the preview: {e}")
        return await show_main_options(update, context)


async def start_offer_letter_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Let's create an Offer Letter. First, what is the candidate's full name?", reply_markup=ReplyKeyboardRemove())
    return GET_OFFER_NAME


async def get_offer_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Got it. Now, please provide their email address.")
    return GET_OFFER_EMAIL


async def get_offer_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("Perfect. Finally, what is the training start date? (e.g., DD-MM-YYYY)")
    return GET_OFFER_TRAINING_DATE


async def get_offer_training_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['training_from'] = update.message.text.strip()
    await update.message.reply_text("Generating preview...")
    try:
        pdf_path, preview_path = pdf_generator.generate_offer_letter_pdf_with_preview(
            name=context.user_data['name'], training_from=context.user_data['training_from']
        )
        context.user_data['pdf_path'] = pdf_path
        context.user_data['preview_path'] = preview_path
        with open(preview_path, 'rb') as photo_file:
            await update.message.reply_photo(photo=photo_file)
        summary = (
            f"This is a preview. The full letter will be sent from the **HR email** to **{context.user_data['email']}**. Shall I proceed?")
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_offer")],
                    [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_OFFER
    except Exception as e:
        await update.message.reply_text(f"An error occurred while generating the preview: {e}")
        return await show_main_options(update, context)


async def cancel_final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the final 'No, Cancel' button click."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(text="Operation cancelled.")
    except BadRequest as e:
        # Ignore error if the message was not modified
        if "Message is not modified" not in e.message:
            raise
    # Clean up temporary files
    if 'pdf_path' in context.user_data and os.path.exists(context.user_data['pdf_path']):
        os.remove(context.user_data['pdf_path'])
    if 'preview_path' in context.user_data and os.path.exists(context.user_data['preview_path']):
        os.remove(context.user_data['preview_path'])
    context.user_data.clear()
    # Show the main menu again.
    return await show_main_options(update, context)


# --- Main Application Setup ---
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    action_buttons_regex = "^(Campus Ambassador Letter|Internship Acceptance Letter|Offer Letter)$"

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("refresh", refresh_status),
            MessageHandler(filters.Regex(action_buttons_regex), route_action)
        ],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex(action_buttons_regex), route_action)
            ],
            AWAITING_PAYMENT_CONFIRMATION: [
                CallbackQueryHandler(handle_payment_confirmation, pattern="^check_payment_status$"),
                CommandHandler("refresh", refresh_status),
            ],
            GET_CA_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ca_name)],
            GET_CA_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ca_email)],
            CONFIRM_CA: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "CA"), pattern="^send_ca$")],

            GET_INTERN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_intern_name)],
            CONFIRM_INTERN: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "Intern"), pattern="^send_intern$")],

            GET_OFFER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_offer_name)],
            GET_OFFER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_offer_email)],
            GET_OFFER_TRAINING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_offer_training_date)],
            CONFIRM_OFFER: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "Offer"), pattern="^send_offer$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel_final_confirmation, pattern="^cancel_final$")
        ],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("refresh", refresh_status))
    application.run_polling()


if __name__ == "__main__":
    main()