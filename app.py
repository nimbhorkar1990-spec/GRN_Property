import os
import json
import re
import csv
import io
from functools import wraps
from datetime import datetime
from urllib.parse import quote
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, Response, abort, send_file
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
import database as db
from excel_exporter import export_all_to_excel

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper function: slugify
def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)

# Helper function: parse JSON or return list
def safe_json_loads(val, default=None):
    if default is None:
        default = []
    if not val:
        return default
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        # If it was comma separated
        return [item.strip() for item in str(val).split(',') if item.strip()]

# Register template filters
@app.template_filter('json_loads')
def filter_json_loads(val):
    return safe_json_loads(val)

@app.template_filter('clean_phone')
def filter_clean_phone(val):
    if not val:
        return ''
    return re.sub(r'\D', '', str(val))

@app.template_filter('format_currency')
def filter_format_currency(val):
    try:
        val = float(val)
        if val >= 10000000:
            return f"₹{val/10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val/100000:.2f} Lakhs"
        else:
            return f"₹{val:,.0f}"
    except (ValueError, TypeError):
        return str(val)

def update_logo_svg(website_name):
    """Dynamically update static/images/logo.svg with the new website name in luxury styling."""
    try:
        import html
        name = (website_name or 'GRN Properties').strip()
        words = name.split()
        if len(words) == 1:
            first_word = html.escape(words[0])
            remaining_words = ""
        else:
            first_word = html.escape(words[0])
            remaining_words = html.escape(" ".join(words[1:]))

        name_len = len(name)
        if name_len <= 14:
            font_size = 24
        elif name_len <= 20:
            font_size = 20
        elif name_len <= 26:
            font_size = 17
        else:
            font_size = 14

        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 80" width="360" height="80">
  <defs>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F2D07C" />
      <stop offset="50%" stop-color="#D4AF37" />
      <stop offset="100%" stop-color="#9A7B2C" />
    </linearGradient>
    <linearGradient id="goldShine" x1="0%" y1="50%" x2="100%" y2="50%">
      <stop offset="0%" stop-color="#D4AF37" stop-opacity="0.3"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#D4AF37" stop-opacity="0.3"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Monogram Emblem / Architecture Crest -->
  <g transform="translate(10, 8)">
    <!-- Outer Shield / Diamond Frame -->
    <polygon points="32,2 62,32 32,62 2,32" fill="none" stroke="url(#goldGrad)" stroke-width="2" />
    <polygon points="32,7 57,32 32,57 7,32" fill="#0C0E12" stroke="url(#goldGrad)" stroke-width="0.7" opacity="0.9" />

    <!-- Stylized Architectural Towers forming G - R - N -->
    <path d="M22 46 L22 24 L29 18 L29 46 Z" fill="url(#goldGrad)" opacity="0.85"/>
    <path d="M30 46 L30 14 L36 10 L42 14 L42 46 Z" fill="url(#goldGrad)" />
    <path d="M43 46 L43 24 L36 29 L43 46 Z" fill="url(#goldGrad)" opacity="0.7"/>

    <!-- Roofline accent -->
    <polygon points="32,10 38,15 26,15" fill="#FFEBB0" />
    
    <!-- Small Luxury Star -->
    <polygon points="32,49 33.5,53 37.5,53.5 34.5,56 35.5,60 32,57.5 28.5,60 29.5,56 26.5,53.5 30.5,53" fill="url(#goldGrad)" />
  </g>

  <!-- Text Branding -->
  <g transform="translate(85, 20)">
    <!-- Main Company Name -->
    <text x="0" y="24" font-family="'Cinzel', 'Playfair Display', 'Trajan Pro', Georgia, serif" font-size="{font_size}" font-weight="800" letter-spacing="2" fill="#FFFFFF">
      {first_word}
      {f'<tspan fill="url(#goldGrad)" dx="5" font-weight="700">{remaining_words}</tspan>' if remaining_words else ''}
    </text>

    <!-- Tagline & Focus -->
    <text x="2" y="42" font-family="'Montserrat', 'Helvetica Neue', Arial, sans-serif" font-size="8.5" font-weight="600" letter-spacing="4.5" fill="#C5A059">
      PREMIER REAL ESTATE PORTAL
    </text>
  </g>
</svg>'''
        logo_path = os.path.join(app.root_path, 'static', 'images', 'logo.svg')
        with open(logo_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        return True
    except Exception as e:
        app.logger.error(f"Error updating logo.svg: {e}")
        return False

# Context processor for global template variables
@app.context_processor
def inject_globals():
    is_logged = 'user_id' in session
    user_role = session.get('user_role', '')
    current_user_obj = {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'name': session.get('user_name'),
        'role': user_role
    } if is_logged else None

    active_theme = session.get('user_theme') or request.cookies.get('grn_theme', 'luxury-gold')
    pending_count = db.get_pending_properties_count() if (is_logged and user_role == 'admin') else 0

    website_name = db.get_website_name()
    wa_settings = db.get_all_whatsapp_settings()
    whatsapp_default_msg = wa_settings['default_message']
    whatsapp_title_fmt = wa_settings['listing_title_format']
    whatsapp_url_fmt = wa_settings['listing_url_format']
    whatsapp_add_msg = wa_settings['additional_message']

    # Dynamic Office & Contact Information
    contact_dict = db.get_contact_settings_dict()
    corp_item = contact_dict.get('corporate_office', {})
    phone_item = contact_dict.get('company_phone', {})
    wa_item = contact_dict.get('company_whatsapp', {})
    email_item = contact_dict.get('company_email', {})
    rera_item = contact_dict.get('company_rera', {})
    branch_item = contact_dict.get('branch_office', {})
    hours_item = contact_dict.get('working_hours', {})
    maps_item = contact_dict.get('google_maps_url', {})

    company_address = corp_item.get('value') or Config.COMPANY_ADDRESS
    company_phone = phone_item.get('value') or Config.COMPANY_PHONE
    company_whatsapp = wa_item.get('value') or Config.COMPANY_WHATSAPP
    company_email = email_item.get('value') or Config.COMPANY_EMAIL
    company_rera = rera_item.get('value') or Config.COMPANY_RERA
    branch_office = branch_item.get('value', '')
    working_hours = hours_item.get('value', '')
    google_maps_url = maps_item.get('value', '')

    company_phone_raw = re.sub(r'\D', '', company_phone)
    company_whatsapp_raw = re.sub(r'\D', '', company_whatsapp)
    if not company_whatsapp_raw:
        company_whatsapp_raw = Config.COMPANY_WHATSAPP_RAW

    # General WhatsApp message (no specific listing)
    general_whatsapp_msg = db.format_whatsapp_message(listing_title=None, listing_url=None)
    general_whatsapp_encoded = quote(general_whatsapp_msg)
    whatsapp_contact_url = f"https://wa.me/{company_whatsapp_raw}?text={general_whatsapp_encoded}"

    def build_whatsapp_url(listing_title=None, listing_url=None, phone=None):
        target_phone = re.sub(r'\D', '', str(phone)) if phone else company_whatsapp_raw
        if not target_phone:
            target_phone = company_whatsapp_raw
        composed_msg = db.format_whatsapp_message(listing_title=listing_title, listing_url=listing_url)
        return f"https://wa.me/{target_phone}?text={quote(composed_msg)}"

    all_contact_enabled = db.get_all_contact_settings(only_enabled=True)
    additional_contact_items = [item for item in all_contact_enabled if item.get('is_custom')]

    return {
        'company_name': website_name,
        'website_name': website_name,
        'company_tagline': Config.COMPANY_TAGLINE,
        'company_phone': company_phone,
        'company_phone_raw': company_phone_raw,
        'company_whatsapp': company_whatsapp,
        'company_whatsapp_raw': company_whatsapp_raw,
        'whatsapp_default_message': whatsapp_default_msg,
        'whatsapp_listing_title_format': whatsapp_title_fmt,
        'whatsapp_listing_url_format': whatsapp_url_fmt,
        'whatsapp_additional_message': whatsapp_add_msg,
        'whatsapp_general_message': general_whatsapp_msg,
        'whatsapp_default_message_encoded': general_whatsapp_encoded,
        'whatsapp_contact_url': whatsapp_contact_url,
        'build_whatsapp_url': build_whatsapp_url,
        'company_email': company_email,
        'company_rera': company_rera,
        'company_address': company_address,
        'branch_office': branch_office,
        'working_hours': working_hours,
        'google_maps_url': google_maps_url,
        'contact_settings': contact_dict,
        'contact_items_list': all_contact_enabled,
        'additional_contact_items': additional_contact_items,
        'pune_locations': Config.PUNE_LOCATIONS,
        'property_categories': Config.PROPERTY_CATEGORIES,
        'available_cities': Config.CITIES,
        'pending_approvals_count': pending_count,
        'current_year': datetime.now().year,
        'is_logged_in': is_logged,
        'is_admin': user_role == 'admin',
        'is_agent': user_role == 'agent',
        'is_owner': user_role == 'owner',
        'current_user': current_user_obj,
        'active_theme': active_theme,
        'is_visible': db.is_item_visible,
        'visibility_map': db.get_visibility_map()
    }

# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this portal.', 'warning')
            return redirect(url_for('login', next=request.url))
        # Ensure active account status
        current_u = db.get_user_by_id(session['user_id'])
        if not current_u or current_u.get('status') != 'active':
            session.clear()
            flash('Your account has been deactivated or suspended by the Administrator. Please contact support.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'admin':
            flash('Admin authorization required.', 'danger')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def check_page_visibility(item_key, page_title=None):
    """
    Check if a public page or feature is visible.
    - If disabled and user is not admin: returns (False, response) rendering unavailable.html (503).
    - If disabled and user is admin: returns (True, True) (allowed with admin_preview=True).
    - If enabled: returns (True, False).
    """
    is_vis = db.is_item_visible(item_key, default=True)
    is_admin = session.get('user_role') == 'admin' or session.get('admin_id')
    if not is_vis:
        if is_admin:
            return True, True  # Admin preview allowed
        return False, (render_template('unavailable.html', page_key=item_key, page_title=page_title), 503)
    return True, False

# ----------------- LIVE VISITOR & SESSION TRACKING ----------------- #

@app.before_request
def track_visitor_and_activity():
    # Ignore static assets to avoid unnecessary session updates
    if request.path.startswith('/static'):
        return

    visitor_id = session.get('visitor_id')
    if not visitor_id:
        import uuid
        visitor_id = str(uuid.uuid4())
        session['visitor_id'] = visitor_id

    username = session.get('username')
    role = session.get('user_role', 'visitor')
    is_authenticated = 1 if 'user_id' in session else 0
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', '')[:250]

    db.track_visitor_session(visitor_id, ip_address, user_agent, username, role, is_authenticated)

# ----------------- PUBLIC ROUTES ----------------- #

@app.route('/')
def index():
    allowed, preview_or_resp = check_page_visibility('page_home', page_title='Homepage')
    if not allowed:
        return preview_or_resp
    featured_properties = db.get_featured_properties(limit=6)
    latest_properties = db.get_all_properties(filters={'status': ['Active', 'Available']}, limit=8)
    return render_template(
        'index.html',
        featured_properties=featured_properties,
        latest_properties=latest_properties,
        is_admin_preview=preview_or_resp
    )

@app.route('/properties')
def properties():
    allowed, preview_or_resp = check_page_visibility('page_all_properties', page_title='All Properties')
    if not allowed:
        return preview_or_resp
    purpose = request.args.get('purpose', '').strip()
    category = request.args.get('category', '').strip()
    city = request.args.get('city', '').strip()
    location = request.args.get('location', '').strip()
    property_type = request.args.get('type', '').strip()
    configuration = request.args.get('bhk', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    keyword = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'latest')

    filters = {'status': ['Active', 'Available']}
    if purpose and purpose != 'All':
        filters['purpose'] = purpose
    if category and category != 'All':
        filters['category'] = category
    if city and city != 'All':
        filters['city'] = city
    if property_type and property_type != 'All':
        filters['property_type'] = property_type
    if location and location != 'All':
        filters['location'] = location
    if configuration and configuration != 'All':
        filters['configuration'] = configuration
    if min_price:
        filters['min_price'] = min_price
    if max_price:
        filters['max_price'] = max_price
    if keyword:
        filters['q'] = keyword

    order_clause = "created_at DESC"
    if sort_by == 'price_low':
        order_clause = "price ASC"
    elif sort_by == 'price_high':
        order_clause = "price DESC"
    elif sort_by == 'area_high':
        order_clause = "carpet_area DESC"

    all_props = db.get_all_properties(filters=filters, order_by=order_clause)

    return render_template(
        'properties.html',
        properties=all_props,
        filters=filters,
        selected_purpose=purpose,
        selected_category=category,
        selected_city=city,
        selected_location=location,
        selected_bhk=configuration,
        selected_sort=sort_by,
        search_query=keyword,
        total_count=len(all_props),
        is_admin_preview=preview_or_resp
    )

@app.route('/property/<slug_or_id>')
def property_detail(slug_or_id):
    allowed, preview_or_resp = check_page_visibility('page_property_detail', page_title='Property Details')
    if not allowed:
        return preview_or_resp
    prop = None
    if slug_or_id.isdigit():
        prop = db.get_property_by_id(int(slug_or_id))
    if not prop:
        prop = db.get_property_by_slug(slug_or_id)
    if not prop:
        abort(404)

    # Restrict unapproved/rejected properties to property creator and admin
    if prop.get('status') not in ['Active', 'Available']:
        user_id = session.get('user_id')
        is_admin = session.get('user_role') == 'admin'
        is_owner = user_id and user_id == prop.get('user_id')
        if not (is_admin or is_owner):
            abort(404)

    gallery = safe_json_loads(prop.get('gallery_images'))
    amenities = safe_json_loads(prop.get('amenities'))
    landmarks = safe_json_loads(prop.get('nearby_landmarks'))
    videos = safe_json_loads(prop.get('video_urls'))
    
    similar = db.get_similar_properties(
        property_id=prop['id'],
        category=prop['category'],
        sub_location=prop['sub_location'] or prop['location'],
        limit=3
    )

    return render_template(
        'property_detail.html',
        property=prop,
        gallery=gallery,
        amenities=amenities,
        landmarks=landmarks,
        videos=videos,
        similar_properties=similar,
        is_admin_preview=preview_or_resp
    )

@app.route('/buy')
def buy():
    allowed, preview_or_resp = check_page_visibility('page_buy', page_title='Buy Properties')
    if not allowed:
        return preview_or_resp
    return redirect(url_for('properties', purpose='Buy'))

@app.route('/rent')
def rent():
    allowed, preview_or_resp = check_page_visibility('page_rent', page_title='Rent Properties')
    if not allowed:
        return preview_or_resp
    return redirect(url_for('properties', purpose='Rent'))

@app.route('/commercial')
def commercial():
    allowed, preview_or_resp = check_page_visibility('page_commercial', page_title='Commercial Properties')
    if not allowed:
        return preview_or_resp
    return redirect(url_for('properties', type='Commercial'))

@app.route('/category/<cat_name>')
def category_view(cat_name):
    clean_name = cat_name.replace('-', ' ').title()
    match = None
    for c in Config.PROPERTY_CATEGORIES:
        if c.lower() == clean_name.lower():
            match = c
            break
    return redirect(url_for('properties', category=match or clean_name))

@app.route('/location/<loc_name>')
def location_view(loc_name):
    clean_name = loc_name.replace('-', ' ').title()
    return redirect(url_for('properties', location=clean_name))

@app.route('/about')
def about():
    allowed, preview_or_resp = check_page_visibility('page_about', page_title='About Us')
    if not allowed:
        return preview_or_resp
    return render_template('about.html', is_admin_preview=preview_or_resp)

@app.route('/services')
def services():
    allowed, preview_or_resp = check_page_visibility('page_services', page_title='Our Services')
    if not allowed:
        return preview_or_resp
    return render_template('services.html', is_admin_preview=preview_or_resp)

@app.route('/sell')
def sell():
    allowed, preview_or_resp = check_page_visibility('page_sell', page_title='Sell Property')
    if not allowed:
        return preview_or_resp
    return render_template('sell.html', is_admin_preview=preview_or_resp)

@app.route('/contact')
def contact():
    allowed, preview_or_resp = check_page_visibility('page_contact', page_title='Contact Us')
    if not allowed:
        return preview_or_resp
    return render_template('contact.html', is_admin_preview=preview_or_resp)

@app.route('/privacy-policy')
def privacy_policy():
    allowed, preview_or_resp = check_page_visibility('page_privacy', page_title='Privacy Policy')
    if not allowed:
        return preview_or_resp
    return render_template('privacy.html', is_admin_preview=preview_or_resp)

@app.route('/terms')
def terms():
    allowed, preview_or_resp = check_page_visibility('page_terms', page_title='Terms of Service')
    if not allowed:
        return preview_or_resp
    return render_template('terms.html', is_admin_preview=preview_or_resp)

# ----------------- LEAD GENERATION & ENQUIRIES ----------------- #

@app.route('/enquire', methods=['POST'])
def handle_enquiry():
    enquiry_type = request.form.get('enquiry_type', 'Property Enquiry').strip()
    is_admin = session.get('user_role') == 'admin' or session.get('admin_id')

    # Security check on form visibility
    if enquiry_type == 'Schedule Site Visit':
        if not db.is_item_visible('form_schedule_visit') and not is_admin:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Site visit booking requests are currently disabled.'}), 403
            flash('Site visit booking requests are currently disabled.', 'danger')
            return redirect(request.referrer or url_for('index'))
    elif enquiry_type in ['Sell Property', 'Sell My Property']:
        if not db.is_item_visible('form_sell_property') and not is_admin:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Sell property submission is currently disabled.'}), 403
            flash('Sell property submission is currently disabled.', 'danger')
            return redirect(request.referrer or url_for('index'))
    elif enquiry_type in ['Contact Us', 'General Consultation', 'General Enquiry']:
        if not db.is_item_visible('form_contact') and not is_admin:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Contact form submissions are currently disabled.'}), 403
            flash('Contact form submissions are currently disabled.', 'danger')
            return redirect(request.referrer or url_for('index'))
    else:
        if not db.is_item_visible('form_property_enquiry') and not is_admin:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Property enquiry submissions are currently disabled.'}), 403
            flash('Property enquiry submissions are currently disabled.', 'danger')
            return redirect(request.referrer or url_for('index'))
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    property_id = request.form.get('property_id')
    property_title = request.form.get('property_title', 'General Consultation').strip()
    enquiry_type = request.form.get('enquiry_type', 'Property Enquiry').strip()
    budget = request.form.get('budget', '').strip()
    preferred_location = request.form.get('preferred_location', '').strip()
    preferred_date = request.form.get('preferred_date', '').strip()
    message = request.form.get('message', '').strip()

    if not name or not phone:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Name and Mobile Number are required.'}), 400
        flash('Please provide your name and mobile number to submit the enquiry.', 'danger')
        return redirect(request.referrer or url_for('index'))

    # Capture Website Enquiry URL from form input, Referer, or page context
    website_enquiry_url = request.form.get('website_enquiry_url', '').strip()
    if not website_enquiry_url:
        website_enquiry_url = request.referrer or request.headers.get('Referer') or ''
    if not website_enquiry_url and property_id and str(property_id).isdigit():
        prop = db.get_property_by_id(int(property_id))
        if prop and prop.get('slug'):
            website_enquiry_url = f"/property/{prop['slug']}"
    if not website_enquiry_url:
        website_enquiry_url = request.url or '—'

    lead_source = request.form.get('lead_source', 'Website Direct').strip() or 'Website Direct'

    enquiry_data = {
        'name': name,
        'phone': phone,
        'email': email,
        'property_id': int(property_id) if property_id and property_id.isdigit() else None,
        'property_title': property_title,
        'enquiry_type': enquiry_type,
        'lead_source': lead_source,
        'website_enquiry_url': website_enquiry_url,
        'budget': budget,
        'preferred_location': preferred_location,
        'preferred_date': preferred_date,
        'message': message,
        'status': 'New',
        'admin_notes': ''
    }

    db.insert_enquiry(enquiry_data)
    try:
        export_all_to_excel()
    except Exception:
        pass

    success_msg = f"Thank you, {name}! Your enquiry has been received. Our property advisor will contact you within 15 minutes."

    site_name = db.get_website_name()
    enq_wa_msg = quote(f"Hi {site_name}, I am {name} interested in {property_title}.")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': success_msg,
            'whatsapp_url': f"https://wa.me/{Config.COMPANY_WHATSAPP_RAW}?text={enq_wa_msg}"
        })

    flash(success_msg, 'success')
    return redirect(request.referrer or url_for('index'))

# ----------------- AUTHENTICATION: LOGIN, REGISTER, LOGOUT ----------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Lookup by username or email
        user = db.get_user_by_username(login_input)
        if not user:
            user = db.get_user_by_email(login_input)

        if user and check_password_hash(user['password_hash'], password):
            # Check if user account is deactivated or suspended
            if user.get('status') != 'active':
                flash('Your account has been deactivated or suspended by the Administrator. Please contact support.', 'danger')
                return render_template('login.html')

            # Record login timestamp
            db.update_user_last_login(user['id'])

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session['user_name'] = user['full_name'] or user['username']

            # Backwards compatibility for admin
            if user['role'] == 'admin':
                session['admin_id'] = user['id']
                session['admin_username'] = user['username']
                session['admin_name'] = user['full_name']

            if user.get('theme_preference'):
                session['user_theme'] = user['theme_preference']

            session['can_manage_feedback'] = user.get('can_manage_feedback', 1)

            # Record login activity and update visitor session
            ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
            db.log_user_activity(user['username'], user['role'], 'Login', ip_addr, 'User logged in successfully')

            if 'visitor_id' in session:
                user_agent = request.headers.get('User-Agent', '')[:250]
                db.track_visitor_session(session['visitor_id'], ip_addr, user_agent, user['username'], user['role'], 1)

            flash(f"Welcome back, {session['user_name']}!", 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username/email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    return login()

@app.route('/api/set-theme', methods=['POST'])
def set_theme():
    data = request.get_json(silent=True) or {}
    theme = data.get('theme', 'luxury-gold').strip()
    valid_themes = ['luxury-gold', 'sapphire-blue', 'emerald-green', 'amethyst-purple', 'executive-light', 'midnight-ivory']
    if theme not in valid_themes:
        theme = 'luxury-gold'
    session['user_theme'] = theme
    if 'user_id' in session:
        db.update_user_theme(session['user_id'], theme)
    resp = jsonify({'success': True, 'theme': theme})
    resp.set_cookie('grn_theme', theme, max_age=60 * 60 * 24 * 365, samesite='Lax')
    return resp

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        role = request.form.get('role', 'owner').strip()
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        agency_name = request.form.get('agency_name', '').strip()
        rera_number = request.form.get('rera_number', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not phone or not email or not username or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register'))

        # Check existing username & email
        if db.get_user_by_username(username):
            flash('Username is already taken. Please choose another username.', 'warning')
            return redirect(url_for('register'))

        if db.get_user_by_email(email):
            flash('An account with this email already exists. Please log in.', 'info')
            return redirect(url_for('login'))

        user_data = {
            'username': username,
            'password_hash': generate_password_hash(password),
            'email': email,
            'full_name': full_name,
            'role': 'agent' if role == 'agent' else 'owner',
            'phone': phone,
            'agency_name': agency_name if role == 'agent' else '',
            'rera_number': rera_number if role == 'agent' else '',
            'status': 'active'
        }

        user_id = db.create_user(user_data)

        # Log in newly registered user
        session['user_id'] = user_id
        session['username'] = username
        session['user_role'] = user_data['role']
        session['user_name'] = full_name
        session['can_manage_feedback'] = 1

        ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
        db.log_user_activity(username, user_data['role'], 'Login', ip_addr, 'New user registered and logged in')
        if 'visitor_id' in session:
            user_agent = request.headers.get('User-Agent', '')[:250]
            db.track_visitor_session(session['visitor_id'], ip_addr, user_agent, username, user_data['role'], 1)

        flash(f'Account created successfully! Welcome to Real Estate as a {user_data["role"].capitalize()}.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    username = session.get('username')
    role = session.get('user_role', 'user')
    ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
    if username:
        db.log_user_activity(username, role, 'Logout', ip_addr, 'User safely logged out')
        if 'visitor_id' in session:
            user_agent = request.headers.get('User-Agent', '')[:250]
            db.track_visitor_session(session['visitor_id'], ip_addr, user_agent, None, 'visitor', 0)
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/logout')
def admin_logout():
    return logout()

# ----------------- AGENT & PROPERTY OWNER PORTAL ----------------- #

@app.route('/dashboard')
@login_required
def user_dashboard():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    stats = db.get_user_dashboard_stats(user_id)
    recent_enquiries = db.get_enquiries_by_owner(user_id, limit=6)
    recent_properties = db.get_all_properties(filters={'user_id': user_id}, limit=5)
    usage = db.get_user_resource_usage(user_id)
    effective_limits = db.get_effective_user_limits(user_id)

    return render_template(
        'dashboard/index.html',
        user=user,
        stats=stats,
        recent_enquiries=recent_enquiries,
        recent_properties=recent_properties,
        usage=usage,
        effective_limits=effective_limits
    )

@app.route('/dashboard/properties')
@login_required
def user_properties():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    my_props = db.get_all_properties(filters={'user_id': user_id})
    active_count = sum(1 for p in my_props if p.get('status') == 'Available')
    return render_template(
        'dashboard/properties.html',
        properties=my_props,
        user=user,
        active_count=active_count
    )

@app.route('/dashboard/properties/add', methods=['GET', 'POST'])
@login_required
def user_property_add():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Check permission: can_post_ads
    if not user.get('can_post_ads', 1):
        flash('Permission Denied: Your account does not have permission to post new property ads. Please contact the administrator.', 'warning')
        return redirect(url_for('user_properties'))

    # Check quota: listing_limit
    eff_limits = db.get_effective_user_limits(user_id)
    listing_limit = eff_limits['listings_limit']
    if listing_limit != -1:
        active_count = db.get_user_active_properties_count(user_id)
        if active_count >= listing_limit:
            flash(f'Listing Limit Reached: You have reached your account limit of {listing_limit} active property listings. Please contact the administrator to increase your quota.', 'danger')
            return redirect(url_for('user_properties'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        property_type = request.form.get('property_type', 'Residential').strip()
        purpose = request.form.get('purpose', 'Buy').strip()
        price = request.form.get('price', '0').strip()
        price_display = request.form.get('price_display', '').strip()
        city = request.form.get('city', 'Pune').strip() or 'Pune'
        location = request.form.get('location', '').strip()
        sub_location = request.form.get('sub_location', '').strip()
        address = request.form.get('address', '').strip()
        configuration = request.form.get('configuration', '').strip()
        carpet_area = request.form.get('carpet_area', '0').strip()
        super_area = request.form.get('super_area', '0').strip()
        bedrooms = request.form.get('bedrooms', '0').strip()
        bathrooms = request.form.get('bathrooms', '0').strip()
        balconies = request.form.get('balconies', '0').strip()
        possession_status = request.form.get('possession_status', '').strip()
        rera_number = request.form.get('rera_number', '').strip() or (user.get('rera_number', '') if user else '')
        contact_person = request.form.get('contact_person', '').strip() or user.get('full_name', '')
        contact_phone = request.form.get('contact_phone', '').strip() or user.get('phone', '')
        # Requirement B: Default status on submission must be 'Under Review'
        status = 'Under Review'
        description = request.form.get('description', '').strip()

        # Primary photo
        featured_image = request.form.get('featured_image_url', '').strip()
        if 'featured_image_file' in request.files:
            file = request.files['featured_image_file']
            if file and file.filename != '':
                filename = f"user_{user_id}_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image = url_for('static', filename=f'uploads/{filename}')

        if not featured_image:
            featured_image = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"

        # Gallery
        gallery_urls = [u.strip() for u in request.form.get('gallery_image_urls', '').splitlines() if u.strip()]
        if 'gallery_files' in request.files:
            files = request.files.getlist('gallery_files')
            for f in files:
                if f and f.filename != '':
                    fname = f"user_{user_id}_gal_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    gallery_urls.append(url_for('static', filename=f'uploads/{fname}'))

        # Enforce upload limit on gallery images
        photos_limit = eff_limits.get('photos_limit', 10)
        if photos_limit != -1 and len(gallery_urls) > photos_limit:
            flash(f'Photo Upload Limit Exceeded: You are allowed a maximum of {photos_limit} photos per listing. Extra photos were truncated.', 'warning')
            gallery_urls = gallery_urls[:photos_limit]

        # Short Videos
        videos_limit = eff_limits.get('videos_limit', 2)
        video_urls = [u.strip() for u in request.form.get('video_urls', '').splitlines() if u.strip()]
        if 'video_files' in request.files:
            v_files = request.files.getlist('video_files')
            for vf in v_files:
                if vf and vf.filename != '':
                    v_fname = f"user_{user_id}_vid_{int(datetime.now().timestamp())}_{secure_filename(vf.filename)}"
                    vf.save(os.path.join(app.config['UPLOAD_FOLDER'], v_fname))
                    video_urls.append(url_for('static', filename=f'uploads/{v_fname}'))
        if videos_limit != -1 and len(video_urls) > videos_limit:
            flash(f'Video Limit Exceeded: You are allowed a maximum of {videos_limit} short video(s) per listing. Extra videos were truncated.', 'warning')
            video_urls = video_urls[:videos_limit]

        # Floor Plan
        floor_plan_image = request.form.get('floor_plan_image_url', '').strip()
        if 'floor_plan_file' in request.files:
            fp_file = request.files['floor_plan_file']
            if fp_file and fp_file.filename != '':
                fp_fname = f"user_{user_id}_plan_{int(datetime.now().timestamp())}_{secure_filename(fp_file.filename)}"
                fp_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fp_fname))
                floor_plan_image = url_for('static', filename=f'uploads/{fp_fname}')

        selected_amenities = request.form.getlist('amenities')
        custom_amenities = [a.strip() for a in request.form.get('custom_amenities', '').split(',') if a.strip()]
        all_amenities = list(set(selected_amenities + custom_amenities))
        landmarks = [lm.strip() for lm in request.form.get('nearby_landmarks', '').splitlines() if lm.strip()]

        base_slug = slugify(f"{title}-{sub_location or location}")
        slug = base_slug
        counter = 1
        while db.get_property_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        can_feature = user.get('can_feature_properties', 0)
        featured = 1 if (request.form.get('featured') and can_feature) else 0

        prop_dict = {
            'user_id': user_id,
            'title': title,
            'slug': slug,
            'category': category,
            'property_type': property_type,
            'purpose': purpose,
            'price': float(price) if price else 0.0,
            'price_display': price_display or f"₹{price}",
            'city': city,
            'location': location,
            'sub_location': sub_location,
            'address': address,
            'configuration': configuration,
            'carpet_area': int(carpet_area) if carpet_area.isdigit() else 0,
            'super_area': int(super_area) if super_area.isdigit() else 0,
            'bedrooms': int(bedrooms) if bedrooms.isdigit() else 0,
            'bathrooms': int(bathrooms) if bathrooms.isdigit() else 0,
            'balconies': int(balconies) if balconies.isdigit() else 0,
            'possession_status': possession_status,
            'rera_number': rera_number,
            'rera_locked': 0,
            'featured': featured,
            'status': status,
            'featured_image': featured_image,
            'gallery_images': json.dumps(gallery_urls),
            'video_urls': json.dumps(video_urls),
            'floor_plan_image': floor_plan_image,
            'description': description,
            'amenities': json.dumps(all_amenities),
            'nearby_landmarks': json.dumps(landmarks),
            'contact_person': contact_person,
            'contact_phone': contact_phone
        }

        db.insert_property(prop_dict)
        flash('Your property advertisement has been submitted successfully and is now Under Review. It will become publicly visible once approved by the Administrator.', 'info')
        return redirect(url_for('user_properties'))

    return render_template(
        'dashboard/property_form.html',
        property=None,
        action='add',
        photos_limit=eff_limits.get('photos_limit', 10),
        videos_limit=eff_limits.get('videos_limit', 2),
        existing_videos=""
    )

@app.route('/dashboard/properties/edit/<int:prop_id>', methods=['GET', 'POST'])
@login_required
def user_property_edit(prop_id):
    user_id = session['user_id']
    prop = db.get_property_by_id(prop_id)

    # Permission check: must be owner or admin
    if not prop or (prop['user_id'] != user_id and session.get('user_role') != 'admin'):
        flash('Unauthorized or property not found.', 'danger')
        return redirect(url_for('user_properties'))

    # Check permission: can_edit_ads
    user = db.get_user_by_id(user_id)
    eff_limits = db.get_effective_user_limits(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_edit_ads', 1):
        flash('Permission Denied: Your account does not have permission to edit property ads. Please contact the administrator.', 'warning')
        return redirect(url_for('user_properties'))

    if request.method == 'POST':
        # Requirement D: Property Title is strictly non-editable during updates
        title = prop['title']
        category = request.form.get('category', '').strip()
        property_type = request.form.get('property_type', 'Residential').strip()
        purpose = request.form.get('purpose', 'Buy').strip()
        price = request.form.get('price', '0').strip()
        price_display = request.form.get('price_display', '').strip()
        city = request.form.get('city', prop.get('city', 'Pune')).strip() or 'Pune'
        location = request.form.get('location', '').strip()
        sub_location = request.form.get('sub_location', '').strip()
        address = request.form.get('address', '').strip()
        configuration = request.form.get('configuration', '').strip()
        carpet_area = request.form.get('carpet_area', '0').strip()
        super_area = request.form.get('super_area', '0').strip()
        bedrooms = request.form.get('bedrooms', '0').strip()
        bathrooms = request.form.get('bathrooms', '0').strip()
        balconies = request.form.get('balconies', '0').strip()
        possession_status = request.form.get('possession_status', '').strip()

        # Requirement C: Lock MahaRERA Registration Number after activation
        is_activated = (prop.get('rera_locked') == 1) or (prop.get('status') in ['Active', 'Available', 'Sold', 'Rented'])
        if is_activated:
            rera_number = prop.get('rera_number', '')
            rera_locked = 1
        else:
            rera_number = request.form.get('rera_number', '').strip()
            rera_locked = 0

        contact_person = request.form.get('contact_person', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()

        # Approval status preservation: if Under Review or Rejected, user edits keep it Under Review
        if prop.get('status') == 'Under Review':
            status = 'Under Review'
        elif prop.get('status') == 'Rejected':
            status = 'Under Review'  # Resubmits for Admin Review
        else:
            form_status = request.form.get('status', prop['status']).strip()
            status = form_status if form_status in ['Available', 'Active', 'Sold', 'Rented'] else prop['status']

        description = request.form.get('description', '').strip()

        featured_image = request.form.get('featured_image_url', '').strip() or prop['featured_image']
        if 'featured_image_file' in request.files:
            file = request.files['featured_image_file']
            if file and file.filename != '':
                filename = f"user_{user_id}_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image = url_for('static', filename=f'uploads/{filename}')

        gallery_urls = [u.strip() for u in request.form.get('gallery_image_urls', '').splitlines() if u.strip()]
        if 'gallery_files' in request.files:
            files = request.files.getlist('gallery_files')
            for f in files:
                if f and f.filename != '':
                    fname = f"user_{user_id}_gal_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    gallery_urls.append(url_for('static', filename=f'uploads/{fname}'))

        # Enforce upload limit on gallery images
        photos_limit = eff_limits.get('photos_limit', 10)
        if photos_limit != -1 and len(gallery_urls) > photos_limit and session.get('user_role') != 'admin':
            flash(f'Photo Upload Limit Exceeded: You are allowed a maximum of {photos_limit} photos per listing. Extra photos were truncated.', 'warning')
            gallery_urls = gallery_urls[:photos_limit]

        # Short Videos
        videos_limit = eff_limits.get('videos_limit', 2)
        video_urls = [u.strip() for u in request.form.get('video_urls', '').splitlines() if u.strip()]
        if 'video_files' in request.files:
            v_files = request.files.getlist('video_files')
            for vf in v_files:
                if vf and vf.filename != '':
                    v_fname = f"user_{user_id}_vid_{int(datetime.now().timestamp())}_{secure_filename(vf.filename)}"
                    vf.save(os.path.join(app.config['UPLOAD_FOLDER'], v_fname))
                    video_urls.append(url_for('static', filename=f'uploads/{v_fname}'))
        if videos_limit != -1 and len(video_urls) > videos_limit and session.get('user_role') != 'admin':
            flash(f'Video Limit Exceeded: You are allowed a maximum of {videos_limit} short video(s) per listing. Extra videos were truncated.', 'warning')
            video_urls = video_urls[:videos_limit]

        floor_plan_image = request.form.get('floor_plan_image_url', '').strip() or prop.get('floor_plan_image', '')
        if 'floor_plan_file' in request.files:
            fp_file = request.files['floor_plan_file']
            if fp_file and fp_file.filename != '':
                fp_fname = f"user_{user_id}_plan_{int(datetime.now().timestamp())}_{secure_filename(fp_file.filename)}"
                fp_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fp_fname))
                floor_plan_image = url_for('static', filename=f'uploads/{fp_fname}')

        selected_amenities = request.form.getlist('amenities')
        custom_amenities = [a.strip() for a in request.form.get('custom_amenities', '').split(',') if a.strip()]
        all_amenities = list(set(selected_amenities + custom_amenities))
        landmarks = [lm.strip() for lm in request.form.get('nearby_landmarks', '').splitlines() if lm.strip()]

        # Enforce can_feature_properties
        can_feature = user.get('can_feature_properties', 0) or session.get('user_role') == 'admin'
        featured = 1 if (request.form.get('featured') and can_feature) else prop.get('featured', 0)

        prop_dict = {
            'user_id': prop['user_id'],
            'title': title,
            'slug': prop['slug'],
            'category': category,
            'property_type': property_type,
            'purpose': purpose,
            'price': float(price) if price else 0.0,
            'price_display': price_display or f"₹{price}",
            'city': city,
            'location': location,
            'sub_location': sub_location,
            'address': address,
            'configuration': configuration,
            'carpet_area': int(carpet_area) if str(carpet_area).isdigit() else 0,
            'super_area': int(super_area) if str(super_area).isdigit() else 0,
            'bedrooms': int(bedrooms) if str(bedrooms).isdigit() else 0,
            'bathrooms': int(bathrooms) if str(bathrooms).isdigit() else 0,
            'balconies': int(balconies) if str(balconies).isdigit() else 0,
            'possession_status': possession_status,
            'rera_number': rera_number,
            'rera_locked': rera_locked,
            'featured': featured,
            'status': status,
            'featured_image': featured_image,
            'gallery_images': json.dumps(gallery_urls),
            'video_urls': json.dumps(video_urls),
            'floor_plan_image': floor_plan_image,
            'description': description,
            'amenities': json.dumps(all_amenities),
            'nearby_landmarks': json.dumps(landmarks),
            'contact_person': contact_person,
            'contact_phone': contact_phone
        }

        db.update_property(prop_id, prop_dict)
        flash('Property ad updated successfully!', 'success')
        return redirect(url_for('user_properties'))

    existing_gallery = "\n".join(safe_json_loads(prop.get('gallery_images')))
    existing_amenities = safe_json_loads(prop.get('amenities'))
    existing_landmarks = "\n".join(safe_json_loads(prop.get('nearby_landmarks')))
    existing_videos = "\n".join(safe_json_loads(prop.get('video_urls')))

    return render_template(
        'dashboard/property_form.html',
        property=prop,
        action='edit',
        existing_gallery=existing_gallery,
        existing_amenities=existing_amenities,
        existing_landmarks=existing_landmarks,
        existing_videos=existing_videos,
        photos_limit=eff_limits.get('photos_limit', 10),
        videos_limit=eff_limits.get('videos_limit', 2)
    )

@app.route('/dashboard/properties/status/<int:prop_id>', methods=['POST'])
@login_required
def user_property_status(prop_id):
    user_id = session['user_id']
    status = request.form.get('status', 'Available')
    prop = db.get_property_by_id(prop_id)

    if not prop or (prop['user_id'] != user_id and session.get('user_role') != 'admin'):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user_properties'))

    # Check permission: can_edit_ads
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_edit_ads', 1):
        flash('Permission Denied: Your account does not have permission to edit property status.', 'warning')
        return redirect(url_for('user_properties'))

    db.update_property_status(prop_id, status)
    flash(f'Property ad status updated to {status}.', 'success')
    return redirect(request.referrer or url_for('user_properties'))

@app.route('/dashboard/properties/delete/<int:prop_id>', methods=['POST'])
@login_required
def user_property_delete(prop_id):
    user_id = session['user_id']
    prop = db.get_property_by_id(prop_id)

    if not prop or (prop['user_id'] != user_id and session.get('user_role') != 'admin'):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user_properties'))

    # Check permission: can_delete_ads
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_delete_ads', 1):
        flash('Permission Denied: Your account does not have permission to delete property ads. Please contact the administrator.', 'warning')
        return redirect(url_for('user_properties'))

    db.delete_property(prop_id)
    flash('Property ad deleted.', 'info')
    return redirect(url_for('user_properties'))

# ----------------- AGENT & OWNER CRM PIPELINE ----------------- #

@app.route('/dashboard/crm')
@login_required
def user_crm():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_access_crm', 1):
        flash('Permission Denied: CRM Lead Management is disabled for your account. Please contact the administrator.', 'warning')
        return redirect(url_for('user_dashboard'))

    # Records per page handling (10, 50, 100, 1000)
    req_per_page = request.args.get('per_page')
    if req_per_page is not None:
        try:
            req_int = int(req_per_page)
        except (ValueError, TypeError):
            req_int = 10
        per_page = db.set_records_per_page_preference(user_id=user_id, section='leads', per_page=req_int)
    else:
        per_page = db.get_records_per_page_preference(user_id=user_id, section='leads')

    status = request.args.get('status', 'All')
    source = request.args.get('source', 'All')
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    if sort not in ['newest', 'oldest']:
        sort = 'newest'

    page = request.args.get('page', 1, type=int)

    # Monthly enquiries limit check & enforcement
    usage = db.get_user_resource_usage(user_id)
    is_limit_reached = usage.get('monthly_enquiries', {}).get('is_reached', False)

    total_count = db.get_enquiries_by_owner_count(user_id, status=status, source=source, search=q)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    if is_limit_reached and session.get('user_role') != 'admin':
        flash(f"You have reached your monthly enquiry access limit of {usage['monthly_enquiries']['allowed']} enquiries. Please contact Admin to upgrade your quota.", 'warning')
        my_enquiries = []
    else:
        my_enquiries = db.get_enquiries_by_owner(
            user_id, status=status, source=source, sort=sort,
            page=page, per_page=per_page, search=q
        )

    lead_sources = db.get_active_lead_sources()
    return render_template(
        'dashboard/crm.html',
        enquiries=my_enquiries,
        selected_status=status,
        selected_source=source,
        sort=sort,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
        lead_sources=lead_sources,
        usage=usage,
        is_limit_reached=is_limit_reached
    )

@app.route('/dashboard/crm/update/<int:enquiry_id>', methods=['POST'])
@login_required
def user_crm_update(enquiry_id):
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_access_crm', 1):
        flash('Permission Denied: CRM Lead Management is disabled for your account.', 'warning')
        return redirect(url_for('user_dashboard'))

    status = request.form.get('status')
    notes = request.form.get('admin_notes', '')
    lead_source = request.form.get('lead_source')

    # Verify enquiry belongs to user's property or user is admin
    enq = db.get_enquiry_by_id(enquiry_id)
    if not enq or (enq['property_owner_id'] != user_id and session.get('user_role') != 'admin'):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user_crm'))

    db.update_enquiry_status(enquiry_id, status, notes, owner_id=user_id, lead_source=lead_source)
    flash('Lead status, source, and CRM follow-up notes saved successfully!', 'success')
    return redirect(request.referrer or url_for('user_crm'))

@app.route('/dashboard/crm/export')
@login_required
def user_crm_export():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_export_leads', 1):
        flash('Permission Denied: Lead export is restricted for your account. Please contact the administrator.', 'warning')
        return redirect(url_for('user_crm'))

    usage = db.get_user_resource_usage(user_id)
    if usage.get('monthly_enquiries', {}).get('is_reached') and session.get('user_role') != 'admin':
        flash(f"Monthly Enquiry Access Limit Reached ({usage['monthly_enquiries']['allowed']} enquiries). Lead export is restricted. Please contact Admin to upgrade your quota.", 'danger')
        return redirect(url_for('user_crm'))

    enquiries = db.get_enquiries_by_owner(user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Lead ID', 'Date Received', 'Customer Name', 'Phone', 'Email',
        'Property Inquired', 'Enquiry Type', 'Lead Source', 'Budget', 
        'Location Preference', 'Preferred Visit Date', 'Customer Message', 
        'Pipeline Status', 'Follow-up Notes'
    ])
    
    for e in enquiries:
        writer.writerow([
            e['id'], e['created_at'], e['name'], e['phone'], e['email'],
            e['property_title'], e['enquiry_type'], e.get('lead_source') or 'Website Direct',
            e['budget'], e['preferred_location'], e['preferred_date'], e['message'],
            e['status'], e['admin_notes']
        ])
    
    output.seek(0)
    filename = f"my_property_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

def _extract_ids_from_request(req):
    ids = []
    if req.is_json:
        data = req.get_json(silent=True) or {}
        ids = data.get('ids') or data.get('selected_ids') or data.get('enquiry_ids') or data.get('feedback_ids') or []
    else:
        ids = (req.form.getlist('ids') or
               req.form.getlist('selected_ids') or
               req.form.getlist('enquiry_ids') or
               req.form.getlist('feedback_ids'))
        if not ids:
            for key in ('ids', 'selected_ids', 'enquiry_ids', 'feedback_ids'):
                val = req.form.get(key)
                if val:
                    ids = [x.strip() for x in str(val).split(',') if x.strip()]
                    break
    if isinstance(ids, (int, str)):
        ids = [ids]
    return ids

@app.route('/dashboard/crm/bulk-delete', methods=['POST'])
@login_required
def user_crm_bulk_delete():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    if session.get('user_role') != 'admin' and not user.get('can_access_crm', 1):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Permission denied.'}), 403
        flash('Permission denied to delete CRM enquiries.', 'danger')
        return redirect(url_for('user_dashboard'))

    ids = _extract_ids_from_request(request)
    owner_filter = None if session.get('user_role') == 'admin' else user_id
    result = db.bulk_delete_enquiries(
        ids,
        owner_id=owner_filter,
        username=session.get('username'),
        role=session.get('user_role', 'agent')
    )
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result), (200 if result['success'] else 400)

    if result['success']:
        flash(f"Successfully permanently deleted {result['count']} selected enquiry record(s).", 'success')
    else:
        flash(result.get('message', 'Failed to delete selected enquiries.'), 'danger')
    return redirect(request.referrer or url_for('user_crm'))

@app.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        agency_name = request.form.get('agency_name', '').strip()
        rera_number = request.form.get('rera_number', '').strip()

        profile_data = {
            'full_name': full_name,
            'phone': phone,
            'email': email,
            'agency_name': agency_name,
            'rera_number': rera_number
        }

        db.update_user_profile(user_id, profile_data)
        session['user_name'] = full_name
        flash('Profile information updated successfully.', 'success')
        return redirect(url_for('user_profile'))

    return render_template('dashboard/profile.html', user=user)

# ----------------- ADMIN DASHBOARD (SUPER ADMIN) ----------------- #

@app.route('/admin/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    admin_id = session.get('admin_id') or session.get('user_id')
    admin_user = None
    if admin_id:
        admin_user = db.get_user_by_id_with_stats(admin_id)
    if not admin_user:
        u = db.get_user_by_username(session.get('admin_username') or 'admin')
        if u:
            admin_user = db.get_user_by_id_with_stats(u['id'])
    if not admin_user:
        admin_user = db.get_user_by_username('admin')
        if admin_user:
            admin_user = db.get_user_by_id_with_stats(admin_user['id'])

    if not admin_user:
        flash("Administrator profile record could not be loaded.", "danger")
        return redirect(url_for('admin_dashboard'))

    ip_addr = request.remote_addr or '127.0.0.1'

    if request.method == 'POST':
        action = request.form.get('action', 'update_profile').strip().lower()

        # Action 1: Change Account Password
        if action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not check_password_hash(admin_user['password_hash'], current_pwd):
                flash("Current password entered is incorrect.", "danger")
                return redirect(url_for('admin_profile'))

            if not new_pwd or len(new_pwd) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('admin_profile'))

            if new_pwd != confirm_pwd:
                flash("New password and confirmation password do not match.", "danger")
                return redirect(url_for('admin_profile'))

            new_hash = generate_password_hash(new_pwd)
            db.update_admin_profile(admin_user['id'], {
                'full_name': admin_user.get('full_name') or admin_user['username'],
                'email': admin_user.get('email', ''),
                'phone': admin_user.get('phone', ''),
                'agency_name': admin_user.get('agency_name', ''),
                'rera_number': admin_user.get('rera_number', ''),
                'notes': admin_user.get('notes', ''),
                'password_hash': new_hash
            })
            db.log_user_activity(admin_user['username'], 'admin', 'Password Change', ip_addr, "Changed Admin account password")
            flash("Administrator account password has been changed successfully.", "success")
            return redirect(url_for('admin_profile'))

        # Action 2: Update Profile Information
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        agency_name = request.form.get('agency_name', '').strip()
        rera_number = request.form.get('rera_number', '').strip()
        notes = request.form.get('notes', '').strip()

        if not full_name:
            flash("Full Name is mandatory and cannot be blank.", "danger")
            return redirect(url_for('admin_profile'))

        if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("Please provide a valid official email address.", "danger")
            return redirect(url_for('admin_profile'))

        if not phone or len(re.sub(r'\D', '', phone)) < 8:
            flash("Please provide a valid contact phone number with at least 8 digits.", "danger")
            return redirect(url_for('admin_profile'))

        profile_data = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'agency_name': agency_name,
            'rera_number': rera_number,
            'notes': notes
        }

        # Check if password change was submitted in the same form
        new_pwd = request.form.get('new_password', '').strip()
        if new_pwd:
            current_pwd = request.form.get('current_password', '')
            confirm_pwd = request.form.get('confirm_password', '').strip()
            if not check_password_hash(admin_user['password_hash'], current_pwd):
                flash("Current password entered is incorrect. Profile details were not saved.", "danger")
                return redirect(url_for('admin_profile'))
            if len(new_pwd) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('admin_profile'))
            if new_pwd != confirm_pwd:
                flash("New password and confirmation password do not match.", "danger")
                return redirect(url_for('admin_profile'))
            profile_data['password_hash'] = generate_password_hash(new_pwd)

        db.update_admin_profile(admin_user['id'], profile_data)

        # Update session display variables immediately
        session['user_name'] = full_name
        session['admin_name'] = full_name

        db.log_user_activity(admin_user['username'], 'admin', 'Profile Update', ip_addr, f"Updated Admin profile for {full_name}")
        flash("Admin profile information has been updated successfully.", "success")
        return redirect(url_for('admin_profile'))

    return render_template('admin/profile.html', user=admin_user)

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = db.get_dashboard_stats()
    recent_enquiries = db.get_all_enquiries(limit=6)
    recent_properties = db.get_all_properties(limit=5)
    live_stats = db.get_live_activity_stats(active_window_minutes=5)
    recent_activities = db.get_recent_activity_logs(limit=10)
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_enquiries=recent_enquiries,
        recent_properties=recent_properties,
        live_stats=live_stats,
        recent_activities=recent_activities
    )

@app.route('/admin/api/live-activity')
@admin_required
def admin_api_live_activity():
    """Real-time JSON endpoint for Admin Live Activity Dashboard auto-refresh."""
    window = request.args.get('window', 5, type=int)
    stats = db.get_live_activity_stats(active_window_minutes=window)
    activities = db.get_recent_activity_logs(limit=10)
    return jsonify({
        'success': True,
        'status': 'success',
        'stats': stats,
        'live_stats': stats,
        'activities': activities,
        'recent_activities': activities,
        'timestamp': datetime.now().strftime('%d-%b-%Y %I:%M:%S %p')
    })

@app.route('/admin/properties')
@admin_required
def admin_properties():
    status = request.args.get('status', 'All')
    category = request.args.get('category', 'All')
    q = request.args.get('q', '').strip()

    filters = {}
    if status != 'All':
        filters['status'] = status
    if category != 'All':
        filters['category'] = category
    if q:
        filters['q'] = q

    properties_list = db.get_all_properties(filters=filters)
    return render_template(
        'admin/properties.html',
        properties=properties_list,
        selected_status=status,
        selected_category=category,
        search_query=q
    )

@app.route('/admin/properties/add', methods=['GET', 'POST'])
@admin_required
def admin_property_add():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        property_type = request.form.get('property_type', 'Residential').strip()
        purpose = request.form.get('purpose', 'Buy').strip()
        price = request.form.get('price', '0').strip()
        price_display = request.form.get('price_display', '').strip()
        city = request.form.get('city', 'Pune').strip() or 'Pune'
        location = request.form.get('location', '').strip()
        sub_location = request.form.get('sub_location', '').strip()
        address = request.form.get('address', '').strip()
        configuration = request.form.get('configuration', '').strip()
        carpet_area = request.form.get('carpet_area', '0').strip()
        super_area = request.form.get('super_area', '0').strip()
        bedrooms = request.form.get('bedrooms', '0').strip()
        bathrooms = request.form.get('bathrooms', '0').strip()
        balconies = request.form.get('balconies', '0').strip()
        possession_status = request.form.get('possession_status', '').strip()
        rera_number = request.form.get('rera_number', '').strip()
        featured = 1 if request.form.get('featured') else 0
        # Requirement B: Default status on submission must be 'Under Review'
        status = 'Under Review'
        description = request.form.get('description', '').strip()

        featured_image = request.form.get('featured_image_url', '').strip()
        if 'featured_image_file' in request.files:
            file = request.files['featured_image_file']
            if file and file.filename != '':
                filename = f"prop_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image = url_for('static', filename=f'uploads/{filename}')

        if not featured_image:
            featured_image = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"

        gallery_urls = [u.strip() for u in request.form.get('gallery_image_urls', '').splitlines() if u.strip()]
        if 'gallery_files' in request.files:
            files = request.files.getlist('gallery_files')
            for f in files:
                if f and f.filename != '':
                    fname = f"gallery_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    gallery_urls.append(url_for('static', filename=f'uploads/{fname}'))

        # Short Videos
        video_urls = [u.strip() for u in request.form.get('video_urls', '').splitlines() if u.strip()]
        if 'video_files' in request.files:
            v_files = request.files.getlist('video_files')
            for vf in v_files:
                if vf and vf.filename != '':
                    v_fname = f"admin_vid_{int(datetime.now().timestamp())}_{secure_filename(vf.filename)}"
                    vf.save(os.path.join(app.config['UPLOAD_FOLDER'], v_fname))
                    video_urls.append(url_for('static', filename=f'uploads/{v_fname}'))

        floor_plan_image = request.form.get('floor_plan_image_url', '').strip()
        if 'floor_plan_file' in request.files:
            fp_file = request.files['floor_plan_file']
            if fp_file and fp_file.filename != '':
                fp_filename = f"plan_{int(datetime.now().timestamp())}_{secure_filename(fp_file.filename)}"
                fp_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fp_filename))
                floor_plan_image = url_for('static', filename=f'uploads/{fp_filename}')

        selected_amenities = request.form.getlist('amenities')
        custom_amenities = [a.strip() for a in request.form.get('custom_amenities', '').split(',') if a.strip()]
        all_amenities = list(set(selected_amenities + custom_amenities))
        landmarks = [lm.strip() for lm in request.form.get('nearby_landmarks', '').splitlines() if lm.strip()]

        base_slug = slugify(f"{title}-{sub_location or location}")
        slug = base_slug
        counter = 1
        while db.get_property_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        prop_dict = {
            'user_id': session.get('user_id', 1),
            'title': title,
            'slug': slug,
            'category': category,
            'property_type': property_type,
            'purpose': purpose,
            'price': float(price) if price else 0.0,
            'price_display': price_display or f"₹{price}",
            'city': city,
            'location': location,
            'sub_location': sub_location,
            'address': address,
            'configuration': configuration,
            'carpet_area': int(carpet_area) if carpet_area.isdigit() else 0,
            'super_area': int(super_area) if super_area.isdigit() else 0,
            'bedrooms': int(bedrooms) if bedrooms.isdigit() else 0,
            'bathrooms': int(bathrooms) if bathrooms.isdigit() else 0,
            'balconies': int(balconies) if balconies.isdigit() else 0,
            'possession_status': possession_status,
            'rera_number': rera_number,
            'rera_locked': 0,
            'featured': featured,
            'status': status,
            'featured_image': featured_image,
            'gallery_images': json.dumps(gallery_urls),
            'video_urls': json.dumps(video_urls),
            'floor_plan_image': floor_plan_image,
            'description': description,
            'amenities': json.dumps(all_amenities),
            'nearby_landmarks': json.dumps(landmarks),
            'contact_person': session.get('user_name', 'Real Estate Admin'),
            'contact_phone': Config.COMPANY_PHONE
        }

        db.insert_property(prop_dict)
        flash('Property listing submitted successfully! Its status is Under Review and can be approved in Pending Approvals.', 'info')
        return redirect(url_for('admin_properties'))

    return render_template('admin/property_form.html', property=None, action='add', existing_videos="")

@app.route('/admin/properties/edit/<int:prop_id>', methods=['GET', 'POST'])
@admin_required
def admin_property_edit(prop_id):
    prop = db.get_property_by_id(prop_id)
    if not prop:
        flash('Property not found.', 'danger')
        return redirect(url_for('admin_properties'))

    if request.method == 'POST':
        # Requirement D: Property Title is strictly non-editable during updates
        title = prop['title']
        category = request.form.get('category', '').strip()
        property_type = request.form.get('property_type', 'Residential').strip()
        purpose = request.form.get('purpose', 'Buy').strip()
        price = request.form.get('price', '0').strip()
        price_display = request.form.get('price_display', '').strip()
        city = request.form.get('city', prop.get('city', 'Pune')).strip() or 'Pune'
        location = request.form.get('location', '').strip()
        sub_location = request.form.get('sub_location', '').strip()
        address = request.form.get('address', '').strip()
        configuration = request.form.get('configuration', '').strip()
        carpet_area = request.form.get('carpet_area', '0').strip()
        super_area = request.form.get('super_area', '0').strip()
        bedrooms = request.form.get('bedrooms', '0').strip()
        bathrooms = request.form.get('bathrooms', '0').strip()
        balconies = request.form.get('balconies', '0').strip()
        possession_status = request.form.get('possession_status', '').strip()

        # Requirement C: MahaRERA number locked after activation
        is_activated = (prop.get('rera_locked') == 1) or (prop.get('status') in ['Active', 'Available', 'Sold', 'Rented'])
        if is_activated:
            rera_number = prop.get('rera_number', '')
            rera_locked = 1
        else:
            rera_number = request.form.get('rera_number', '').strip()
            rera_locked = 0

        featured = 1 if request.form.get('featured') else 0
        status = request.form.get('status', prop['status']).strip()
        if status in ['Active', 'Available']:
            rera_locked = 1

        description = request.form.get('description', '').strip()

        featured_image = request.form.get('featured_image_url', '').strip() or prop['featured_image']
        if 'featured_image_file' in request.files:
            file = request.files['featured_image_file']
            if file and file.filename != '':
                filename = f"prop_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image = url_for('static', filename=f'uploads/{filename}')

        gallery_urls = [u.strip() for u in request.form.get('gallery_image_urls', '').splitlines() if u.strip()]
        if 'gallery_files' in request.files:
            files = request.files.getlist('gallery_files')
            for f in files:
                if f and f.filename != '':
                    fname = f"gallery_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    gallery_urls.append(url_for('static', filename=f'uploads/{fname}'))

        # Short Videos
        video_urls = [u.strip() for u in request.form.get('video_urls', '').splitlines() if u.strip()]
        if 'video_files' in request.files:
            v_files = request.files.getlist('video_files')
            for vf in v_files:
                if vf and vf.filename != '':
                    v_fname = f"admin_vid_{int(datetime.now().timestamp())}_{secure_filename(vf.filename)}"
                    vf.save(os.path.join(app.config['UPLOAD_FOLDER'], v_fname))
                    video_urls.append(url_for('static', filename=f'uploads/{v_fname}'))

        floor_plan_image = request.form.get('floor_plan_image_url', '').strip() or prop.get('floor_plan_image', '')
        if 'floor_plan_file' in request.files:
            fp_file = request.files['floor_plan_file']
            if fp_file and fp_file.filename != '':
                fp_filename = f"plan_{int(datetime.now().timestamp())}_{secure_filename(fp_file.filename)}"
                fp_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fp_filename))
                floor_plan_image = url_for('static', filename=f'uploads/{fp_filename}')

        selected_amenities = request.form.getlist('amenities')
        custom_amenities = [a.strip() for a in request.form.get('custom_amenities', '').split(',') if a.strip()]
        all_amenities = list(set(selected_amenities + custom_amenities))
        landmarks = [lm.strip() for lm in request.form.get('nearby_landmarks', '').splitlines() if lm.strip()]

        prop_dict = {
            'title': title,
            'slug': prop['slug'],
            'category': category,
            'property_type': property_type,
            'purpose': purpose,
            'price': float(price) if price else 0.0,
            'price_display': price_display or f"₹{price}",
            'city': city,
            'location': location,
            'sub_location': sub_location,
            'address': address,
            'configuration': configuration,
            'carpet_area': int(carpet_area) if str(carpet_area).isdigit() else 0,
            'super_area': int(super_area) if str(super_area).isdigit() else 0,
            'bedrooms': int(bedrooms) if str(bedrooms).isdigit() else 0,
            'bathrooms': int(bathrooms) if str(bathrooms).isdigit() else 0,
            'balconies': int(balconies) if str(balconies).isdigit() else 0,
            'possession_status': possession_status,
            'rera_number': rera_number,
            'rera_locked': rera_locked,
            'featured': featured,
            'status': status,
            'featured_image': featured_image,
            'gallery_images': json.dumps(gallery_urls),
            'video_urls': json.dumps(video_urls),
            'floor_plan_image': floor_plan_image,
            'description': description,
            'amenities': json.dumps(all_amenities),
            'nearby_landmarks': json.dumps(landmarks),
            'contact_person': prop.get('contact_person', ''),
            'contact_phone': prop.get('contact_phone', '')
        }

        db.update_property(prop_id, prop_dict)
        flash('Property details updated successfully!', 'success')
        return redirect(url_for('admin_properties'))

    existing_gallery = "\n".join(safe_json_loads(prop.get('gallery_images')))
    existing_amenities = safe_json_loads(prop.get('amenities'))
    existing_landmarks = "\n".join(safe_json_loads(prop.get('nearby_landmarks')))
    existing_videos = "\n".join(safe_json_loads(prop.get('video_urls')))

    return render_template(
        'admin/property_form.html',
        property=prop,
        action='edit',
        existing_gallery=existing_gallery,
        existing_amenities=existing_amenities,
        existing_landmarks=existing_landmarks,
        existing_videos=existing_videos
    )

@app.route('/admin/properties/pending')
@admin_required
def admin_pending_properties():
    pending_list = db.get_pending_properties()
    return render_template(
        'admin/properties_pending.html',
        properties=pending_list,
        total_pending=len(pending_list)
    )

@app.route('/admin/properties/approve/<int:prop_id>', methods=['POST'])
@admin_required
def admin_property_approve(prop_id):
    prop = db.get_property_by_id(prop_id)
    if not prop:
        flash('Property listing not found.', 'danger')
        return redirect(url_for('admin_pending_properties'))
    db.approve_property(prop_id)
    flash(f'Property listing "{prop["title"]}" (ID #{prop_id}) has been approved and activated! It is now live on Real Estate.', 'success')
    return redirect(request.referrer or url_for('admin_pending_properties'))

@app.route('/admin/properties/reject/<int:prop_id>', methods=['POST'])
@admin_required
def admin_property_reject(prop_id):
    prop = db.get_property_by_id(prop_id)
    if not prop:
        flash('Property listing not found.', 'danger')
        return redirect(url_for('admin_pending_properties'))
    reason = request.form.get('rejection_reason', 'Listing details do not meet publication criteria.').strip()
    db.reject_property(prop_id, reason=reason)
    flash(f'Property listing "{prop["title"]}" (ID #{prop_id}) has been rejected and remains unpublished.', 'warning')
    return redirect(request.referrer or url_for('admin_pending_properties'))

    existing_gallery = "\n".join(safe_json_loads(prop.get('gallery_images')))
    existing_amenities = safe_json_loads(prop.get('amenities'))
    existing_landmarks = "\n".join(safe_json_loads(prop.get('nearby_landmarks')))

    return render_template(
        'admin/property_form.html',
        property=prop,
        action='edit',
        existing_gallery=existing_gallery,
        existing_amenities=existing_amenities,
        existing_landmarks=existing_landmarks
    )

@app.route('/admin/properties/status/<int:prop_id>', methods=['POST'])
@admin_required
def admin_property_status(prop_id):
    status = request.form.get('status', 'Available')
    db.update_property_status(prop_id, status)
    flash(f'Property status updated to {status}.', 'success')
    return redirect(request.referrer or url_for('admin_properties'))

@app.route('/admin/properties/delete/<int:prop_id>', methods=['POST'])
@admin_required
def admin_property_delete(prop_id):
    db.delete_property(prop_id)
    flash('Property listing deleted successfully.', 'info')
    return redirect(url_for('admin_properties'))

@app.route('/admin/crm/lead-sources', methods=['GET', 'POST'])
@admin_required
def admin_lead_sources():
    if request.method == 'POST':
        source_name = request.form.get('source_name', '').strip()
        description = request.form.get('description', '').strip()
        try:
            display_order = int(request.form.get('display_order', 0))
        except (ValueError, TypeError):
            display_order = 0
        is_active = 1 if request.form.get('is_active') is not None and request.form.get('is_active') != '0' else 1

        success, res = db.add_lead_source(source_name, description, display_order, is_active)
        if success:
            flash(f"CRM Lead Source '{source_name}' added successfully and synchronized with Enquiry Feedback.", 'success')
        else:
            flash(f"Error adding lead source: {res}", 'danger')
        return redirect(request.referrer or url_for('admin_enquiries'))

    sources = db.get_all_lead_sources()
    return jsonify({'status': 'success', 'sources': sources})

@app.route('/admin/crm/lead-sources/add', methods=['POST'])
@admin_required
def admin_lead_source_add():
    source_name = request.form.get('source_name', '').strip()
    description = request.form.get('description', '').strip()
    try:
        display_order = int(request.form.get('display_order', 0))
    except (ValueError, TypeError):
        display_order = 0
    is_active = 1 if request.form.get('is_active', '1') in ('1', 'on', 'true') else 0

    success, res = db.add_lead_source(source_name, description, display_order, is_active)
    if success:
        flash(f"CRM Lead Source '{source_name}' added successfully and synchronized with Enquiry Feedback.", 'success')
    else:
        flash(f"Error adding lead source: {res}", 'danger')
    return redirect(request.referrer or url_for('admin_enquiries'))

@app.route('/admin/crm/lead-sources/edit/<int:source_id>', methods=['POST'])
@admin_required
def admin_lead_source_edit(source_id):
    source_name = request.form.get('source_name', '').strip()
    description = request.form.get('description', '').strip()
    try:
        display_order = int(request.form.get('display_order', 0))
    except (ValueError, TypeError):
        display_order = 0
    is_active = 1 if request.form.get('is_active') in ('1', 'on', 'true') else 0

    success, msg = db.update_lead_source(source_id, source_name, description, display_order, is_active)
    if success:
        flash(f"CRM Lead Source updated and synchronized across all CRM leads and enquiry feedbacks.", 'success')
    else:
        flash(f"Error updating lead source: {msg}", 'danger')
    return redirect(request.referrer or url_for('admin_enquiries'))

@app.route('/admin/crm/lead-sources/delete/<int:source_id>', methods=['POST'])
@admin_required
def admin_lead_source_delete(source_id):
    success, msg = db.delete_lead_source(source_id)
    if success:
        flash(msg, 'info')
    else:
        flash(f"Error deleting lead source: {msg}", 'danger')
    return redirect(request.referrer or url_for('admin_enquiries'))

@app.route('/admin/api/lead-sources')
@admin_required
def admin_api_lead_sources():
    sources = db.get_active_lead_sources()
    return jsonify({'status': 'success', 'sources': sources})

@app.route('/admin/enquiries')
@admin_required
def admin_enquiries():
    req_per_page = request.args.get('per_page')
    admin_id = session.get('user_id', 1)
    if req_per_page is not None:
        try:
            req_int = int(req_per_page)
        except (ValueError, TypeError):
            req_int = 10
        per_page = db.set_records_per_page_preference(user_id=admin_id, section='leads', per_page=req_int)
    else:
        per_page = db.get_records_per_page_preference(user_id=admin_id, section='leads')

    status = request.args.get('status', 'All')
    source = request.args.get('source', 'All')
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    if sort not in ['newest', 'oldest']:
        sort = 'newest'

    page = request.args.get('page', 1, type=int)

    total_count = db.get_enquiries_count(status=status, source=source, search=q)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    enquiries_list = db.get_all_enquiries(
        status=status, source=source, sort=sort,
        page=page, per_page=per_page, search=q
    )
    lead_sources = db.get_active_lead_sources()
    all_lead_sources = db.get_all_lead_sources()
    return render_template(
        'admin/enquiries.html',
        enquiries=enquiries_list,
        selected_status=status,
        selected_source=source,
        sort=sort,
        q=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
        lead_sources=lead_sources,
        all_lead_sources=all_lead_sources
    )

@app.route('/admin/enquiries/update/<int:enquiry_id>', methods=['POST'])
@admin_required
def admin_enquiry_update(enquiry_id):
    status = request.form.get('status')
    notes = request.form.get('admin_notes', '')
    lead_source = request.form.get('lead_source')
    db.update_enquiry_status(enquiry_id, status, notes, lead_source=lead_source)
    flash('Lead status, source, and notes saved successfully.', 'success')
    return redirect(request.referrer or url_for('admin_enquiries'))

@app.route('/admin/enquiries/delete/<int:enquiry_id>', methods=['POST'])
@admin_required
def admin_enquiry_delete(enquiry_id):
    db.delete_enquiry(enquiry_id)
    flash('Enquiry record deleted.', 'info')
    return redirect(url_for('admin_enquiries'))

@app.route('/admin/enquiries/bulk-delete', methods=['POST'])
@admin_required
def admin_enquiries_bulk_delete():
    ids = _extract_ids_from_request(request)
    result = db.bulk_delete_enquiries(
        ids,
        username=session.get('admin_username') or session.get('username', 'admin'),
        role='admin'
    )
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result), (200 if result['success'] else 400)
    
    if result['success']:
        flash(f"Successfully permanently deleted {result['count']} selected enquiry record(s).", 'success')
    else:
        flash(result.get('message', 'Failed to delete selected enquiries.'), 'danger')
    return redirect(request.referrer or url_for('admin_enquiries'))

@app.route('/admin/enquiries/export')
@admin_required
def admin_enquiries_export():
    enquiries = db.get_all_enquiries()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'ID', 'Date', 'Customer Name', 'Phone', 'Email', 
        'Property Interested', 'Enquiry Type', 'Lead Source', 'Website Enquiry URL', 'Budget', 
        'Preferred Location', 'Visit Date', 'Message', 'Status', 'Admin Notes'
    ])
    
    for e in enquiries:
        writer.writerow([
            e['id'], e['created_at'], e['name'], e['phone'], e['email'],
            e['property_title'], e['enquiry_type'], e.get('lead_source') or 'Website Direct',
            e.get('website_enquiry_url') or 'N/A',
            e['budget'], e['preferred_location'], e['preferred_date'], e['message'],
            e['status'], e['admin_notes']
        ])
    
    output.seek(0)
    filename = f"grn_properties_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/admin/export/excel')
@admin_required
def admin_export_excel():
    excel_path = export_all_to_excel()
    return send_file(
        excel_path,
        as_attachment=True,
        download_name=f"GRN_Properties_Master_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ----------------- CENTRALIZED ADMIN USER & PERMISSION MANAGEMENT ----------------- #

@app.route('/admin/users')
@admin_required
def admin_users():
    role = request.args.get('role', 'All')
    status = request.args.get('status', 'All')
    q = request.args.get('q', '').strip()

    users_list = db.get_all_users_with_stats(role=role, status=status, q=q)
    user_stats = db.get_admin_user_stats()
    default_limits = db.get_default_user_limits()

    return render_template(
        'admin/users.html',
        users=users_list,
        stats=user_stats,
        default_limits=default_limits,
        selected_role=role,
        selected_status=status,
        search_query=q
    )

@app.route('/admin/users/default-limits', methods=['POST'])
@admin_required
def admin_users_default_limits():
    try:
        listings_limit = int(request.form.get('default_listings_limit', 10))
    except (ValueError, TypeError):
        listings_limit = 10
    try:
        monthly_enquiries_limit = int(request.form.get('default_monthly_enquiries_limit', 100))
    except (ValueError, TypeError):
        monthly_enquiries_limit = 100
    try:
        photos_limit = int(request.form.get('default_photos_limit', 10))
    except (ValueError, TypeError):
        photos_limit = 10
    try:
        videos_limit = int(request.form.get('default_videos_limit', 2))
    except (ValueError, TypeError):
        videos_limit = 2

    db.update_default_user_limits(
        listings_limit=listings_limit,
        monthly_enquiries_limit=monthly_enquiries_limit,
        photos_limit=photos_limit,
        videos_limit=videos_limit,
        username=session.get('admin_username') or session.get('username', 'admin')
    )
    flash('Default user limits have been successfully saved and applied to standard accounts.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/default-limits/reset', methods=['POST'])
@admin_required
def admin_users_default_limits_reset():
    db.reset_default_user_limits(username=session.get('admin_username') or session.get('username', 'admin'))
    flash('Default user limits have been reset to system defaults (10 Listings, 100 Monthly Enquiries, 10 Photos, 2 Short Videos).', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_user_create():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', 'agent').strip()
    agency_name = request.form.get('agency_name', '').strip()
    rera_number = request.form.get('rera_number', '').strip()
    status = request.form.get('status', 'active').strip()
    
    def_limits = db.get_default_user_limits()

    try:
        listing_limit = int(request.form.get('listing_limit', def_limits['listings_limit']))
    except (ValueError, TypeError):
        listing_limit = def_limits['listings_limit']

    try:
        photos_limit = int(request.form.get('photos_limit') or request.form.get('upload_limit') or def_limits['photos_limit'])
    except (ValueError, TypeError):
        photos_limit = def_limits['photos_limit']

    try:
        monthly_enquiries_limit = int(request.form.get('monthly_enquiries_limit', def_limits['monthly_enquiries_limit']))
    except (ValueError, TypeError):
        monthly_enquiries_limit = def_limits['monthly_enquiries_limit']

    try:
        videos_limit = int(request.form.get('videos_limit', def_limits['videos_limit']))
    except (ValueError, TypeError):
        videos_limit = def_limits['videos_limit']

    has_custom = 1 if (
        request.form.get('has_custom_limits') or
        listing_limit != def_limits['listings_limit'] or
        photos_limit != def_limits['photos_limit'] or
        monthly_enquiries_limit != def_limits['monthly_enquiries_limit'] or
        videos_limit != def_limits['videos_limit']
    ) else 0

    can_post_ads = 1 if request.form.get('can_post_ads') else 0
    can_edit_ads = 1 if request.form.get('can_edit_ads') else 0
    can_delete_ads = 1 if request.form.get('can_delete_ads') else 0
    can_access_crm = 1 if request.form.get('can_access_crm') else 0
    can_export_leads = 1 if request.form.get('can_export_leads') else 0
    can_feature_properties = 1 if request.form.get('can_feature_properties') else 0
    can_manage_feedback = 1 if request.form.get('can_manage_feedback') else 0
    notes = request.form.get('notes', '').strip()

    if not username or not password or not full_name:
        flash('Full Name, Username, and Password are required fields.', 'danger')
        return redirect(url_for('admin_users'))

    if db.get_user_by_username(username):
        flash(f'Username "{username}" is already in use. Please select a different username.', 'warning')
        return redirect(url_for('admin_users'))

    if email and db.get_user_by_email(email):
        flash(f'An account with email "{email}" already exists.', 'warning')
        return redirect(url_for('admin_users'))

    user_dict = {
        'username': username,
        'password_hash': generate_password_hash(password),
        'email': email,
        'full_name': full_name,
        'role': role,
        'phone': phone,
        'agency_name': agency_name,
        'rera_number': rera_number,
        'status': status,
        'listing_limit': listing_limit,
        'upload_limit': photos_limit,
        'photos_limit': photos_limit,
        'monthly_enquiries_limit': monthly_enquiries_limit,
        'videos_limit': videos_limit,
        'has_custom_limits': has_custom,
        'can_post_ads': can_post_ads,
        'can_edit_ads': can_edit_ads,
        'can_delete_ads': can_delete_ads,
        'can_access_crm': can_access_crm,
        'can_export_leads': can_export_leads,
        'can_feature_properties': can_feature_properties,
        'can_manage_feedback': can_manage_feedback,
        'notes': notes
    }

    db.create_user_by_admin(user_dict)
    flash(f'User account "{username}" created successfully with assigned permissions and limits.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
@admin_required
def admin_user_edit(user_id):
    target = db.get_user_by_id(user_id)
    if not target:
        flash('User account not found.', 'danger')
        return redirect(url_for('admin_users'))

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', target['role']).strip()
    agency_name = request.form.get('agency_name', '').strip()
    rera_number = request.form.get('rera_number', '').strip()
    status = request.form.get('status', target['status']).strip()
    
    def_limits = db.get_default_user_limits()

    try:
        listing_limit = int(request.form.get('listing_limit', target.get('listing_limit', def_limits['listings_limit'])))
    except (ValueError, TypeError):
        listing_limit = target.get('listing_limit', def_limits['listings_limit'])

    try:
        photos_limit = int(request.form.get('photos_limit') or request.form.get('upload_limit') or target.get('photos_limit') or def_limits['photos_limit'])
    except (ValueError, TypeError):
        photos_limit = target.get('photos_limit', def_limits['photos_limit'])

    try:
        monthly_enquiries_limit = int(request.form.get('monthly_enquiries_limit', target.get('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])))
    except (ValueError, TypeError):
        monthly_enquiries_limit = target.get('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])

    try:
        videos_limit = int(request.form.get('videos_limit', target.get('videos_limit', def_limits['videos_limit'])))
    except (ValueError, TypeError):
        videos_limit = target.get('videos_limit', def_limits['videos_limit'])

    has_custom = 1 if (
        request.form.get('has_custom_limits') or
        listing_limit != def_limits['listings_limit'] or
        photos_limit != def_limits['photos_limit'] or
        monthly_enquiries_limit != def_limits['monthly_enquiries_limit'] or
        videos_limit != def_limits['videos_limit']
    ) else 0

    can_post_ads = 1 if request.form.get('can_post_ads') else 0
    can_edit_ads = 1 if request.form.get('can_edit_ads') else 0
    can_delete_ads = 1 if request.form.get('can_delete_ads') else 0
    can_access_crm = 1 if request.form.get('can_access_crm') else 0
    can_export_leads = 1 if request.form.get('can_export_leads') else 0
    can_feature_properties = 1 if request.form.get('can_feature_properties') else 0
    can_manage_feedback = 1 if request.form.get('can_manage_feedback') else 0
    notes = request.form.get('notes', '').strip()
    new_password = request.form.get('new_password', '').strip()

    # Super Admin immunity & enforcement
    if target['id'] == 1 or target['username'] == 'admin':
        role = 'admin'
        status = 'active'
        listing_limit = -1
        monthly_enquiries_limit = -1
        photos_limit = 50
        videos_limit = 10
        has_custom = 1
        can_post_ads = 1
        can_edit_ads = 1
        can_delete_ads = 1
        can_access_crm = 1
        can_export_leads = 1
        can_feature_properties = 1
        can_manage_feedback = 1

    user_dict = {
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'role': role,
        'agency_name': agency_name,
        'rera_number': rera_number,
        'status': status,
        'listing_limit': listing_limit,
        'upload_limit': photos_limit,
        'photos_limit': photos_limit,
        'monthly_enquiries_limit': monthly_enquiries_limit,
        'videos_limit': videos_limit,
        'has_custom_limits': has_custom,
        'can_post_ads': can_post_ads,
        'can_edit_ads': can_edit_ads,
        'can_delete_ads': can_delete_ads,
        'can_access_crm': can_access_crm,
        'can_export_leads': can_export_leads,
        'can_feature_properties': can_feature_properties,
        'can_manage_feedback': can_manage_feedback,
        'notes': notes
    }

    if new_password:
        user_dict['password_hash'] = generate_password_hash(new_password)

    db.update_user_by_admin(user_id, user_dict)
    flash(f'Account settings and limits for "{target["username"]}" have been updated successfully.', 'success')
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/users/status/<int:user_id>', methods=['POST'])
@admin_required
def admin_user_status(user_id):
    target = db.get_user_by_id(user_id)
    if not target:
        flash('User account not found.', 'danger')
        return redirect(url_for('admin_users'))

    if target['id'] == 1 or target['username'] == 'admin':
        flash('The primary Super Admin account cannot be deactivated.', 'danger')
        return redirect(url_for('admin_users'))

    status = request.form.get('status', 'active')
    db.toggle_user_status(user_id, status)
    
    action_text = "activated" if status == 'active' else "suspended / deactivated"
    flash(f'Account for "{target["username"]}" has been {action_text}.', 'info')
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    target = db.get_user_by_id(user_id)
    if not target:
        flash('User account not found.', 'danger')
        return redirect(url_for('admin_users'))

    if target['id'] == 1 or target['username'] == 'admin':
        flash('The primary Super Admin account cannot be deleted.', 'danger')
        return redirect(url_for('admin_users'))

    db.delete_user_by_admin(user_id)
    flash(f'User "{target["username"]}" deleted. All properties preserved under Master Admin.', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/monitor')
@admin_required
def admin_user_monitor(user_id):
    target = db.get_user_by_id_with_stats(user_id)
    if not target:
        flash('User account not found.', 'danger')
        return redirect(url_for('admin_users'))

    user_props = db.get_all_properties(filters={'user_id': user_id})
    user_enqs = db.get_enquiries_by_owner(user_id)

    return render_template(
        'admin/user_monitor.html',
        target_user=target,
        properties=user_props,
        enquiries=user_enqs
    )

# ----------------- ADMIN ENQUIRY FEEDBACK MODULE ----------------- #

@app.route('/api/feedback/<int:feedback_id>', methods=['GET'])
@app.route('/admin/feedback/get/<int:feedback_id>', methods=['GET'])
@app.route('/dashboard/feedback/get/<int:feedback_id>', methods=['GET'])
def api_get_feedback(feedback_id):
    """Fetch complete feedback record details from database for viewing or editing."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required. Please login.'}), 401

    current_u = db.get_user_by_id(session['user_id'])
    if session.get('user_role') != 'admin' and (not current_u or not current_u.get('can_manage_feedback', 1)):
        return jsonify({'success': False, 'message': 'Permission denied.'}), 403

    fb = db.get_feedback_by_id(feedback_id)
    if not fb:
        return jsonify({'success': False, 'message': f'Feedback record #{feedback_id} not found.'}), 404

    return jsonify({
        'success': True,
        'feedback': fb
    })

@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    req_per_page = request.args.get('per_page')
    admin_id = session.get('user_id', 1)
    if req_per_page is not None:
        try:
            req_int = int(req_per_page)
        except (ValueError, TypeError):
            req_int = 10
        per_page = db.set_records_per_page_preference(user_id=admin_id, section='feedback', per_page=req_int)
    else:
        per_page = db.get_records_per_page_preference(user_id=admin_id, section='feedback')

    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    project = request.args.get('project', '').strip()
    user = request.args.get('user', '').strip()
    source = request.args.get('source', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    if sort not in ['newest', 'oldest']:
        sort = 'newest'

    filters = {}
    if q:
        filters['search'] = q
    if project:
        filters['project_name'] = project
    if user:
        filters['feedback_by_username'] = user
    if source:
        filters['source'] = source
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to

    total_count = db.get_feedbacks_count(filters)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    feedbacks = db.get_all_feedbacks(filters, page=page, per_page=per_page, sort=sort)
    distinct_projects = db.get_distinct_feedback_projects()
    distinct_users = db.get_distinct_feedback_users()
    admin_email = db.get_setting('admin_email', Config.COMPANY_EMAIL)

    property_projects = [p['title'] for p in db.get_all_properties(limit=50)]
    lead_sources = db.get_active_lead_sources()
    all_lead_sources = db.get_all_lead_sources()

    return render_template(
        'admin/feedback.html',
        feedbacks=feedbacks,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        q=q,
        project=project,
        user=user,
        selected_source=source,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        distinct_projects=distinct_projects,
        distinct_users=distinct_users,
        property_projects=property_projects,
        admin_email=admin_email,
        lead_sources=lead_sources,
        all_lead_sources=all_lead_sources
    )

@app.route('/admin/feedback/add', methods=['POST'])
@admin_required
def admin_feedback_add():
    client_name = request.form.get('client_name', '').strip()
    client_contact = request.form.get('client_contact', '').strip()
    enquiry_datetime = request.form.get('enquiry_datetime', '').strip()
    enquiry_source = request.form.get('enquiry_source', 'Website Direct').strip() or 'Website Direct'
    project_name = request.form.get('project_name', '').strip()
    configuration = request.form.get('configuration', '').strip()
    cost = request.form.get('cost', '').strip()
    carpet = request.form.get('carpet', '').strip()
    possession = request.form.get('possession', '').strip()
    website_enquiry_url = request.form.get('website_enquiry_url', '').strip()
    client_feedback = request.form.get('client_feedback', '').strip()

    if not client_name or not client_contact or not project_name or not client_feedback:
        flash('Please fill in all required fields (Client Name, Contact, Project Name, and Client Feedback).', 'danger')
        return redirect(url_for('admin_feedback'))

    logged_in_username = session.get('admin_username') or session.get('username', 'admin')

    feedback_data = {
        'client_name': client_name,
        'client_contact': client_contact,
        'enquiry_datetime': enquiry_datetime or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'enquiry_source': enquiry_source,
        'project_name': project_name,
        'configuration': configuration,
        'cost': cost,
        'carpet': carpet,
        'possession': possession,
        'website_enquiry_url': website_enquiry_url,
        'client_feedback': client_feedback,
        'feedback_by_username': logged_in_username,
        'role': 'admin'
    }

    feedback_id = db.create_feedback(feedback_data)
    flash(f'Enquiry feedback #{feedback_id} for "{client_name}" added successfully.', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/edit/<int:feedback_id>', methods=['POST'])
@admin_required
def admin_feedback_edit(feedback_id):
    fb = db.get_feedback_by_id(feedback_id)
    if not fb:
        flash('Feedback record not found.', 'danger')
        return redirect(url_for('admin_feedback'))

    client_name = request.form.get('client_name', '').strip()
    client_contact = request.form.get('client_contact', '').strip()
    enquiry_datetime = request.form.get('enquiry_datetime', '').strip()
    enquiry_source = request.form.get('enquiry_source', 'Website Direct').strip() or 'Website Direct'
    project_name = request.form.get('project_name', '').strip()
    configuration = request.form.get('configuration', '').strip()
    cost = request.form.get('cost', '').strip()
    carpet = request.form.get('carpet', '').strip()
    possession = request.form.get('possession', '').strip()
    website_enquiry_url = request.form.get('website_enquiry_url', '').strip()
    client_feedback = request.form.get('client_feedback', '').strip()

    if not client_name or not client_contact or not project_name or not client_feedback:
        flash('Required fields cannot be empty.', 'danger')
        return redirect(url_for('admin_feedback'))

    update_data = {
        'client_name': client_name,
        'client_contact': client_contact,
        'enquiry_datetime': enquiry_datetime,
        'enquiry_source': enquiry_source,
        'project_name': project_name,
        'configuration': configuration,
        'cost': cost,
        'carpet': carpet,
        'possession': possession,
        'website_enquiry_url': website_enquiry_url,
        'client_feedback': client_feedback,
        'updated_by': session.get('admin_username') or session.get('username', 'admin'),
        'role': 'admin'
    }

    db.update_feedback(feedback_id, update_data)
    flash(f'Feedback record #{feedback_id} updated successfully.', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/delete/<int:feedback_id>', methods=['POST'])
@admin_required
def admin_feedback_delete(feedback_id):
    fb = db.get_feedback_by_id(feedback_id)
    if not fb:
        flash('Feedback record not found.', 'danger')
        return redirect(url_for('admin_feedback'))

    db.delete_feedback(
        feedback_id,
        username=session.get('admin_username') or session.get('username', 'admin'),
        role='admin'
    )
    flash(f'Feedback record #{feedback_id} has been permanently deleted.', 'info')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/bulk-delete', methods=['POST'])
@admin_required
def admin_feedback_bulk_delete():
    ids = _extract_ids_from_request(request)
    result = db.bulk_delete_feedbacks(
        ids,
        username=session.get('admin_username') or session.get('username', 'admin'),
        role='admin'
    )
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result), (200 if result['success'] else 400)

    if result['success']:
        flash(f"Successfully permanently deleted {result['count']} selected feedback record(s).", 'success')
    else:
        flash(result.get('message', 'Failed to delete selected feedback records.'), 'danger')
    return redirect(request.referrer or url_for('admin_feedback'))

@app.route('/admin/feedback/export')
@admin_required
def admin_feedback_export():
    import io
    from flask import send_file
    import feedback_service as fs

    filters = {}
    if request.args.get('q'):
        filters['search'] = request.args.get('q').strip()
    if request.args.get('project'):
        filters['project_name'] = request.args.get('project').strip()
    if request.args.get('user'):
        filters['feedback_by_username'] = request.args.get('user').strip()
    if request.args.get('source'):
        filters['source'] = request.args.get('source').strip()
    if request.args.get('date_from'):
        filters['date_from'] = request.args.get('date_from').strip()
    if request.args.get('date_to'):
        filters['date_to'] = request.args.get('date_to').strip()

    feedbacks = db.get_all_feedbacks_for_export(filters)
    excel_bytes = fs.generate_feedback_excel_bytes(feedbacks)

    filename = f"Enquiry_Feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/admin/feedback/email', methods=['POST'])
@admin_required
def admin_feedback_email():
    import feedback_service as fs

    feedbacks = db.get_all_feedbacks_for_export()
    if not feedbacks:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'No feedback records available to send in database.'}), 400
        flash('No feedback records available to send in database.', 'warning')
        return redirect(url_for('admin_feedback'))

    recipient_email = request.form.get('recipient_email') or db.get_setting('admin_email', Config.COMPANY_EMAIL)
    excel_bytes = fs.generate_feedback_excel_bytes(feedbacks)
    success, msg = fs.send_feedback_email(
        excel_bytes,
        recipient_email=recipient_email,
        sender_username=session.get('admin_username') or session.get('username', 'admin')
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': success, 'message': msg}), (200 if success else 400)

    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/refresh', methods=['POST', 'GET'])
@admin_required
def admin_feedback_refresh():
    """
    Refresh / Reload enquiries:
    Fetches newly received customer enquiries directly from the website enquiry database
    and synchronizes them into Feedback without manual entry or duplicate records.
    """
    try:
        username = session.get('admin_username') or session.get('username') or 'admin'
        count, message = db.sync_website_enquiries_to_feedback(username=username, role='admin')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'count': count,
                'message': message
            })
            
        flash(message, 'success' if count > 0 else 'info')
        return redirect(url_for('admin_feedback'))
    except Exception as e:
        app.logger.error(f"Error in admin_feedback_refresh: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': False,
                'count': 0,
                'message': f"Database or system error: {str(e)}"
            }), 500
        flash(f"Error refreshing enquiries: {str(e)}", 'danger')
        return redirect(url_for('admin_feedback'))

@app.route('/admin/settings/email', methods=['POST'])
@admin_required
def admin_settings_email():
    admin_email = request.form.get('admin_email', '').strip()
    smtp_host = request.form.get('smtp_host', '').strip()
    smtp_port = request.form.get('smtp_port', '587').strip()
    smtp_user = request.form.get('smtp_user', '').strip()
    smtp_password = request.form.get('smtp_password', '')
    smtp_tls = '1' if request.form.get('smtp_tls') else '0'

    if admin_email and '@' in admin_email:
        db.set_setting('admin_email', admin_email)
    if smtp_host is not None:
        db.set_setting('smtp_host', smtp_host)
    if smtp_port is not None:
        db.set_setting('smtp_port', smtp_port)
    if smtp_user is not None:
        db.set_setting('smtp_user', smtp_user)
    if smtp_password:
        db.set_setting('smtp_password', smtp_password)
    db.set_setting('smtp_tls', smtp_tls)

    flash('Admin Email & SMTP settings updated successfully.', 'success')
    return redirect(url_for('admin_feedback'))

# ----------------- ADMIN WEBSITE VISIBILITY MANAGEMENT ----------------- #

@app.route('/admin/visibility')
@admin_required
def admin_visibility():
    category = request.args.get('category', 'All').strip()
    status = request.args.get('status', 'All').strip()
    search = request.args.get('q', '').strip()
    
    items = db.get_all_visibility_settings(category=category, search=search, status=status)
    stats = db.get_visibility_stats()
    
    return render_template(
        'admin/visibility.html',
        items=items,
        stats=stats,
        selected_category=category,
        selected_status=status,
        search_query=search
    )

@app.route('/admin/visibility/toggle', methods=['POST'])
@admin_required
def admin_visibility_toggle():
    if request.is_json:
        data = request.get_json() or {}
        item_key = data.get('item_key', '').strip()
        is_visible = data.get('is_visible')
    else:
        item_key = request.form.get('item_key', '').strip()
        is_visible = request.form.get('is_visible')
    
    if not item_key:
        return jsonify({'success': False, 'message': 'Item key is required.'}), 400
    
    is_visible_bool = bool(int(is_visible)) if is_visible is not None else True
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    
    success = db.update_visibility_setting(item_key, is_visible_bool, updated_by=admin_user)
    if success:
        return jsonify({
            'success': True,
            'item_key': item_key,
            'is_visible': 1 if is_visible_bool else 0,
            'updated_by': admin_user,
            'message': f"Visibility updated successfully."
        })
    return jsonify({'success': False, 'message': 'Setting item not found.'}), 404

@app.route('/admin/visibility/bulk', methods=['POST'])
@admin_required
def admin_visibility_bulk():
    action = request.form.get('action', '').strip()
    category = request.form.get('category', 'All').strip()
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    
    is_visible = 1 if action == 'enable_all' else 0
    count = db.bulk_update_visibility(is_visible, category=category if category != 'All' else None, updated_by=admin_user)
    
    flash(f"Successfully {'enabled' if is_visible else 'disabled'} {count} website items.", 'success' if is_visible else 'warning')
    return redirect(url_for('admin_visibility'))

@app.route('/admin/visibility/add', methods=['POST'])
@admin_required
def admin_visibility_add():
    item_key = request.form.get('item_key', '').strip()
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    url_path = request.form.get('url_path', '').strip()
    description = request.form.get('description', '').strip()
    is_visible = 1 if request.form.get('is_visible') else 0
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    
    if not item_key or not name or not category:
        flash('Item key, name, and category are required.', 'danger')
        return redirect(url_for('admin_visibility'))
    
    db.add_visibility_setting(
        item_key=item_key,
        name=name,
        category=category,
        url_path=url_path,
        description=description,
        is_visible=is_visible,
        updated_by=admin_user
    )
    flash(f"Visibility option '{name}' registered successfully.", 'success')
    return redirect(url_for('admin_visibility'))

# ----------------- ADMIN DASHBOARD: WEBSITE & WHATSAPP SETTINGS ----------------- #

@app.route('/admin/settings', methods=['GET'])
@admin_required
def admin_settings():
    tab = request.args.get('tab', 'general').strip().lower()
    if tab not in ['general', 'whatsapp', 'contact']:
        tab = 'general'
    website_name = db.get_website_name()
    wa_settings = db.get_all_whatsapp_settings()
    sample_props = db.get_all_properties()[:8]
    all_contact_settings = db.get_all_contact_settings()
    contact_dict = db.get_contact_settings_dict()

    wa_item = contact_dict.get('company_whatsapp', {})
    company_wa = wa_item.get('value') or Config.COMPANY_WHATSAPP
    company_wa_raw = re.sub(r'\D', '', company_wa) or Config.COMPANY_WHATSAPP_RAW

    general_preview_msg = db.format_whatsapp_message(listing_title=None, listing_url=None)
    general_preview_url = f"https://wa.me/{company_wa_raw}?text={quote(general_preview_msg)}"

    first_prop = sample_props[0] if sample_props else None
    sample_title = first_prop['title'] if first_prop else "3BHK Premium Flat in Wakad"
    sample_url = url_for('property_detail', slug_or_id=first_prop['slug'], _external=True) if first_prop else f"{request.host_url.rstrip('/')}/property/3bhk-premium-flat-wakad"
    sample_preview_msg = db.format_whatsapp_message(listing_title=sample_title, listing_url=sample_url)
    sample_preview_url = f"https://wa.me/{company_wa_raw}?text={quote(sample_preview_msg)}"

    return render_template('admin/settings.html',
                           active_tab=tab,
                           website_name=website_name,
                           whatsapp_default_message=wa_settings['default_message'],
                           whatsapp_message=wa_settings['default_message'],
                           whatsapp_listing_title_format=wa_settings['listing_title_format'],
                           whatsapp_listing_url_format=wa_settings['listing_url_format'],
                           whatsapp_additional_message=wa_settings['additional_message'],
                           whatsapp_preview_url=general_preview_url,
                           sample_preview_url=sample_preview_url,
                           sample_preview_msg=sample_preview_msg,
                           sample_title=sample_title,
                           sample_url=sample_url,
                           sample_properties=sample_props,
                           contact_settings_list=all_contact_settings,
                           contact_dict=contact_dict,
                           default_website_name="GRN Properties",
                           default_whatsapp_message=f"Hi {website_name}, I am looking for property consultation in Pune.",
                           default_listing_title_format="Property / Listing Name: {{listing_title}}.",
                           default_listing_url_format="Property Details Link: {{listing_url}}",
                           default_additional_message="Please share the complete property details, pricing, location and site visit availability.")

@app.route('/admin/settings/contact', methods=['GET', 'POST'])
@app.route('/admin/contact-settings', methods=['GET', 'POST'])
@admin_required
def admin_settings_contact():
    if request.method == 'GET':
        return redirect(url_for('admin_settings', tab='contact'))

    action = request.form.get('action', 'save').strip().lower()
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    ip_addr = request.remote_addr or '127.0.0.1'

    if action == 'reset':
        db.reset_contact_settings_to_default()
        db.log_user_activity(admin_user, 'admin', 'Settings Reset', ip_addr, "Reset Office & Contact Information to default")
        flash("All Office & Contact Information has been reset to system defaults.", 'success')
        return redirect(url_for('admin_settings', tab='contact'))

    if action == 'add_custom':
        new_label = request.form.get('new_label', '').strip()
        new_value = request.form.get('new_value', '').strip()
        new_icon = request.form.get('new_icon', 'fas fa-info-circle').strip()
        new_link_type = request.form.get('new_link_type', 'none').strip()
        new_order = request.form.get('new_order', 90)
        new_enabled = 1 if request.form.get('new_enabled') else 0

        if not new_label or not new_value:
            flash("Label and Contact Detail / Value are required to add new contact information.", 'danger')
            return redirect(url_for('admin_settings', tab='contact'))

        field_key = db.add_custom_contact_setting(new_label, new_value, new_icon, new_link_type, new_enabled, new_order)
        db.log_user_activity(admin_user, 'admin', 'Settings Add', ip_addr, f"Added Additional Contact field '{new_label}' ({field_key})")
        flash(f"Additional contact information '{new_label}' added successfully.", 'success')
        return redirect(url_for('admin_settings', tab='contact'))

    if action == 'delete_custom':
        field_key = request.form.get('field_key', '').strip()
        if field_key:
            db.delete_contact_setting(field_key)
            db.log_user_activity(admin_user, 'admin', 'Settings Delete', ip_addr, f"Deleted Contact field '{field_key}'")
            flash("Contact information field deleted successfully.", 'success')
        return redirect(url_for('admin_settings', tab='contact'))

    # Save / Update action
    corp_office = request.form.get('corporate_office', '').strip()
    company_phone = request.form.get('company_phone', '').strip()
    company_whatsapp = request.form.get('company_whatsapp', '').strip()
    company_email = request.form.get('company_email', '').strip()
    company_rera = request.form.get('company_rera', '').strip()
    branch_office = request.form.get('branch_office', '').strip()
    working_hours = request.form.get('working_hours', '').strip()
    google_maps_url = request.form.get('google_maps_url', '').strip()

    # Validation:
    if not corp_office:
        flash("Corporate Office address cannot be blank.", 'danger')
        return redirect(url_for('admin_settings', tab='contact'))
    if not company_phone or len(re.sub(r'\D', '', company_phone)) < 8:
        flash("Please provide a valid company contact phone number (at least 8 digits).", 'danger')
        return redirect(url_for('admin_settings', tab='contact'))
    if not company_whatsapp or len(re.sub(r'\D', '', company_whatsapp)) < 8:
        flash("Please provide a valid WhatsApp contact number (at least 8 digits).", 'danger')
        return redirect(url_for('admin_settings', tab='contact'))
    if not company_email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', company_email):
        flash("Please provide a valid official email address.", 'danger')
        return redirect(url_for('admin_settings', tab='contact'))

    # 1. Update corporate_office
    db.update_contact_setting('corporate_office',
                              value=corp_office,
                              is_enabled=1 if request.form.get('is_enabled_corporate_office') else 0,
                              display_order=request.form.get('order_corporate_office', 10),
                              label=request.form.get('label_corporate_office', 'Corporate Office'))

    # 2. Update company_phone
    db.update_contact_setting('company_phone',
                              value=company_phone,
                              is_enabled=1 if request.form.get('is_enabled_company_phone') else 0,
                              display_order=request.form.get('order_company_phone', 20),
                              label=request.form.get('label_company_phone', 'Call Us'),
                              link_type='tel')

    # 3. Update company_whatsapp
    db.update_contact_setting('company_whatsapp',
                              value=company_whatsapp,
                              is_enabled=1 if request.form.get('is_enabled_company_whatsapp') else 0,
                              display_order=request.form.get('order_company_whatsapp', 30),
                              label=request.form.get('label_company_whatsapp', 'WhatsApp Desk'),
                              link_type='whatsapp')

    # 4. Update company_email
    db.update_contact_setting('company_email',
                              value=company_email,
                              is_enabled=1 if request.form.get('is_enabled_company_email') else 0,
                              display_order=request.form.get('order_company_email', 40),
                              label=request.form.get('label_company_email', 'Email Address'),
                              link_type='mailto')

    # 5. Update company_rera
    db.update_contact_setting('company_rera',
                              value=company_rera,
                              is_enabled=1 if request.form.get('is_enabled_company_rera') else 0,
                              display_order=request.form.get('order_company_rera', 50),
                              label=request.form.get('label_company_rera', 'MahaRERA Reg. No.'))

    # 6. Update branch_office
    db.update_contact_setting('branch_office',
                              value=branch_office,
                              is_enabled=1 if request.form.get('is_enabled_branch_office') else 0,
                              display_order=request.form.get('order_branch_office', 60),
                              label=request.form.get('label_branch_office', 'Branch Office'))

    # 7. Update working_hours
    db.update_contact_setting('working_hours',
                              value=working_hours,
                              is_enabled=1 if request.form.get('is_enabled_working_hours') else 0,
                              display_order=request.form.get('order_working_hours', 70),
                              label=request.form.get('label_working_hours', 'Working Hours'))

    # 8. Update google_maps_url
    db.update_contact_setting('google_maps_url',
                              value=google_maps_url,
                              is_enabled=1 if request.form.get('is_enabled_google_maps_url') else 0,
                              display_order=request.form.get('order_google_maps_url', 80),
                              label=request.form.get('label_google_maps_url', 'Google Maps Location'),
                              link_type='url')

    # Update any custom contact fields
    all_settings = db.get_all_contact_settings()
    for item in all_settings:
        if item.get('is_custom'):
            f_key = item['field_key']
            val = request.form.get(f"val_{f_key}")
            lbl = request.form.get(f"lbl_{f_key}")
            ord_v = request.form.get(f"order_{f_key}")
            enb = 1 if request.form.get(f"is_enabled_{f_key}") else 0
            icn = request.form.get(f"icon_{f_key}")
            lnk = request.form.get(f"link_{f_key}")
            if val is not None and lbl is not None:
                db.update_contact_setting(f_key, value=val, label=lbl, is_enabled=enb, display_order=ord_v, icon=icn, link_type=lnk)

    # Sync with system_settings for backwards-compatibility
    db.set_setting('company_phone', company_phone)
    db.set_setting('company_whatsapp', company_whatsapp)
    db.set_setting('company_email', company_email)
    db.set_setting('company_address', corp_office)
    db.set_setting('company_rera', company_rera)

    db.log_user_activity(admin_user, 'admin', 'Settings Update', ip_addr, "Updated Office & Contact Settings")
    flash("Office & Contact Information updated successfully. All changes are immediately live across the website.", 'success')
    return redirect(url_for('admin_settings', tab='contact'))

@app.route('/admin/settings/contact/custom/delete/<field_key>', methods=['GET', 'POST'])
@admin_required
def admin_settings_contact_delete(field_key):
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    ip_addr = request.remote_addr or '127.0.0.1'
    if field_key:
        db.delete_contact_setting(field_key)
        db.log_user_activity(admin_user, 'admin', 'Settings Delete', ip_addr, f"Deleted Contact field '{field_key}'")
        flash("Contact information field deleted successfully.", 'success')
    return redirect(url_for('admin_settings', tab='contact'))

@app.route('/admin/settings/general', methods=['GET', 'POST'])
@admin_required
def admin_settings_general():
    if request.method == 'GET':
        return redirect(url_for('admin_settings', tab='general'))

    action = request.form.get('action', 'save').strip().lower()
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    ip_addr = request.remote_addr or '127.0.0.1'

    if action == 'reset':
        old_name = db.get_website_name()
        default_name = "GRN Properties"
        db.set_website_name(default_name)
        update_logo_svg(default_name)

        # Synchronize WhatsApp message if it contains old name
        current_wa = db.get_whatsapp_message()
        if old_name and old_name in current_wa and old_name != default_name:
            updated_wa = current_wa.replace(old_name, default_name)
            db.set_whatsapp_message(updated_wa)

        db.log_user_activity(admin_user, 'admin', 'Settings Reset', ip_addr, f"Reset Project / Website Name to default: {default_name}")

        msg = f"Project / Website name has been reset to default ({default_name})."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': msg, 'website_name': default_name})

        flash(msg, 'success')
        return redirect(url_for('admin_settings', tab='general'))

    # Save / Update action
    new_name = request.form.get('website_name', '').strip()
    if not new_name:
        err_msg = "Project / Website Name cannot be blank."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': err_msg}), 400
        flash(err_msg, 'danger')
        return redirect(url_for('admin_settings', tab='general'))

    old_name = db.get_website_name()
    db.set_website_name(new_name)
    update_logo_svg(new_name)

    # Automatically synchronize website name in WhatsApp default message if present
    current_wa = db.get_whatsapp_message()
    if old_name and old_name in current_wa and old_name != new_name:
        updated_wa = current_wa.replace(old_name, new_name)
        db.set_whatsapp_message(updated_wa)

    db.log_user_activity(admin_user, 'admin', 'Settings Update', ip_addr, f"Updated Project / Website Name from '{old_name}' to '{new_name}'")

    success_msg = f"Project / Website Name updated to '{new_name}' successfully."
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': success_msg, 'website_name': new_name})

    flash(success_msg, 'success')
    return redirect(url_for('admin_settings', tab='general'))

@app.route('/admin/settings/whatsapp', methods=['GET', 'POST'])
@admin_required
def admin_settings_whatsapp():
    if request.method == 'GET':
        return redirect(url_for('admin_settings', tab='whatsapp'))

    action = request.form.get('action', 'save').strip().lower()
    admin_user = session.get('admin_username') or session.get('username') or 'admin'
    ip_addr = request.remote_addr or '127.0.0.1'

    contact_dict = db.get_contact_settings_dict()
    wa_item = contact_dict.get('company_whatsapp', {})
    company_wa = wa_item.get('value') or Config.COMPANY_WHATSAPP
    company_wa_raw = re.sub(r'\D', '', company_wa) or Config.COMPANY_WHATSAPP_RAW

    if action == 'reset':
        db.reset_whatsapp_settings_to_default()
        db.log_user_activity(admin_user, 'admin', 'Settings Reset', ip_addr, "Reset WhatsApp Message Settings to default")

        reset_settings = db.get_all_whatsapp_settings()
        default_general_msg = db.format_whatsapp_message()
        msg = "WhatsApp message settings have been reset to system defaults."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': msg, 
                'whatsapp_message': reset_settings['default_message'],
                'whatsapp_default_message': reset_settings['default_message'],
                'whatsapp_listing_title_format': reset_settings['listing_title_format'],
                'whatsapp_listing_url_format': reset_settings['listing_url_format'],
                'whatsapp_additional_message': reset_settings['additional_message'],
                'whatsapp_url': f"https://wa.me/{company_wa_raw}?text={quote(default_general_msg)}"
            })

        flash(msg, 'success')
        return redirect(url_for('admin_settings', tab='whatsapp'))

    # Save / Update action
    # Support both whatsapp_default_message and fallback to whatsapp_message
    default_msg = request.form.get('whatsapp_default_message', '').strip()
    if not default_msg:
        default_msg = request.form.get('whatsapp_message', '').strip()

    title_fmt = request.form.get('whatsapp_listing_title_format', '').strip()
    url_fmt = request.form.get('whatsapp_listing_url_format', '').strip()
    add_msg = request.form.get('whatsapp_additional_message', '').strip()

    if not default_msg:
        err_msg = "Default WhatsApp Contact Message cannot be blank."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': err_msg}), 400
        flash(err_msg, 'danger')
        return redirect(url_for('admin_settings', tab='whatsapp'))

    db.set_whatsapp_settings(default_message=default_msg,
                             listing_title_format=title_fmt or "Property / Listing Name: {{listing_title}}.",
                             listing_url_format=url_fmt or "Property Details Link: {{listing_url}}",
                             additional_message=add_msg)
    db.log_user_activity(admin_user, 'admin', 'Settings Update', ip_addr, "Updated WhatsApp Message Settings")

    updated_settings = db.get_all_whatsapp_settings()
    general_msg = db.format_whatsapp_message()
    success_msg = "WhatsApp Message Settings updated successfully. Changes are now active across all website buttons."
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': success_msg, 
            'whatsapp_message': updated_settings['default_message'],
            'whatsapp_default_message': updated_settings['default_message'],
            'whatsapp_listing_title_format': updated_settings['listing_title_format'],
            'whatsapp_listing_url_format': updated_settings['listing_url_format'],
            'whatsapp_additional_message': updated_settings['additional_message'],
            'whatsapp_url': f"https://wa.me/{company_wa_raw}?text={quote(general_msg)}"
        })

    flash(success_msg, 'success')
    return redirect(url_for('admin_settings', tab='whatsapp'))

# ----------------- AGENT & OWNER ENQUIRY FEEDBACK MODULE ----------------- #

@app.route('/dashboard/feedback')
@login_required
def user_feedback():
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        flash('You do not have permission to access the Feedback Management module. Please contact Admin.', 'danger')
        return redirect(url_for('user_dashboard'))

    req_per_page = request.args.get('per_page')
    if req_per_page is not None:
        try:
            req_int = int(req_per_page)
        except (ValueError, TypeError):
            req_int = 10
        per_page = db.set_records_per_page_preference(user_id=session['user_id'], section='feedback', per_page=req_int)
    else:
        per_page = db.get_records_per_page_preference(user_id=session['user_id'], section='feedback')

    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    project = request.args.get('project', '').strip()
    source = request.args.get('source', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    if sort not in ['newest', 'oldest']:
        sort = 'newest'

    filters = {}
    if q:
        filters['search'] = q
    if project:
        filters['project_name'] = project
    if source:
        filters['source'] = source
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to

    total_count = db.get_feedbacks_count(filters)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    feedbacks = db.get_all_feedbacks(filters, page=page, per_page=per_page, sort=sort)
    distinct_projects = db.get_distinct_feedback_projects()
    property_projects = [p['title'] for p in db.get_all_properties(filters={'user_id': session['user_id']}, limit=50)]
    lead_sources = db.get_active_lead_sources()

    return render_template(
        'dashboard/feedback.html',
        feedbacks=feedbacks,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        q=q,
        project=project,
        selected_source=source,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        distinct_projects=distinct_projects,
        property_projects=property_projects,
        lead_sources=lead_sources
    )

@app.route('/dashboard/feedback/add', methods=['POST'])
@login_required
def user_feedback_add():
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        flash('Permission denied to add feedback.', 'danger')
        return redirect(url_for('user_dashboard'))

    client_name = request.form.get('client_name', '').strip()
    client_contact = request.form.get('client_contact', '').strip()
    enquiry_datetime = request.form.get('enquiry_datetime', '').strip()
    enquiry_source = request.form.get('enquiry_source', 'Website Direct').strip() or 'Website Direct'
    project_name = request.form.get('project_name', '').strip()
    configuration = request.form.get('configuration', '').strip()
    cost = request.form.get('cost', '').strip()
    carpet = request.form.get('carpet', '').strip()
    possession = request.form.get('possession', '').strip()
    website_enquiry_url = request.form.get('website_enquiry_url', '').strip()
    client_feedback = request.form.get('client_feedback', '').strip()

    if not client_name or not client_contact or not project_name or not client_feedback:
        flash('Please fill in all required fields (Client Name, Contact, Project Name, and Feedback).', 'danger')
        return redirect(url_for('user_feedback'))

    feedback_data = {
        'client_name': client_name,
        'client_contact': client_contact,
        'enquiry_datetime': enquiry_datetime or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'enquiry_source': enquiry_source,
        'project_name': project_name,
        'configuration': configuration,
        'cost': cost,
        'carpet': carpet,
        'possession': possession,
        'website_enquiry_url': website_enquiry_url,
        'client_feedback': client_feedback,
        'feedback_by_username': session.get('username'),
        'role': session.get('user_role', 'agent')
    }

    feedback_id = db.create_feedback(feedback_data)
    flash(f'Enquiry feedback #{feedback_id} recorded successfully.', 'success')
    return redirect(url_for('user_feedback'))

@app.route('/dashboard/feedback/edit/<int:feedback_id>', methods=['POST'])
@login_required
def user_feedback_edit(feedback_id):
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        flash('Permission denied.', 'danger')
        return redirect(url_for('user_dashboard'))

    fb = db.get_feedback_by_id(feedback_id)
    if not fb:
        flash('Feedback record not found.', 'danger')
        return redirect(url_for('user_feedback'))

    client_name = request.form.get('client_name', '').strip()
    client_contact = request.form.get('client_contact', '').strip()
    enquiry_datetime = request.form.get('enquiry_datetime', '').strip()
    enquiry_source = request.form.get('enquiry_source', 'Website Direct').strip() or 'Website Direct'
    project_name = request.form.get('project_name', '').strip()
    configuration = request.form.get('configuration', '').strip()
    cost = request.form.get('cost', '').strip()
    carpet = request.form.get('carpet', '').strip()
    possession = request.form.get('possession', '').strip()
    website_enquiry_url = request.form.get('website_enquiry_url', '').strip()
    client_feedback = request.form.get('client_feedback', '').strip()

    update_data = {
        'client_name': client_name,
        'client_contact': client_contact,
        'enquiry_datetime': enquiry_datetime,
        'enquiry_source': enquiry_source,
        'project_name': project_name,
        'configuration': configuration,
        'cost': cost,
        'carpet': carpet,
        'possession': possession,
        'website_enquiry_url': website_enquiry_url,
        'client_feedback': client_feedback,
        'updated_by': session.get('username'),
        'role': session.get('user_role', 'agent')
    }

    db.update_feedback(feedback_id, update_data)
    flash(f'Feedback #{feedback_id} updated successfully.', 'success')
    return redirect(url_for('user_feedback'))

@app.route('/dashboard/feedback/delete/<int:feedback_id>', methods=['POST'])
@login_required
def user_feedback_delete(feedback_id):
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        flash('Permission denied.', 'danger')
        return redirect(url_for('user_dashboard'))

    db.delete_feedback(
        feedback_id,
        username=session.get('username'),
        role=session.get('user_role', 'agent')
    )
    flash(f'Feedback #{feedback_id} deleted successfully.', 'info')
    return redirect(url_for('user_feedback'))

@app.route('/dashboard/feedback/bulk-delete', methods=['POST'])
@login_required
def user_feedback_bulk_delete():
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Permission denied.'}), 403
        flash('Permission denied to manage feedback.', 'danger')
        return redirect(url_for('user_dashboard'))

    ids = _extract_ids_from_request(request)
    result = db.bulk_delete_feedbacks(
        ids,
        username=session.get('username'),
        role=session.get('user_role', 'agent')
    )
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result), (200 if result['success'] else 400)

    if result['success']:
        flash(f"Successfully permanently deleted {result['count']} selected feedback record(s).", 'success')
    else:
        flash(result.get('message', 'Failed to delete selected feedback records.'), 'danger')
    return redirect(request.referrer or url_for('user_feedback'))

@app.route('/dashboard/feedback/export')
@login_required
def user_feedback_export():
    import io
    from flask import send_file
    import feedback_service as fs

    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        flash('Permission denied.', 'danger')
        return redirect(url_for('user_dashboard'))

    filters = {}
    if request.args.get('q'):
        filters['search'] = request.args.get('q').strip()
    if request.args.get('project'):
        filters['project_name'] = request.args.get('project').strip()
    if request.args.get('source'):
        filters['source'] = request.args.get('source').strip()

    feedbacks = db.get_all_feedbacks_for_export(filters)
    excel_bytes = fs.generate_feedback_excel_bytes(feedbacks)

    filename = f"My_Enquiry_Feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/dashboard/feedback/refresh', methods=['POST', 'GET'])
@login_required
def user_feedback_refresh():
    """
    User/Agent Refresh Enquiries:
    Fetches newly received enquiries for this user or portal directly into Feedback.
    """
    current_u = db.get_user_by_id(session['user_id'])
    if not current_u or not current_u.get('can_manage_feedback', 1):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Permission denied.'}), 403
        flash('Permission denied to refresh feedback enquiries.', 'danger')
        return redirect(url_for('user_dashboard'))

    try:
        username = session.get('username') or 'agent'
        role = session.get('user_role', 'agent')
        user_id = session.get('user_id')
        count, message = db.sync_website_enquiries_to_feedback(username=username, role=role, user_id=user_id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'count': count,
                'message': message
            })
            
        flash(message, 'success' if count > 0 else 'info')
        return redirect(url_for('user_feedback'))
    except Exception as e:
        app.logger.error(f"Error in user_feedback_refresh: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': False,
                'count': 0,
                'message': f"Database or system error: {str(e)}"
            }), 500
        flash(f"Error refreshing enquiries: {str(e)}", 'danger')
        return redirect(url_for('user_feedback'))

# ----------------- ERROR HANDLERS ----------------- #

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    db.init_db()
    app.run(debug=True, port=5000)
