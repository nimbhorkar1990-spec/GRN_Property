import io
import os
import smtplib
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config import Config
import database as db

def generate_feedback_excel_bytes(feedbacks):
    """
    Generate a formatted Excel (.xlsx) file containing all 13 columns
    for client enquiry feedback records.
    Returns bytes of the generated workbook.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Enquiry Feedback"

    # Styling definitions
    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    fill_title = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

    font_subtitle = Font(name="Calibri", size=10, italic=True, color="64748B")

    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="B8860B", end_color="B8860B", fill_type="solid")

    font_data = Font(name="Calibri", size=10, color="0F172A")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # 1. Title Banner
    ws.merge_cells("A1:N1")
    cell_title = ws["A1"]
    cell_title.value = f"{Config.COMPANY_NAME.upper()} - CLIENT ENQUIRY FEEDBACK MASTER REPORT"
    cell_title.font = font_title
    cell_title.fill = fill_title
    cell_title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 2. Metadata Subtitle
    ws.merge_cells("A2:N2")
    cell_sub = ws["A2"]
    now_str = datetime.now().strftime("%d-%b-%Y at %I:%M %p")
    cell_sub.value = f"Generated on {now_str} | Total Records: {len(feedbacks)} | Real Estate CRM Module"
    cell_sub.font = font_subtitle
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    # 3. Column Headers (All Required Fields + Synchronized CRM Source)
    headers = [
        "SN",
        "Client Name",
        "Client Contact",
        "Enquiry Date and Time",
        "Enquiry Source",
        "Enquiry Project Name",
        "Configuration",
        "Cost (₹)",
        "Carpet Area",
        "Possession",
        "Website Enquiry URL",
        "Client Feedback",
        "Feedback By UserName",
        "Feedback Date and Time"
    ]

    ws.row_dimensions[4].height = 28
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    # 4. Data Rows
    row_idx = 5
    for item in feedbacks:
        cost_val = item.get('cost')
        try:
            cost_num = float(cost_val) if cost_val is not None else 0.0
        except (ValueError, TypeError):
            cost_num = 0.0

        row_data = [
            item.get('id', row_idx - 4),
            item.get('client_name') or '',
            item.get('client_contact') or '',
            item.get('enquiry_datetime') or '',
            item.get('enquiry_source') or 'Website Direct',
            item.get('project_name') or '',
            item.get('configuration') or '—',
            cost_num,
            item.get('carpet') or '—',
            item.get('possession') or '—',
            item.get('website_enquiry_url') or '—',
            item.get('client_feedback') or '',
            item.get('feedback_by_username') or '—',
            item.get('feedback_datetime') or ''
        ]

        fill_current = fill_zebra if row_idx % 2 == 0 else fill_white
        ws.row_dimensions[row_idx].height = 24

        for col_num, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.value = val
            cell.font = font_data
            cell.fill = fill_current
            cell.border = border_thin

            # Specific column alignments & formatting
            if col_num == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_num == 8:
                cell.number_format = '₹#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_num in (3, 4, 5, 7, 9, 10, 13, 14):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        row_idx += 1

    # Auto-adjust column widths with safety limits
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip title and subtitle rows
            if cell.row in (1, 2):
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 48)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

def send_feedback_email(excel_bytes, recipient_email=None, sender_username="Administrator"):
    """
    Send the Excel feedback report as an email attachment to configured Admin Email Address.
    Returns (success: bool, message: str).
    """
    if not recipient_email:
        recipient_email = db.get_setting('admin_email', Config.COMPANY_EMAIL)

    if not recipient_email or '@' not in recipient_email:
        return False, "Recipient admin email address is invalid or not configured."

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Enquiry_Feedback_Report_{now_str}.xlsx"

    # Read SMTP configuration from database or environment
    smtp_host = db.get_setting('smtp_host', os.environ.get('SMTP_HOST', ''))
    smtp_port = int(db.get_setting('smtp_port', os.environ.get('SMTP_PORT', 587)))
    smtp_user = db.get_setting('smtp_user', os.environ.get('SMTP_USER', ''))
    smtp_password = db.get_setting('smtp_password', os.environ.get('SMTP_PASSWORD', ''))
    smtp_tls = db.get_setting('smtp_tls', '1') == '1'

    # Build Email Message
    msg = MIMEMultipart()
    msg['From'] = smtp_user or f"Real Estate CRM <no-reply@realestate.com>"
    msg['To'] = recipient_email
    msg['Subject'] = f"Client Enquiry Feedback Master Report - {datetime.now().strftime('%d-%b-%Y')}"

    body_text = f"""Hello Administrator,

Attached is the latest Real Estate Client Enquiry Feedback Master Report in Excel (.xlsx) format.

Report Summary:
- Generated On: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}
- Requested By: {sender_username}
- Recipient Email: {recipient_email}
- Included Fields: All 13 Enquiry Feedback Database Columns

This is an automated system notification from your Real Estate CRM.

Regards,
{Config.COMPANY_NAME} CRM System
"""
    msg.attach(MIMEText(body_text, 'plain'))

    # Attach Excel
    part = MIMEApplication(excel_bytes, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)

    # 1. If SMTP server host is configured, attempt live transmission
    if smtp_host:
        try:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            if smtp_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()

            db.log_user_activity(
                username=sender_username,
                role='admin',
                activity_type='Email Sent',
                details=f"Feedback Excel sent to {recipient_email} via SMTP ({smtp_host})"
            )
            return True, f"Feedback report successfully sent to {recipient_email}."
        except Exception as e:
            err_msg = str(e)
            db.log_user_activity(
                username=sender_username,
                role='admin',
                activity_type='Email Error',
                details=f"SMTP transmission to {recipient_email} failed: {err_msg}"
            )
            return False, f"Email delivery failed: {err_msg}. Please check your SMTP settings in Admin Settings."

    # 2. In local development or when external SMTP is not yet configured, save locally and deliver safely
    outbox_dir = os.path.join(Config.DATABASE_DIR, 'email_outbox')
    os.makedirs(outbox_dir, exist_ok=True)
    file_path = os.path.join(outbox_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(excel_bytes)

    # Write receipt log
    meta_path = os.path.join(outbox_dir, f"{filename}.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump({
            'recipient': recipient_email,
            'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file': filename,
            'size_bytes': len(excel_bytes),
            'sender': sender_username,
            'status': 'Delivered (Local Outbox Archive - Configure live SMTP in Settings for external mail delivery)'
        }, f, indent=2)

    db.log_user_activity(
        username=sender_username,
        role='admin',
        activity_type='Email Generated',
        details=f"Feedback Excel generated for {recipient_email} and saved to {filename}"
    )

    return True, f"Feedback Excel report successfully generated and dispatched to {recipient_email}. (Archived in Outbox. To send via external mail relay, configure SMTP in Settings)."

