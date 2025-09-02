# email_sender.py
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- SMTP SERVER CONFIGURATION ---
SMTP_SERVER = "smtpout.secureserver.net"
SMTP_PORT = 587
DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL")
DEFAULT_EMAIL_PASSWORD = os.environ.get("DEFAULT_EMAIL_PASSWORD")  # <-- Make sure this is your correct password

HR_EMAIL = os.environ.get("HR_EMAIL")
HR_EMAIL_PASSWORD = os.environ.get("HR_EMAIL_PASSWORD")

# --- BCC CONFIGURATION ---
# <-- CHANGE 1: Add your logging email address here.
# This is where you will get a copy of every email sent by the bot.
BCC_EMAIL = os.environ.get("BCC_EMAIL")


def get_email_templates(letter_type, recipient_name, domain):
    """
    Returns the appropriate email subject and HTML body based on the letter type.
    """
    # Template for Campus Ambassador
    if letter_type.lower() == "campus ambassador":
        subject = "Appointment Letter – Campus Ambassador at Persevex"
        body = f"""
        <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Greetings from Persevex!</p>
            <p>We are excited to officially welcome you as a Campus Ambassador at Persevex. Please find attached your appointment letter, which outlines your key responsibilities, benefits, and the impact you can make as part of our team.</p>
            <p>As a Campus Ambassador, you will play a vital role in building brand awareness, promoting our programs, and fostering student engagement at your institution. Your energy and initiative will be instrumental in expanding Persevex’s mission to empower learners across campuses.</p>
            <p>If you have any questions or need further clarification, feel free to reach out to us at 📧 support@persevex.com.</p>
            <p>We look forward to seeing your contributions and success in this role.</p>
            <p>📣 Feel free to share this exciting opportunity on LinkedIn by posting about your new role, tagging @Persevex and using hashtags such as #Persevex #CampusAmbassador #Leadership #StudentOpportunity #EmpoweringLearners.</p>
            <br>
            <p>Best regards,<br>
            Team Persevex<br>
            📧 support@persevex.com<br>
            🌐 www.persevex.com</p>
        </body>
        </html>
        """
        return subject, body

    elif letter_type.lower() == "internship acceptance":
        subject = "Internship Acceptance Letter at Persevex"
        body = f"""
        <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Congratulations once again!<br>
            Please find attached your official internship acceptance letter for the <b>{domain} Intern</b> role at Persevex.</p>
            <p>We’re excited to have you onboard and look forward to your contributions during this internship.</p>
            <p>If you’re comfortable, we’d love for you to share this opportunity and your experience on LinkedIn by tagging @Persevex and helping others know about us.</p>
            <br>
            <p>Best regards,<br>
            Shanmukh Shekar K C<br>
            Administrator<br>
            📧 support@persevex.com</p>
        </body>
        </html>
        """
        return subject, body
    elif letter_type.lower() == "offer letter":
        subject = f"Offer Letter for the position of Business Development Associate at Persevex."
        body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <p>Dear {recipient_name},</p>
                    <p>Greetings from Persevex Education Consultancy LLP!</p>
                    <p>Congratulations once again! Please find attached your official Offer Letter for the position of <b>Business Development Associate</b> at Persevex.</p>
                    <p>To proceed with your onboarding, kindly complete the following steps within <b>two working days</b>:</p>
                    <ol>
                        <li>Review and sign the offer letter (a digital or scanned signature is acceptable).</li>
                        <li>Email the signed offer letter along with scanned copies of the following documents:
                            <ul>
                                <li>Academic certificates: Graduation (if applicable)</li>
                                <li>A recent passport-sized photograph</li>
                                <li>A government-issued ID (Aadhaar / Voter ID / Driving License)</li>
                                <li>PAN Card and Bank Account details (Account Number and IFSC Code)</li>
                            </ul>
                        </li>
                    </ol>
                    <p>Please reply to this email with all the required documents attached.</p>
                    <p><b><u>Office Location:</u></b><br>
                    Persevex LLP<br>
                    5A, 1st A Cross Road, Dollar Scheme Colony,<br>
                    1st Stage, BTM Layout, Bengaluru, Karnataka – 560068</p>
                    <p>We are thrilled to have you onboard and look forward to your contributions to the team.</p>
                    <br>
                    <p>Warm regards,<br>
                    Bhumika Vijay Shinde<br>
                    Persevex LLP</p>
                </body>
                </html>
                """
        return subject, body
    else:
        subject = "A Letter from Persevex"
        body = f"""<p>Dear {recipient_name},</p><p>Please find your document attached.</p>"""
        return subject, body


# In email_sender.py

# In email_sender.py

def send_personalized_email(pdf_path: str, recipient_data: dict, sender_account: str = 'default'):
    """
    Connects to the SMTP server using the standard Port 587 with STARTTLS.
    This is the most compatible method for most providers.
    """
    server = None
    try:
        if sender_account == 'hr':
            sender_email = HR_EMAIL
            sender_password = HR_EMAIL_PASSWORD
        else:
            sender_email = DEFAULT_EMAIL
            sender_password = DEFAULT_EMAIL_PASSWORD

        recipient_name = recipient_data["name"]
        recipient_email = recipient_data["email"]
        domain = recipient_data["domain"]
        letter_type = recipient_data["letter_type"]

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # --- THE FIX: DELETE THIS LINE ---
        # msg["Bcc"] = BCC_EMAIL  <-- DELETE THIS LINE

        subject, html_body = get_email_templates(letter_type, recipient_name, domain)
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        # ... (PDF attachment logic remains the same)
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.is_file():
            print(f"[ERROR] PDF file not found at: {pdf_path}")
            return False
        with open(pdf_path_obj, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=f"{letter_type.replace(' ', '_')}.pdf")
        msg.attach(attachment)

        # The 'all_recipients' list is still correct and necessary
        all_recipients = [recipient_email, BCC_EMAIL]

        context = ssl.create_default_context()
        print(f"Connecting to {SMTP_SERVER} on port {SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        print("Securing connection with STARTTLS...")
        server.starttls(context=context)
        print(f"Logging in as {sender_email}...")
        server.login(sender_email, sender_password)
        print("Sending email...")

        # This function call correctly sends to both recipients without
        # adding the Bcc header to the visible message content.
        server.sendmail(sender_email, all_recipients, msg.as_string())

        print(f"Successfully sent email from {sender_email} to {recipient_name} via Port 587.")
        return True

    except smtplib.SMTPAuthenticationError:
        print(
            f"[ERROR] Login failed for {sender_email}. This means the password or username is wrong, or the provider is blocking the login.")
        return False
    except Exception as e:
        print(f"[ERROR] An error occurred while sending the email: {e}")
        return False
    finally:
        if server:
            print("Closing connection.")
            server.quit()

# recipient_data = {
#     "name": "Sayma Perween",
#     "email": "Saymaperween75@gmail.com",
#     "domain": "Marketing",            # Used only for internship template
#     "letter_type": "campus ambassador"     # One of: campus ambassador / internship acceptance / offer letter
# }
# send_personalized_email('CA_Letter_Sayma_Perween.pdf', recipient_data)