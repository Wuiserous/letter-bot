# pdf_generator.py

import fitz  # PyMuPDF
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


# --- HELPER FUNCTION FOR PREVIEW GENERATION ---
def _create_preview_from_pdf(pdf_path: str) -> str:
    """
    Takes a path to a PDF, saves its first page as a PNG image,
    and returns the path to the new image.
    """
    preview_image_path = pdf_path.replace(".pdf", ".png")
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]  # Get the first page
        pix = page.get_pixmap(dpi=150)  # Render page to an image with good resolution
        pix.save(preview_image_path)
        doc.close()
        return preview_image_path
    except Exception as e:
        print(f"Error creating preview image: {e}")
        return ""


# --- UPDATED PDF GENERATION FUNCTIONS WITH PREVIEW ---

def generate_campus_ambassador_pdf_with_preview(name: str) -> tuple[str, str]:
    """Generates the CA PDF and a preview image of the first page."""
    # Step 1: Generate the full PDF as before
    TEMPLATE_PATH = "templates/campus_ambassador.pdf"
    output_path = f"CA_Letter_{name.replace(' ', '_')}.pdf"

    NAME_COORDS = (110, 244)
    DATE_COORDS = (423, 245)
    current_date = datetime.now().strftime("%B %d, %Y")

    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]
    page_1.insert_text(NAME_COORDS, name, fontsize=18, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(DATE_COORDS, current_date, fontsize=14, fontname="helv", color=(0, 0, 0))

    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=1)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview from the generated PDF
    preview_path = _create_preview_from_pdf(output_path)
    return output_path, preview_path


def generate_internship_acceptance_pdf_with_preview(name: str, month: str, domain: str) -> tuple[str, str]:
    """Generates the Internship PDF and a preview image."""
    # Step 1: Generate the full PDF as before
    domain_to_template_map = {
        "artificial intelligence": "templates/ai-internship.pdf", "machine learning": "templates/ml-internship.pdf",
        "web development": "templates/wd-internship.pdf", "cybersecurity": "templates/cs-internship.pdf",
        "data science": "templates/ds-internship.pdf", "digital marketing": "templates/dm-internship.pdf",
        "human resourses": "templates/hr-internship.pdf", "finance": "templates/fi-internship.pdf",
        "financial modeling & analysis": "templates/fi-internship.pdf",
        "financial modeling & valuation": "templates/fi-internship.pdf",
        "cloud computing": "templates/cc-internship.pdf",
    }
    clean_domain = domain.strip().lower()
    template_path = domain_to_template_map.get(clean_domain)
    if not template_path:
        raise ValueError(f"No template found for domain: '{domain}'")
    try:
        current_year = datetime.now().year
        start_month_date = datetime.strptime(f"10 {month} {current_year}", "%d %B %Y")
        from_date = start_month_date.strftime("%d-%m-%Y")
        to_date_obj = start_month_date + relativedelta(months=2)
        to_date = to_date_obj.strftime("%d-%m-%Y")
    except ValueError:
        raise ValueError(f"Invalid month format from sheet: '{month}'")

    output_path = f"Internship_Letter_{name.replace(' ', '_')}.pdf"
    NAME_COORDS, FROM_DATE_COORDS, TO_DATE_COORDS = (262, 307), (365, 560), (448, 560)

    doc = fitz.open(template_path)
    page = doc[0]
    page.insert_text(NAME_COORDS, name, fontsize=12, fontname="helv", color=(0, 0, 0))
    page.insert_text(FROM_DATE_COORDS, from_date, fontsize=11, fontname="helv", color=(0, 0, 0))
    page.insert_text(TO_DATE_COORDS, to_date, fontsize=11, fontname="helv", color=(0, 0, 0))
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    # Step 2: Create the preview
    preview_path = _create_preview_from_pdf(output_path)
    return output_path, preview_path


def generate_offer_letter_pdf_with_preview(name: str, training_from: str) -> tuple[str, str]:
    """Generates the Offer Letter PDF and a preview image."""
    # Step 1: Generate the full PDF as before
    TEMPLATE_PATH = "templates/offer_letter.pdf"
    output_path = f"Offer_Letter_{name.replace(' ', '_')}.pdf"
    NAME_COORDS, TODAY_DATE_COORDS = (91, 293), (94, 253)
    TRAINING_DATES_COORDS, INTERNSHIP_START_COORDS, INTERNSHIP_END_COORDS = (136, 374), (170, 401), (163, 428)

    todays_date = datetime.now().strftime("%d-%m-%Y")
    try:
        training_from_obj = datetime.strptime(training_from, "%d-%m-%Y")
        training_to_obj = training_from_obj + timedelta(days=10)
        internship_start_obj = training_to_obj + timedelta(days=1)
        internship_end_obj = internship_start_obj + relativedelta(months=6)
        training_to = training_to_obj.strftime("%d-%m-%Y")
        internship_start = internship_start_obj.strftime("%d-%m-%Y")
        internship_end = internship_end_obj.strftime("%d-%m-%Y")
        training_dates_text = f"{training_from} to {training_to}"
    except ValueError:
        raise ValueError("Invalid date format. Please use DD-MM-YYYY.")

    template_doc = fitz.open(TEMPLATE_PATH)
    page_1 = template_doc[0]
    page_1.insert_text(NAME_COORDS, name, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(TODAY_DATE_COORDS, todays_date, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(TRAINING_DATES_COORDS, training_dates_text, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(INTERNSHIP_START_COORDS, internship_start, fontsize=10, fontname="helv", color=(0, 0, 0))
    page_1.insert_text(INTERNSHIP_END_COORDS, internship_end, fontsize=10, fontname="helv", color=(0, 0, 0))

    output_doc = fitz.open()
    output_doc.insert_pdf(template_doc, from_page=0, to_page=2)
    output_doc.save(output_path, garbage=4, deflate=True)
    template_doc.close()
    output_doc.close()

    # Step 2: Create the preview
    preview_path = _create_preview_from_pdf(output_path)
    return output_path, preview_path

