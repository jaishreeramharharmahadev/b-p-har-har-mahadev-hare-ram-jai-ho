from flask import Flask, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfutils
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os
import io


from reportlab.lib.units import mm

import qrcode
from PIL import Image

from pypdf import PdfReader, PdfWriter
import traceback
from PIL import Image

app = Flask(__name__)

PDF_FOLDER = "generated_pdfs"
TEMPLATE_FOLDER = "templates"
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

def add_content_to_template(data):
    """Add content to the existing template PDF"""
    try:
        # Use the template PDF
        template_path = os.path.join(TEMPLATE_FOLDER, "offerLetterTemplate.pdf")
        
        if not os.path.exists(template_path):
            # Fallback to generating from scratch if template doesn't exist
            return generate_from_scratch(data)
        
        # Create a new PDF with the template as background
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
                
        # Candidate Information
        can.setFont("Helvetica", 10)
        can.drawString(50, 640, f"To: {data['full_name']}")
        can.drawString(50, 620, f"Domain: {data['domain']}")
        can.drawString(50, 600, f"Location: Online(Remote)")
        can.drawString(300, 640, f"ID: {data['unique_id']}")
        # can.drawString(50, 640, f"Date: {datetime.now().strftime('%d %B, %Y')}")
        can.drawString(300, 600, f"Start Date: {data['start_date']}")
        can.drawString(300, 620, f"Duration: {data['internship_duration']}")
        
        # Offer letter content
        y_position = 560
        content_lines = [
            f"Dear {data['full_name']},",
            "",
            f"Congratulations! We are excited to offer you the position of {data['domain']} at GT Technovation Innovations.", 
            "Your application demonstrated exceptional potential and alignment with our organization's values and objectives.",
            "",
            "This internship opportunity is designed to provide you with hands-on experience in real-world projects while working", 
            "alongside our experienced professionals. We are confident that this experience will significantly contribute to your",
            "professional development and career growth.",
            "",
            f"During your {data['internship_duration']} internship period, you will have the opportunity to work on challenging projects and contribute",
            "to meaningful solutions. We believe that your unique perspective and skills will be valuable assets to our team and",
            "and we look forward to the innovative contributions we know you will make.",            "",
            "Welcome to GT Technovation Innovations! We look forward to seeing the great work you will accomplish.",
        ]
        
        for line in content_lines:
            can.drawString(50, y_position, line)
            y_position -= 15
        
        # Terms and conditions
        y_position -= 20
        can.setFont("Helvetica-Bold", 11)
        can.drawString(50, y_position, "Terms & Conditions:")
        y_position -= 20
        can.setFont("Helvetica", 9)
        
        terms = [
            f"• Internship period: {data['internship_duration']}",
            f"• Participate in project planning and development activities",
            "• Professional conduct and performance expectations must be maintained",
            "• All company policies and procedures must be adhered to during the internship period",
            "• Successful completion may lead to certificate of completion and potential references",
            "• Provide regular progress updates to your supervisor"
        ]
        
        for term in terms:
            can.drawString(60, y_position, term)
            y_position -= 12
        
        # Company signatures
        signature_path = os.path.join("static", "signature.png")
        verify_path = os.path.join("static", "verify.png")
        
        y_position -= 30
        if os.path.exists(signature_path):
            try:
                sig_img = ImageReader(signature_path)
                can.drawImage(sig_img, 70, y_position, width=80, height=30, preserveAspectRatio=True)
            except:
                pass
        
        if os.path.exists(verify_path):
            try:
                verify_img = ImageReader(verify_path)
                can.drawImage(verify_img, 330, y_position, width=80, height=30, preserveAspectRatio=True)
            except:
                pass

        y_position -= 6

        can.setFont("Helvetica-Bold", 10)
        can.drawString(80, y_position, "Priyanshu Rose")
        can.setFont("Helvetica", 8)
        can.drawString(80, y_position - 12, "HR, Program Manager")
        
        y_position -= 100
        can.setFont("Helvetica", 8)
        can.drawString(50, y_position, f"Internship ID: {data['unique_id']}")
        can.drawString(50, y_position - 12, f"Date: {datetime.now().strftime('%d %B, %Y')}")
        can.drawString(50, y_position - 24, f"www.gttechnovation.com")
        
        can.save()
        
        # Merge template with content
        packet.seek(0)
        new_pdf = PdfReader(packet)
        
        # Read existing template
        existing_pdf = PdfReader(open(template_path, "rb"))
        output = PdfWriter()
        
        # Merge the pages
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)
        
        # Save the result
        output_path = os.path.join(PDF_FOLDER, f"{data['unique_id']}_offer_letter.pdf")
        with open(output_path, "wb") as outputStream:
            output.write(outputStream)
        
        return output_path
        
    except Exception as e:
        print(f"Error using template: {e}")
        # Fallback to generating from scratch
        return generate_from_scratch(data)

def generate_from_scratch(data):
    pass



def generate_certificate_pdf(data):
    """
    data: dict with keys:
      - fullName
      - uniqueId
      - domain
      - startDate (string)
      - endDate (string)
      - durationMonths / durationText (string)
      - certificateNumber (string, unique)
      - issueDate (string)
      - directorName (string)   # unused in layout but saved in template text
      - verifyUrl (string)  # full URL encoded into QR
    Returns path to saved PDF (temp file) or None on failure
    """
    try:
        template_path = os.path.join(TEMPLATE_FOLDER, "certificate_template.pdf")

        # Read the template to get page size and inspect fonts/resources
        reader = PdfReader(open(template_path, "rb"))
        template_page = reader.pages[0]
        mediabox = template_page.mediabox
        # pypdf mediabox values are Decimal-like; convert to float
        page_width = float(mediabox.width)
        page_height = float(mediabox.height)

        # Attempt to detect any standard font names present in the template resources.
        detected_fonts = []
        try:
            resources = template_page.get("/Resources")
            if resources:
                fonts = resources.get("/Font")
                if fonts:
                    # fonts is a dictionary-like object; extract names
                    for k, v in fonts.items():
                        fontname = str(v.get("/BaseFont", "")).replace("/", "")
                        if fontname:
                            detected_fonts.append(fontname)
        except Exception:
            # Non-fatal — font detection is a best-effort
            detected_fonts = []

        # Map detected font hints to ReportLab standard font names (best-effort)
        # If template uses "Helvetica" or "Times", prefer those.
        base_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        for fn in detected_fonts:
            n = fn.lower()
            if "times" in n or "times-roman" in n:
                base_font = "Times-Roman"
                bold_font = "Times-Bold"
                break
            if "helvetica" in n:
                base_font = "Helvetica"
                bold_font = "Helvetica-Bold"
                break
            if "courier" in n:
                base_font = "Courier"
                bold_font = "Courier-Bold"
                break
        # Fall back to default reportlab fonts if nothing matched

        # Create an overlay PDF in memory with the same size as template page
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Margins
        margin_x = 23  # points
        margin_y = 15

        # Certificate number top-right
        cert_no = data.get("certificateNumber", "")
        c.setFont(base_font, 11)
        # position near top-right with small margin
        c.drawRightString(page_width - margin_x, page_height - margin_y, f"{cert_no}")

        # Name centered prominently
        full_name = data.get("fullName", "")
        # Choose a big font size for the name; clamp between 20 and 48
        name_font_size = 36
        c.setFont(bold_font, name_font_size)
        # place name approximately in upper-middle (tweakable)
        name_y = page_height * 0.5
        c.drawCentredString((page_width / 2), name_y, full_name)

        # Domain / Title under the name (optional)
        domain = data.get("domain", "")
        if domain:
            c.setFont(base_font, 16)
            c.drawCentredString((page_width / 2) + 170, name_y - 54, domain)

        # Duratin 
        # Domain / Title under the name (optional)
        duration_text1 = data.get("durationText", "")
        if duration_text1:
            c.setFont(base_font, 16)
            c.drawCentredString((page_width / 2) - 70, name_y - 54, duration_text1)


        # Duration paragraph below the name/domain
        duration_text = data.get("durationText") or data.get("durationMonths") or ""
        start = data.get("startDate", "")
        end = data.get("endDate", "")
        # Compose a human-friendly paragraph. You can tweak wording to match your template language.
        paragraph_lines = []
        if start or end:
            # Example: "From <start> to <end>"
            if start and end:
                paragraph_lines.append(f"{start}      {end}")
            elif start:
                paragraph_lines.append(f"Start Date: {start}")
            elif end:
                paragraph_lines.append(f"End Date: {end}")

        # Draw paragraph centered, using smaller font, allowing 2 lines
        para_font = base_font
        para_font_size = 14
        c.setFont(para_font, para_font_size)
        para_start_y = name_y - 70
        for i, line in enumerate(paragraph_lines[:2]):
            c.drawCentredString((page_width / 2) + 125, para_start_y - 6, line)

        # Issued Date bottom-left
        issue_date = data.get("issueDate", "")
        c.setFont(base_font, 10)
        c.drawString(margin_x + 10, margin_y - 5, f"{issue_date}")

        # QR code bottom-right
        verify_url = data.get("verifyUrl")
        if verify_url:
            qr = qrcode.QRCode(box_size=4, border=1)
            qr.add_data(verify_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            # Resize QR to a reasonable size (e.g., 100x100 points)
            qr_size_pts = 70
            qr_img = qr_img.resize((qr_size_pts, qr_size_pts), Image.LANCZOS)
            qr_byte_arr = io.BytesIO()
            qr_img.save(qr_byte_arr, format="PNG")
            qr_byte_arr.seek(0)
            qr_reader = ImageReader(qr_byte_arr)

            qr_x = page_width - margin_x - qr_size_pts - 10
            qr_y = margin_y + 20 # put above the bottom margin
            c.drawImage(qr_reader, qr_x, qr_y, width=qr_size_pts, height=qr_size_pts, preserveAspectRatio=True, mask='auto')

        # finalize overlay canvas
        c.save()
        packet.seek(0)

        # Merge overlay with template
        overlay_pdf = PdfReader(packet)
        output = PdfWriter()

        # If template has multiple pages, we merge overlay onto first page and append others unchanged
        num_template_pages = len(reader.pages)
        for i in range(num_template_pages):
            tpage = reader.pages[i]
            if i == 0:
                # merge overlay page 0 onto template page i
                try:
                    tpage.merge_page(overlay_pdf.pages[0])
                except Exception:
                    # older/newer pypdf versions may use merge_page or merge_page; catch and try add_transformation
                    tpage.merge_page(overlay_pdf.pages[0])
            output.add_page(tpage)

        # ensure output directory exists
        CERT_FOLDER = os.path.join(PDF_FOLDER, "certificates")
        os.makedirs(CERT_FOLDER, exist_ok=True)
        out_filename = f"{cert_no}_certificate.pdf" if cert_no else f"{data.get('uniqueId','certificate')}_certificate.pdf"
        out_path = os.path.join(CERT_FOLDER, out_filename)

        with open(out_path, "wb") as f_out:
            output.write(f_out)

        return out_path

    except Exception as exc:
        print("Error generating certificate PDF:", str(exc))
        traceback.print_exc()
        return None


@app.route("/generate-offer-letter", methods=["POST"])
def generate_offer_letter():
    try:
        data = request.get_json()
        full_name = data.get("fullName")
        domain = data.get("domain")
        unique_id = data.get("uniqueId")
        internship_duration = data.get("duration", "3 Months")
        start_date = data.get("startDate", datetime.now().strftime("%d %B, %Y"))
        stipend = data.get("stipend", "Unpaid")

        if not full_name or not domain or not unique_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Prepare data for PDF generation
        pdf_data = {
            'full_name': full_name,
            'domain': domain,
            'unique_id': unique_id,
            'internship_duration': internship_duration,
            'start_date': start_date,
            'stipend': stipend
        }

        # Generate PDF using template
        pdf_path = add_content_to_template(pdf_data)

        return send_file(
            pdf_path, 
            as_attachment=True,
            download_name=f"{unique_id}_offer_letter.pdf", 
            mimetype="application/pdf"
        )

    except Exception as e:
        print("Error generating PDF:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/upload-signature", methods=["POST"])
def upload_signature():
    """Endpoint to upload signature image"""
    try:
        if 'signature' not in request.files:
            return jsonify({"error": "No signature file provided"}), 400
        
        signature_file = request.files['signature']
        if signature_file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save signature image
        signature_path = os.path.join("static", "signature.png")
        signature_file.save(signature_path)
        
        return jsonify({"message": "Signature uploaded successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload-verify", methods=["POST"])
def upload_verify():
    """Endpoint to upload verification image"""
    try:
        if 'verify' not in request.files:
            return jsonify({"error": "No verification file provided"}), 400
        
        verify_file = request.files['verify']
        if verify_file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save verification image
        verify_path = os.path.join("static", "verify.png")
        verify_file.save(verify_path)
        
        return jsonify({"message": "Verification image uploaded successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return jsonify({
        "message": "GT Technovation PDF Service - Template-Based Offer Letter Generator",
        "status": "Running",
        "version": "3.0",
        "features": [
            "Template-based PDF generation",
            "Signature image support",
            "Verification image support",
            "Dynamic content placement"
        ]
    })


# --- Flask route to generate certificate (accepts JSON and returns PDF) ---
@app.route("/generate-certificate", methods=["POST"])
def generate_certificate():
    """
    Expects JSON:
      fullName, uniqueId, domain, startDate, endDate, durationText, certificateNumber, issueDate, directorName, verifyUrl
    Returns: generated PDF bytes (application/pdf)
    """
    try:
        data = request.get_json()
        # minimal validation
        required = ["fullName", "certificateNumber", "domain", "verifyUrl"]
        for k in required:
            if not data.get(k):
                return jsonify({"error": f"Missing {k}"}), 400

        pdf_path = generate_certificate_pdf(data)
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"error": "PDF generation failed"}), 500

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{data.get('certificateNumber')}_certificate.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("Error in /generate-certificate:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route("/test-pdf")
def test_pdf():
    try:
        pdf_path = add_content_to_template({
            "full_name": "Test User",
            "domain": "Backend",
            "unique_id": "TEST001",
            "internship_duration": "3 Months",
            "start_date": "01 Jan 2025",
            "stipend": "Unpaid"
        })
        return f"PDF generated at: {pdf_path}"
    except Exception as e:
        return f"Error: {str(e)}"
    
    
if __name__ == "__main__":
    # Create static folder if it doesn't exist
    import os
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)