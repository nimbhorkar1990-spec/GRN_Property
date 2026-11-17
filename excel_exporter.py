import os
import csv
import json
import sqlite3
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config import Config
import database as db

def style_worksheet(ws, title, header_bg="1A1D24", header_fg="D4AF37"):
    """Apply styling: title row, headers, borders, and auto column widths."""
    # Header styling
    header_fill = PatternFill(start_color=header_bg, end_color=header_bg, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color=header_fg)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )

    # Style header row (Row 1)
    ws.row_dimensions[1].height = 28
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align

    # Style data rows and auto-fit column widths
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        ws.row_dimensions[row[0].row].height = 22
        for cell in row:
            cell.border = thin_border
            if not cell.alignment.horizontal:
                cell.alignment = left_align

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if '\n' in val_str:
                val_str = max(val_str.split('\n'), key=len)
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 45)

def export_all_to_excel(output_dir=None):
    """
    Exports all website database tables into a multi-tab Excel spreadsheet (.xlsx)
    and individual CSV spreadsheets inside the specified directory (defaults to GRN_Property_Database).
    """
    if not output_dir:
        output_dir = Config.DATABASE_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, 'GRN_Properties_Master_Data.xlsx')

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    conn = db.get_db()
    cursor = conn.cursor()

    # ==========================================
    # 1. PROPERTIES SHEET
    # ==========================================
    ws_props = wb.create_sheet(title="Properties")
    prop_headers = [
        "Property ID", "Title", "Category", "Property Type", "Purpose", 
        "Numeric Price (INR)", "Display Price", "City", "Location", "Sub Location", 
        "Street Address", "Configuration", "Carpet Area (sq.ft)", "Super Area (sq.ft)", 
        "Bedrooms", "Bathrooms", "Balconies", "Possession Status", "MahaRERA Number", 
        "Featured", "Status", "Owner/Agent Name", "Owner Role", "Agency Name", 
        "Contact Phone", "Amenities", "Nearby Landmarks", "Date Listed"
    ]
    ws_props.append(prop_headers)

    cursor.execute("""
        SELECT p.*, u.full_name as owner_name, u.role as owner_role, 
               u.agency_name as owner_agency, u.phone as owner_phone
        FROM properties p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)
    properties = cursor.fetchall()

    for p in properties:
        # Parse amenities & landmarks from JSON
        amenities_list = []
        if p['amenities']:
            try:
                amenities_list = json.loads(p['amenities'])
            except Exception:
                amenities_list = [p['amenities']]
        
        landmarks_list = []
        if p['nearby_landmarks']:
            try:
                landmarks_list = json.loads(p['nearby_landmarks'])
            except Exception:
                landmarks_list = [p['nearby_landmarks']]

        ws_props.append([
            p['id'],
            p['title'],
            p['category'],
            p['property_type'],
            p['purpose'],
            p['price'],
            p['price_display'],
            p['city'] or 'Pune',
            p['location'],
            p['sub_location'] or '',
            p['address'] or '',
            p['configuration'] or '',
            p['carpet_area'] or 0,
            p['super_area'] or 0,
            p['bedrooms'] or 0,
            p['bathrooms'] or 0,
            p['balconies'] or 0,
            p['possession_status'] or '',
            p['rera_number'] or '',
            "Yes" if p['featured'] else "No",
            p['status'],
            p['owner_name'] or p['contact_person'] or 'Real Estate Admin',
            (p['owner_role'] or 'Admin').capitalize(),
            p['owner_agency'] or '',
            p['contact_phone'] or p['owner_phone'] or '',
            ", ".join(amenities_list),
            " | ".join(landmarks_list),
            str(p['created_at'])
        ])

    style_worksheet(ws_props, "Properties", header_bg="0A0B0E", header_fg="F2D07C")

    # ==========================================
    # 2. ENQUIRIES & LEADS SHEET
    # ==========================================
    ws_enq = wb.create_sheet(title="Customer_Leads")
    enq_headers = [
        "Lead ID", "Date Received", "Customer Name", "Customer Phone", 
        "Customer Email", "Property Inquired", "Assigned Agent/Owner", 
        "Enquiry Type", "Enquiry Source", "Website Enquiry URL", "Budget", "Preferred Location", "Preferred Visit Date", 
        "Customer Message", "Pipeline Status", "Follow-Up Notes"
    ]
    ws_enq.append(enq_headers)

    cursor.execute("""
        SELECT e.*, p.title as prop_title, u.full_name as assigned_agent
        FROM enquiries e
        LEFT JOIN properties p ON e.property_id = p.id
        LEFT JOIN users u ON e.property_owner_id = u.id
        ORDER BY e.id DESC
    """)
    enquiries = cursor.fetchall()

    for e in enquiries:
        row_dict = dict(e)
        ws_enq.append([
            row_dict['id'],
            str(row_dict['created_at']),
            row_dict['name'],
            row_dict['phone'],
            row_dict['email'] or '',
            row_dict['prop_title'] or row_dict['property_title'] or 'General Enquiry',
            row_dict['assigned_agent'] or 'Real Estate Central Desk',
            row_dict['enquiry_type'] or 'Property Enquiry',
            row_dict.get('lead_source') or 'Website Direct',
            row_dict.get('website_enquiry_url') or 'N/A',
            row_dict['budget'] or '',
            row_dict['preferred_location'] or '',
            row_dict['preferred_date'] or '',
            row_dict['message'] or '',
            row_dict['status'] or 'New',
            row_dict['admin_notes'] or ''
        ])

    style_worksheet(ws_enq, "Customer Leads", header_bg="161922", header_fg="D4AF37")

    # ==========================================
    # 3. USERS & AGENTS SHEET
    # ==========================================
    ws_users = wb.create_sheet(title="Users_and_Agents")
    user_headers = [
        "User ID", "Full Name", "Username", "Role", "Phone", 
        "Email", "Agency / Firm Name", "MahaRERA Reg No", "Status", 
        "Listing Limit", "Upload Limit", "Can Post Ads", "Can Edit Ads", 
        "Can Delete Ads", "Can Access CRM", "Can Export Leads", "Can Feature Properties", 
        "Last Login", "Admin Notes", "Date Registered"
    ]
    ws_users.append(user_headers)

    cursor.execute("SELECT * FROM users ORDER BY id ASC")
    users = cursor.fetchall()

    for u in users:
        ws_users.append([
            u['id'],
            u['full_name'] or '',
            u['username'],
            (u['role'] or 'owner').capitalize(),
            u['phone'] or '',
            u['email'] or '',
            u['agency_name'] or '',
            u['rera_number'] or '',
            (u['status'] or 'active').capitalize(),
            "Unlimited (-1)" if u['listing_limit'] == -1 else (u['listing_limit'] or 10),
            u['upload_limit'] or 10,
            "Yes" if u['can_post_ads'] else "No",
            "Yes" if u['can_edit_ads'] else "No",
            "Yes" if u['can_delete_ads'] else "No",
            "Yes" if u['can_access_crm'] else "No",
            "Yes" if u['can_export_leads'] else "No",
            "Yes" if u['can_feature_properties'] else "No",
            str(u['last_login'] or 'Never'),
            u['notes'] or '',
            str(u['created_at'])
        ])

    style_worksheet(ws_users, "Users and Agents", header_bg="07080A", header_fg="F2D07C")

    conn.close()

    # Save workbook to disk
    wb.save(excel_path)
    print(f"Excel Master Sheet saved to: {excel_path}")

    # ==========================================
    # 4. ALSO EXPORT CSVs FOR MAXIMUM PORTABILITY
    # ==========================================
    csv_files = {
        'Properties_Export.csv': (prop_headers, ws_props),
        'Customer_Leads_Export.csv': (enq_headers, ws_enq),
        'Users_and_Agents_Export.csv': (user_headers, ws_users)
    }

    for fname, (headers, ws) in csv_files.items():
        csv_path = os.path.join(output_dir, fname)
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(row)
        print(f"CSV copy saved: {csv_path}")

    return excel_path

if __name__ == '__main__':
    export_all_to_excel()

