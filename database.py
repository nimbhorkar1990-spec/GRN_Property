import sqlite3
import json
import os
import re
from datetime import datetime, timezone
from config import Config

def get_db():
    """Get database connection with row factory enabled."""
    os.makedirs(Config.DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    """Ensure database schema has all fields for Agent & Owner functionality."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Check users columns
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row['name'] for row in cursor.fetchall()]
    if 'role' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'owner'")
    if 'phone' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if 'agency_name' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN agency_name TEXT")
    if 'rera_number' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN rera_number TEXT")
    if 'status' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if 'listing_limit' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN listing_limit INTEGER DEFAULT 10")
    if 'upload_limit' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN upload_limit INTEGER DEFAULT 10")
    if 'can_post_ads' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_post_ads INTEGER DEFAULT 1")
    if 'can_edit_ads' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_edit_ads INTEGER DEFAULT 1")
    if 'can_delete_ads' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_delete_ads INTEGER DEFAULT 1")
    if 'can_access_crm' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_access_crm INTEGER DEFAULT 1")
    if 'can_export_leads' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_export_leads INTEGER DEFAULT 1")
    if 'can_feature_properties' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_feature_properties INTEGER DEFAULT 0")
    if 'can_manage_feedback' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN can_manage_feedback INTEGER DEFAULT 1")
    if 'last_login' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    if 'notes' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN notes TEXT")
    if 'theme_preference' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT 'luxury-gold'")
    if 'monthly_enquiries_limit' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN monthly_enquiries_limit INTEGER DEFAULT 100")
    if 'photos_limit' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN photos_limit INTEGER DEFAULT 10")
    if 'videos_limit' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN videos_limit INTEGER DEFAULT 2")
    if 'has_custom_limits' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN has_custom_limits INTEGER DEFAULT 0")
    if 'monthly_enquiries_used' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN monthly_enquiries_used INTEGER DEFAULT 0")
    if 'monthly_enquiries_reset_date' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN monthly_enquiries_reset_date TEXT DEFAULT ''")
    if 'leads_per_page' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN leads_per_page INTEGER DEFAULT 10")
    if 'feedback_per_page' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN feedback_per_page INTEGER DEFAULT 10")

    # Ensure admin user has role 'admin' and full unlimited permissions
    cursor.execute("""
        UPDATE users SET 
            role = 'admin',
            listing_limit = -1,
            monthly_enquiries_limit = -1,
            photos_limit = 50,
            videos_limit = 10,
            upload_limit = 50,
            has_custom_limits = 1,
            can_post_ads = 1,
            can_edit_ads = 1,
            can_delete_ads = 1,
            can_access_crm = 1,
            can_export_leads = 1,
            can_feature_properties = 1,
            can_manage_feedback = 1
        WHERE username = 'admin'
    """)

    # 2. Check properties columns
    cursor.execute("PRAGMA table_info(properties)")
    prop_cols = [row['name'] for row in cursor.fetchall()]
    if 'user_id' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN user_id INTEGER DEFAULT 1")
    if 'contact_person' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN contact_person TEXT")
    if 'contact_phone' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN contact_phone TEXT")
    if 'city' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN city TEXT DEFAULT 'Pune'")
    if 'rera_locked' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN rera_locked INTEGER DEFAULT 0")
    if 'rejection_reason' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN rejection_reason TEXT")
    if 'video_urls' not in prop_cols:
        cursor.execute("ALTER TABLE properties ADD COLUMN video_urls TEXT DEFAULT '[]'")

    # Backfill city for existing records
    cursor.execute("UPDATE properties SET city = 'Pune' WHERE city IS NULL OR city = ''")
    # For existing activated properties, lock rera_number
    cursor.execute("UPDATE properties SET rera_locked = 1 WHERE status IN ('Available', 'Active', 'Sold', 'Rented') AND rera_number IS NOT NULL AND rera_number != ''")

    # 3. Check enquiries columns
    cursor.execute("PRAGMA table_info(enquiries)")
    enq_cols = [row['name'] for row in cursor.fetchall()]
    if 'property_owner_id' not in enq_cols:
        cursor.execute("ALTER TABLE enquiries ADD COLUMN property_owner_id INTEGER DEFAULT 1")
    if 'lead_source' not in enq_cols:
        cursor.execute("ALTER TABLE enquiries ADD COLUMN lead_source TEXT DEFAULT 'Website Direct'")
        cursor.execute("UPDATE enquiries SET lead_source = 'Website Direct' WHERE lead_source IS NULL OR lead_source = ''")
    if 'website_enquiry_url' not in enq_cols:
        cursor.execute("ALTER TABLE enquiries ADD COLUMN website_enquiry_url TEXT")
        # Backfill website_enquiry_url for existing enquiries using linked property slug or enquiry type
        cursor.execute("""
            UPDATE enquiries 
            SET website_enquiry_url = (
                SELECT '/property/' || p.slug 
                FROM properties p 
                WHERE p.id = enquiries.property_id AND p.slug IS NOT NULL AND p.slug != ''
            )
            WHERE property_id IS NOT NULL AND (website_enquiry_url IS NULL OR website_enquiry_url = '')
        """)
        cursor.execute("""
            UPDATE enquiries 
            SET website_enquiry_url = CASE 
                WHEN enquiry_type LIKE '%Sell%' THEN '/sell'
                WHEN enquiry_type LIKE '%Contact%' THEN '/contact'
                WHEN enquiry_type LIKE '%Site Visit%' OR enquiry_type LIKE '%Homepage%' THEN '/'
                ELSE '/properties'
            END
            WHERE website_enquiry_url IS NULL OR website_enquiry_url = ''
        """)

    # 4. Check & Create New SQL Tables (Lead Sources, Enquiry Feedback, Visitor Sessions, User Activity Logs, System Settings)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lead_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT UNIQUE NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enquiry_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enquiry_id INTEGER,
        client_name TEXT NOT NULL,
        client_contact TEXT NOT NULL,
        enquiry_datetime TEXT NOT NULL,
        enquiry_source TEXT DEFAULT 'Website Direct',
        project_name TEXT NOT NULL,
        configuration TEXT,
        cost REAL,
        carpet TEXT,
        possession TEXT,
        website_enquiry_url TEXT,
        client_feedback TEXT NOT NULL,
        feedback_by_username TEXT NOT NULL,
        feedback_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Check enquiry_feedback columns for enquiry_source and enquiry_id if table already existed
    cursor.execute("PRAGMA table_info(enquiry_feedback)")
    fb_cols = [row['name'] for row in cursor.fetchall()]
    if 'enquiry_source' not in fb_cols:
        cursor.execute("ALTER TABLE enquiry_feedback ADD COLUMN enquiry_source TEXT DEFAULT 'Website Direct'")
        cursor.execute("UPDATE enquiry_feedback SET enquiry_source = 'Website Direct' WHERE enquiry_source IS NULL OR enquiry_source = ''")
    if 'enquiry_id' not in fb_cols:
        cursor.execute("ALTER TABLE enquiry_feedback ADD COLUMN enquiry_id INTEGER")

    # Seed default CRM lead sources if table is empty
    cursor.execute("SELECT COUNT(*) as cnt FROM lead_sources")
    if cursor.fetchone()['cnt'] == 0:
        default_lead_sources = [
            ("Website Direct", "Direct website visitor inquiries and landing page forms", 1),
            ("Google Search / Ads", "Google paid search and organic search visitors", 2),
            ("Facebook / Instagram Ads", "Meta social media advertisement campaigns", 3),
            ("MagicBricks", "MagicBricks real estate portal leads", 4),
            ("99acres", "99acres property listing portal leads", 5),
            ("Housing.com", "Housing.com partner portal inquiries", 6),
            ("Referral / Word of Mouth", "Existing customer and client referrals", 7),
            ("Channel Partner / Broker", "Real estate brokers and channel partner networks", 8),
            ("Walk-in / Site Visit", "Direct site visit and office walk-ins", 9),
            ("Newspaper / Hoarding", "Print media, hoardings, and outdoor advertisements", 10),
            ("Cold Call / SMS Campaign", "Outbound calling and promotional SMS blasts", 11),
            ("WhatsApp Campaign", "WhatsApp direct messaging and catalogue inquiries", 12)
        ]
        for s_name, s_desc, s_order in default_lead_sources:
            cursor.execute("INSERT OR IGNORE INTO lead_sources (source_name, description, display_order, is_active) VALUES (?, ?, ?, 1)", (s_name, s_desc, s_order))

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visitor_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        username TEXT,
        role TEXT DEFAULT 'visitor',
        is_authenticated INTEGER DEFAULT 0,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        role TEXT,
        activity_type TEXT NOT NULL,
        ip_address TEXT,
        activity_date TEXT NOT NULL,
        activity_time TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('admin_email', 'contact@realestate.com')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('website_name', 'GRN Properties')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('whatsapp_default_message', 'Hi GRN Properties, I am looking for property consultation in Pune.')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('whatsapp_listing_title_format', 'Property / Listing Name: {{listing_title}}.')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('whatsapp_listing_url_format', 'Property Details Link: {{listing_url}}')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('whatsapp_additional_message', 'Please share the complete property details, pricing, location and site visit availability.')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('default_listings_limit', '10')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('default_monthly_enquiries_limit', '100')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('default_photos_limit', '10')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('default_videos_limit', '2')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('admin_leads_per_page', '10')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('admin_feedback_per_page', '10')")

    # Office & Contact Settings Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contact_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_key TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        value TEXT NOT NULL DEFAULT '',
        icon TEXT DEFAULT 'fas fa-info-circle',
        is_enabled INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        is_custom INTEGER DEFAULT 0,
        category TEXT DEFAULT 'general',
        link_type TEXT DEFAULT 'none',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    default_contact_settings = [
        ('corporate_office', 'Corporate Office', 'Office 405, Platinum Square, Near Balewadi High Street, Baner-Balewadi Road, Pune, Maharashtra 411045', 'fas fa-map-marked-alt', 1, 10, 0, 'office', 'none'),
        ('company_phone', 'Call Us', '+91 7499077170', 'fas fa-phone-alt', 1, 20, 0, 'phone', 'tel'),
        ('company_whatsapp', 'WhatsApp Desk', '+91 7499077170', 'fab fa-whatsapp', 1, 30, 0, 'whatsapp', 'whatsapp'),
        ('company_email', 'Email Address', 'contact@realestate.com', 'fas fa-envelope', 1, 40, 0, 'email', 'mailto'),
        ('company_rera', 'MahaRERA Reg. No.', 'MahaRERA Reg. No: A52100034982', 'fas fa-shield-alt', 1, 50, 0, 'rera', 'none'),
        ('branch_office', 'Branch Office', 'Tower B, Phase 1, Hinjewadi IT Park, Pune, Maharashtra 411057', 'fas fa-building', 1, 60, 0, 'office', 'none'),
        ('working_hours', 'Working Hours', 'Mon - Sat: 9:30 AM - 7:30 PM | Sun: By Appointment', 'fas fa-clock', 1, 70, 0, 'timing', 'none'),
        ('google_maps_url', 'Google Maps Location', 'https://maps.google.com/maps?q=Balewadi+High+Street,+Pune,+Maharashtra&t=&z=14&ie=UTF8&iwloc=&output=embed', 'fas fa-map-marker-alt', 1, 80, 0, 'map', 'url'),
    ]

    for item in default_contact_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO contact_settings 
            (field_key, label, value, icon, is_enabled, display_order, is_custom, category, link_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', item)

    # 5. Website Visibility Management Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS website_visibility (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        url_path TEXT,
        description TEXT,
        is_visible INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by TEXT DEFAULT 'admin'
    )
    ''')

    # Seed default visibility settings
    default_visibility_items = [
        # Header Navigation Menus
        ('nav_home', 'Home Menu', 'Header Navigation', '/', 'Main header navigation link to homepage', 1, 10),
        ('nav_buy', 'Buy Menu', 'Header Navigation', '/buy', 'Main header navigation link to properties for sale', 1, 20),
        ('nav_sell', 'Sell Menu', 'Header Navigation', '/sell', 'Main header navigation link to sell property page', 1, 30),
        ('nav_rent', 'Rent Menu', 'Header Navigation', '/rent', 'Main header navigation link to rental properties', 1, 40),
        ('nav_commercial', 'Commercial Menu', 'Header Navigation', '/commercial', 'Main header navigation link to commercial properties', 1, 50),
        ('nav_all_properties', 'All Properties Menu', 'Header Navigation', '/properties', 'Main header navigation link to all property listings', 1, 60),
        ('nav_about', 'About Us Menu', 'Header Navigation', '/about', 'Main header navigation link to about page', 1, 70),
        ('nav_contact', 'Contact Menu', 'Header Navigation', '/contact', 'Main header navigation link to contact page', 1, 80),
        ('nav_post_ad', 'Post Property Ad Button', 'Header Navigation', '/dashboard/properties/add', 'Header action button to post a new property ad', 1, 90),
        ('nav_schedule_visit', 'Schedule Visit Header Button', 'Header Navigation', '#scheduleVisitModal', 'Header gold button to trigger site visit modal', 1, 100),

        # Main Website Pages & Routes
        ('page_home', 'Home Page', 'Main Pages', '/', 'Public home landing page', 1, 10),
        ('page_buy', 'Buy Properties Page', 'Main Pages', '/buy', 'Property listings filtered for sale', 1, 20),
        ('page_sell', 'Sell Property Page', 'Main Pages', '/sell', 'Sell property landing and submission page', 1, 30),
        ('page_rent', 'Rent Properties Page', 'Main Pages', '/rent', 'Property listings filtered for rent', 1, 40),
        ('page_commercial', 'Commercial Properties Page', 'Main Pages', '/commercial', 'Commercial property listings page', 1, 50),
        ('page_all_properties', 'All Properties Catalog', 'Main Pages', '/properties', 'Complete property listings search catalog', 1, 60),
        ('page_property_detail', 'Property Details Page', 'Main Pages', '/property/<slug>', 'Individual property detail view page', 1, 70),
        ('page_about', 'About Us Page', 'Main Pages', '/about', 'Company background and about us page', 1, 80),
        ('page_services', 'Our Services Page', 'Main Pages', '/services', 'Real estate consultancy services page', 1, 90),
        ('page_contact', 'Contact Us Page', 'Main Pages', '/contact', 'Contact form and corporate office information page', 1, 100),
        ('page_privacy', 'Privacy Policy Page', 'Main Pages', '/privacy-policy', 'Legal privacy policy terms page', 1, 110),
        ('page_terms', 'Terms of Service Page', 'Main Pages', '/terms', 'Terms of service and conditions page', 1, 120),

        # Homepage Sections
        ('section_hero_search', 'Hero Banner & Search Card', 'Homepage Sections', '/', 'Homepage top hero banner with multi-filter property search card', 1, 10),
        ('section_quick_stats', 'Quick Counter Stats', 'Homepage Sections', '/', 'Homepage statistics counter (15+ Years, 500+ Projects, etc.)', 1, 20),
        ('section_featured_properties', 'Featured Properties Showcase', 'Homepage Sections', '/', 'Homepage luxury featured property cards showcase', 1, 30),
        ('section_property_categories', 'Property Categories Grid', 'Homepage Sections', '/', 'Homepage property category exploration grid', 1, 40),
        ('section_pune_locations', 'Pune Micro-Markets Spotlight', 'Homepage Sections', '/', 'Homepage prime Pune localities and micro-markets spotlight', 1, 50),
        ('section_why_choose_us', 'Why Choose Us Section', 'Homepage Sections', '/', 'Homepage key value proposition and reasons to choose GRN', 1, 60),
        ('section_our_services', 'Real Estate Services Section', 'Homepage Sections', '/', 'Homepage full real estate services overview', 1, 70),
        ('section_testimonials', 'Customer Testimonials', 'Homepage Sections', '/', 'Homepage verified client testimonials and feedback reviews', 1, 80),
        ('section_cta_banner', 'Site Visit Call-To-Action Banner', 'Homepage Sections', '/', 'Homepage full-width site visit booking banner', 1, 90),

        # Property Listings & Details
        ('prop_search_filters', 'Search & Filter Sidebar', 'Property Listings & Details', '/properties', 'Property listing filter sidebar (type, price, BHK, location)', 1, 10),
        ('prop_gallery', 'Property Image Gallery', 'Property Listings & Details', '/property/<slug>', 'Property detail page interactive photo gallery', 1, 20),
        ('prop_overview', 'Property Overview & MahaRERA', 'Property Listings & Details', '/property/<slug>', 'Property overview description and MahaRERA verification card', 1, 30),
        ('prop_amenities', 'Amenities Showcase', 'Property Listings & Details', '/property/<slug>', 'Property detail page world-class amenities list', 1, 40),
        ('prop_floor_plans', 'Floor Plans & Layouts', 'Property Listings & Details', '/property/<slug>', 'Architectural layout and floor plan section', 1, 50),
        ('prop_landmarks', 'Connectivity & Landmarks', 'Property Listings & Details', '/property/<slug>', 'Nearby transit, schools, hospitals, and landmarks', 1, 60),
        ('prop_emi_calculator', 'Home Loan EMI Calculator', 'Property Listings & Details', '/property/<slug>', 'Interactive monthly EMI calculator tool', 1, 70),
        ('prop_agent_card', 'Agent / Owner Contact Card', 'Property Listings & Details', '/property/<slug>', 'Sidebar verified contact card and direct call/whatsapp', 1, 80),
        ('prop_similar_properties', 'Similar Properties Recommendations', 'Property Listings & Details', '/property/<slug>', 'Recommendations carousel of similar nearby properties', 1, 90),

        # Forms & Interactive Tools
        ('form_schedule_visit', 'Schedule Site Visit Modal Form', 'Forms & Tools', '#scheduleVisitModal', 'Universal site visit appointment booking modal form', 1, 10),
        ('form_property_enquiry', 'Property Detail Enquiry Form', 'Forms & Tools', '/property/<slug>', 'Sidebar property specific enquiry and callback form', 1, 20),
        ('form_sell_property', 'Sell Property Listing Form', 'Forms & Tools', '/sell', 'Sell property submission form for property owners', 1, 30),
        ('form_contact', 'Contact Us Form', 'Forms & Tools', '/contact', 'General contact enquiry form', 1, 40),
        ('action_whatsapp_float', 'Floating WhatsApp Button', 'Forms & Tools', 'All Pages', 'Bottom-right floating WhatsApp quick chat button', 1, 50),
        ('action_mobile_call_bar', 'Mobile Sticky Call & WhatsApp Bar', 'Forms & Tools', 'Mobile Only', 'Sticky bottom call and WhatsApp quick bar for mobile devices', 1, 60),
        ('action_theme_switcher', 'Theme Switcher Engine', 'Forms & Tools', 'All Pages', 'Header theme switcher and floating color palette tool', 1, 70),

        # Footer Menus & Links
        ('footer_about_col', 'Footer Company Info Column', 'Footer Menus & Links', 'Footer', 'Footer brand logo, corporate intro, and social media icons', 1, 10),
        ('footer_quick_links', 'Footer Quick Navigation Links', 'Footer Menus & Links', 'Footer', 'Footer quick links column', 1, 20),
        ('footer_locations_col', 'Footer Pune Micro-Markets Column', 'Footer Menus & Links', 'Footer', 'Footer Pune localities and micro-markets column', 1, 30),
        ('footer_contact_col', 'Footer Office & Contact Column', 'Footer Menus & Links', 'Footer', 'Footer corporate office address, phones, and RERA badge', 1, 40),
        ('footer_social_links', 'Footer Social Media Links', 'Footer Menus & Links', 'Footer', 'Facebook, Instagram, LinkedIn, and WhatsApp social links', 1, 50),
        ('footer_legal_links', 'Footer Privacy & Terms Links', 'Footer Menus & Links', 'Footer', 'Bottom copyright bar Privacy Policy and Terms of Service links', 1, 60)
    ]

    for item in default_visibility_items:
        cursor.execute("""
            INSERT OR IGNORE INTO website_visibility 
            (item_key, name, category, url_path, description, is_visible, display_order) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, item)

    conn.commit()
    conn.close()

def init_db():
    """Initialize database tables."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'owner',
        phone TEXT,
        agency_name TEXT,
        rera_number TEXT,
        status TEXT DEFAULT 'active',
        listing_limit INTEGER DEFAULT 10,
        upload_limit INTEGER DEFAULT 10,
        can_post_ads INTEGER DEFAULT 1,
        can_edit_ads INTEGER DEFAULT 1,
        can_delete_ads INTEGER DEFAULT 1,
        can_access_crm INTEGER DEFAULT 1,
        can_export_leads INTEGER DEFAULT 1,
        can_feature_properties INTEGER DEFAULT 0,
        can_manage_feedback INTEGER DEFAULT 1,
        monthly_enquiries_limit INTEGER DEFAULT 100,
        photos_limit INTEGER DEFAULT 10,
        videos_limit INTEGER DEFAULT 2,
        has_custom_limits INTEGER DEFAULT 0,
        monthly_enquiries_used INTEGER DEFAULT 0,
        monthly_enquiries_reset_date TEXT DEFAULT '',
        leads_per_page INTEGER DEFAULT 10,
        feedback_per_page INTEGER DEFAULT 10,
        last_login TIMESTAMP,
        notes TEXT,
        theme_preference TEXT DEFAULT 'luxury-gold',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Properties table (Default status is 'Under Review' per Admin Approval System)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        title TEXT NOT NULL,
        slug TEXT UNIQUE,
        category TEXT NOT NULL,
        property_type TEXT NOT NULL,
        purpose TEXT NOT NULL,
        price REAL NOT NULL,
        price_display TEXT NOT NULL,
        city TEXT DEFAULT 'Pune',
        location TEXT NOT NULL,
        sub_location TEXT,
        address TEXT,
        configuration TEXT,
        carpet_area INTEGER,
        super_area INTEGER,
        bedrooms INTEGER DEFAULT 0,
        bathrooms INTEGER DEFAULT 0,
        balconies INTEGER DEFAULT 0,
        possession_status TEXT,
        rera_number TEXT,
        rera_locked INTEGER DEFAULT 0,
        featured INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Under Review',
        rejection_reason TEXT,
        featured_image TEXT NOT NULL,
        gallery_images TEXT,
        video_urls TEXT DEFAULT '[]',
        floor_plan_image TEXT,
        description TEXT,
        amenities TEXT,
        nearby_landmarks TEXT,
        contact_person TEXT,
        contact_phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Enquiries table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        property_id INTEGER,
        property_owner_id INTEGER DEFAULT 1,
        property_title TEXT,
        enquiry_type TEXT DEFAULT 'Property Enquiry',
        lead_source TEXT DEFAULT 'Website Direct',
        website_enquiry_url TEXT,
        budget TEXT,
        preferred_location TEXT,
        preferred_date TEXT,
        message TEXT,
        status TEXT DEFAULT 'New',
        admin_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties(id) ON DELETE SET NULL,
        FOREIGN KEY(property_owner_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    conn.commit()
    conn.close()

    # Run migration check
    migrate_db()

# Property Queries
def get_all_properties(filters=None, order_by="created_at DESC", limit=None):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT p.*, u.full_name as owner_name, u.role as owner_role, 
               u.agency_name as owner_agency, u.rera_number as owner_rera, u.phone as owner_phone
        FROM properties p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get('purpose'):
            query += " AND p.purpose = ?"
            params.append(filters['purpose'])
        if filters.get('category'):
            query += " AND p.category = ?"
            params.append(filters['category'])
        if filters.get('property_type'):
            query += " AND p.property_type = ?"
            params.append(filters['property_type'])
        if filters.get('city') and filters.get('city') != 'All':
            query += " AND p.city = ?"
            params.append(filters['city'])
        if filters.get('location'):
            query += " AND (p.location LIKE ? OR p.sub_location LIKE ? OR p.city LIKE ?)"
            loc_val = f"%{filters['location']}%"
            params.extend([loc_val, loc_val, loc_val])
        if filters.get('configuration'):
            query += " AND p.configuration LIKE ?"
            params.append(f"%{filters['configuration']}%")
        
        # Status filtering
        if 'status' in filters:
            st = filters['status']
            if st == 'All':
                pass # All statuses allowed
            elif isinstance(st, (list, tuple)):
                placeholders = ','.join(['?'] * len(st))
                query += f" AND p.status IN ({placeholders})"
                params.extend(st)
            else:
                query += " AND p.status = ?"
                params.append(st)
        elif filters.get('user_id') or filters.get('include_all_status'):
            # Specific user viewing their own or internal query
            pass
        else:
            # Default public filter: only approved listings
            query += " AND p.status IN ('Active', 'Available')"

        if filters.get('featured') is not None:
            query += " AND p.featured = ?"
            params.append(1 if filters['featured'] else 0)
        if filters.get('user_id'):
            query += " AND p.user_id = ?"
            params.append(int(filters['user_id']))
        if filters.get('min_price'):
            try:
                query += " AND p.price >= ?"
                params.append(float(filters['min_price']))
            except (ValueError, TypeError):
                pass
        if filters.get('max_price'):
            try:
                query += " AND p.price <= ?"
                params.append(float(filters['max_price']))
            except (ValueError, TypeError):
                pass
        if filters.get('q'):
            keyword = f"%{filters['q']}%"
            query += " AND (p.title LIKE ? OR p.description LIKE ? OR p.location LIKE ? OR p.sub_location LIKE ? OR p.city LIKE ?)"
            params.extend([keyword, keyword, keyword, keyword, keyword])
    else:
        # Default public listing query without filters
        query += " AND p.status IN ('Active', 'Available')"

    if order_by:
        query += f" ORDER BY p.{order_by}"
    if limit:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_property_by_id(property_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name as owner_name, u.role as owner_role, 
               u.agency_name as owner_agency, u.rera_number as owner_rera, u.phone as owner_phone
        FROM properties p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (property_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_property_by_slug(slug):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name as owner_name, u.role as owner_role, 
               u.agency_name as owner_agency, u.rera_number as owner_rera, u.phone as owner_phone
        FROM properties p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.slug = ?
    """, (slug,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_featured_properties(limit=6):
    return get_all_properties(filters={'featured': 1, 'status': ['Active', 'Available']}, limit=limit)

def get_similar_properties(property_id, category, sub_location, limit=3):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM properties 
        WHERE id != ? AND (category = ? OR sub_location = ?) AND status IN ('Active', 'Available')
        ORDER BY created_at DESC LIMIT ?
    """, (property_id, category, sub_location, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_property(prop_dict):
    conn = get_db()
    cursor = conn.cursor()

    # Ensure user_id defaults to 1 if not specified
    if 'user_id' not in prop_dict or not prop_dict['user_id']:
        prop_dict['user_id'] = 1
    if 'contact_person' not in prop_dict:
        prop_dict['contact_person'] = ''
    if 'contact_phone' not in prop_dict:
        prop_dict['contact_phone'] = ''
    if 'city' not in prop_dict or not prop_dict['city']:
        prop_dict['city'] = 'Pune'
    # Default status is strictly 'Under Review' per Admin Approval System
    if 'status' not in prop_dict or not prop_dict['status']:
        prop_dict['status'] = 'Under Review'
    if 'rera_locked' not in prop_dict:
        prop_dict['rera_locked'] = 0
    if 'rejection_reason' not in prop_dict:
        prop_dict['rejection_reason'] = None
    if 'video_urls' not in prop_dict or not prop_dict['video_urls']:
        prop_dict['video_urls'] = '[]'

    cursor.execute('''
        INSERT INTO properties (
            user_id, title, slug, category, property_type, purpose, price, price_display,
            city, location, sub_location, address, configuration, carpet_area, super_area,
            bedrooms, bathrooms, balconies, possession_status, rera_number, rera_locked,
            featured, status, rejection_reason, featured_image, gallery_images, video_urls, floor_plan_image,
            description, amenities, nearby_landmarks, contact_person, contact_phone
        ) VALUES (
            :user_id, :title, :slug, :category, :property_type, :purpose, :price, :price_display,
            :city, :location, :sub_location, :address, :configuration, :carpet_area, :super_area,
            :bedrooms, :bathrooms, :balconies, :possession_status, :rera_number, :rera_locked,
            :featured, :status, :rejection_reason, :featured_image, :gallery_images, :video_urls, :floor_plan_image,
            :description, :amenities, :nearby_landmarks, :contact_person, :contact_phone
        )
    ''', prop_dict)
    conn.commit()
    prop_id = cursor.lastrowid
    conn.close()
    return prop_id

def update_property(property_id, prop_dict):
    conn = get_db()
    cursor = conn.cursor()
    
    # Retrieve current property to enforce restrictions
    cursor.execute("SELECT title, slug, rera_number, rera_locked, status, city, rejection_reason FROM properties WHERE id = ?", (property_id,))
    current_prop = cursor.fetchone()
    
    prop_dict['id'] = property_id
    if current_prop:
        # Requirement D: Once submitted, Property Title must not be changed across all roles
        prop_dict['title'] = current_prop['title']
        prop_dict['slug'] = current_prop['slug']
        
        # Requirement C: Once activated, MahaRERA Number is permanently locked
        is_activated = (current_prop['rera_locked'] == 1) or (current_prop['status'] in ('Active', 'Available', 'Sold', 'Rented'))
        if is_activated:
            prop_dict['rera_number'] = current_prop['rera_number']
            prop_dict['rera_locked'] = 1
        else:
            # Before activation, can be edited
            prop_dict['rera_locked'] = prop_dict.get('rera_locked', 0)
    else:
        prop_dict['rera_locked'] = prop_dict.get('rera_locked', 0)

    if 'city' not in prop_dict or not prop_dict['city']:
        prop_dict['city'] = current_prop['city'] if current_prop else 'Pune'
    if 'contact_person' not in prop_dict:
        prop_dict['contact_person'] = ''
    if 'contact_phone' not in prop_dict:
        prop_dict['contact_phone'] = ''
    if 'rejection_reason' not in prop_dict:
        prop_dict['rejection_reason'] = current_prop['rejection_reason'] if current_prop else None
    if 'video_urls' not in prop_dict:
        prop_dict['video_urls'] = '[]'

    cursor.execute('''
        UPDATE properties SET
            title = :title,
            slug = :slug,
            category = :category,
            property_type = :property_type,
            purpose = :purpose,
            price = :price,
            price_display = :price_display,
            city = :city,
            location = :location,
            sub_location = :sub_location,
            address = :address,
            configuration = :configuration,
            carpet_area = :carpet_area,
            super_area = :super_area,
            bedrooms = :bedrooms,
            bathrooms = :bathrooms,
            balconies = :balconies,
            possession_status = :possession_status,
            rera_number = :rera_number,
            rera_locked = :rera_locked,
            featured = :featured,
            status = :status,
            rejection_reason = :rejection_reason,
            featured_image = :featured_image,
            gallery_images = :gallery_images,
            video_urls = :video_urls,
            floor_plan_image = :floor_plan_image,
            description = :description,
            amenities = :amenities,
            nearby_landmarks = :nearby_landmarks,
            contact_person = :contact_person,
            contact_phone = :contact_phone,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    ''', prop_dict)
    conn.commit()
    conn.close()

def approve_property(property_id):
    """Admin activates/approves a property listing. Status becomes 'Active' and rera_number is locked."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE properties 
        SET status = 'Active', rera_locked = 1, rejection_reason = NULL, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (property_id,))
    conn.commit()
    conn.close()

def reject_property(property_id, reason="Listing details do not meet publication standards."):
    """Admin rejects a property listing. Remains unpublished."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE properties 
        SET status = 'Rejected', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (reason, property_id))
    conn.commit()
    conn.close()

def get_pending_properties():
    """Admin query for properties awaiting review."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name as owner_name, u.role as owner_role, 
               u.agency_name as owner_agency, u.rera_number as owner_rera, u.phone as owner_phone, u.email as owner_email
        FROM properties p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.status = 'Under Review'
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_pending_properties_count():
    """Count of properties awaiting review."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM properties WHERE status = 'Under Review'")
    row = cursor.fetchone()
    conn.close()
    return row['count'] if row else 0

def delete_property(property_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM properties WHERE id = ? AND user_id = ?", (property_id, user_id))
    else:
        cursor.execute("DELETE FROM properties WHERE id = ?", (property_id,))
    conn.commit()
    conn.close()

def update_property_status(property_id, new_status, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("UPDATE properties SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?", (new_status, property_id, user_id))
    else:
        cursor.execute("UPDATE properties SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, property_id))
    conn.commit()
    conn.close()

# Enquiry Queries
def insert_enquiry(enquiry_dict):
    conn = get_db()
    cursor = conn.cursor()

    # Determine property_owner_id
    property_owner_id = 1
    if enquiry_dict.get('property_id'):
        cursor.execute("SELECT user_id FROM properties WHERE id = ?", (enquiry_dict['property_id'],))
        row = cursor.fetchone()
        if row and row['user_id']:
            property_owner_id = row['user_id']
    
    enquiry_dict['property_owner_id'] = property_owner_id
    if not enquiry_dict.get('lead_source'):
        enquiry_dict['lead_source'] = 'Website Direct'
    if not enquiry_dict.get('website_enquiry_url'):
        enquiry_dict['website_enquiry_url'] = ''
    if not enquiry_dict.get('status'):
        enquiry_dict['status'] = 'New'
    if 'admin_notes' not in enquiry_dict or enquiry_dict['admin_notes'] is None:
        enquiry_dict['admin_notes'] = ''

    cursor.execute('''
        INSERT INTO enquiries (
            name, phone, email, property_id, property_owner_id, property_title, enquiry_type,
            lead_source, website_enquiry_url, budget, preferred_location, preferred_date, message, status, admin_notes
        ) VALUES (
            :name, :phone, :email, :property_id, :property_owner_id, :property_title, :enquiry_type,
            :lead_source, :website_enquiry_url, :budget, :preferred_location, :preferred_date, :message, :status, :admin_notes
        )
    ''', enquiry_dict)
    conn.commit()
    enquiry_id = cursor.lastrowid
    conn.close()

    # Automatically synchronize new enquiry into Feedback module immediately
    try:
        sync_single_enquiry_to_feedback(enquiry_id)
    except Exception as e:
        print(f"Notice: Auto-syncing enquiry #{enquiry_id} to feedback: {e}")

    return enquiry_id

def get_all_enquiries(status=None, source=None, limit=None, sort='newest', page=None, per_page=None, search=None):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT e.*, p.title as prop_title, p.location as prop_loc, u.full_name as assigned_owner
        FROM enquiries e
        LEFT JOIN properties p ON e.property_id = p.id
        LEFT JOIN users u ON e.property_owner_id = u.id
        WHERE 1=1
    """
    params = []
    if status and status != 'All':
        query += " AND e.status = ?"
        params.append(status)
    if source and source != 'All':
        query += " AND e.lead_source = ?"
        params.append(source)
    if search:
        search_kw = f"%{search.strip()}%"
        query += " AND (e.name LIKE ? OR e.phone LIKE ? OR e.email LIKE ? OR e.property_title LIKE ? OR e.preferred_location LIKE ? OR e.message LIKE ?)"
        params.extend([search_kw, search_kw, search_kw, search_kw, search_kw, search_kw])

    if sort in ['oldest', 'asc']:
        query += " ORDER BY CASE WHEN e.created_at IS NULL OR e.created_at = '' THEN 1 ELSE 0 END, e.created_at ASC, e.id ASC"
    else:
        query += " ORDER BY CASE WHEN e.created_at IS NULL OR e.created_at = '' THEN 1 ELSE 0 END, e.created_at DESC, e.id DESC"

    if page is not None and per_page is not None:
        offset = max(0, (int(page) - 1) * int(per_page))
        query += f" LIMIT {int(per_page)} OFFSET {offset}"
    elif limit:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_enquiries_count(status=None, source=None, search=None):
    """Get total count of enquiries matching filters."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as cnt FROM enquiries e WHERE 1=1"
    params = []
    if status and status != 'All':
        query += " AND e.status = ?"
        params.append(status)
    if source and source != 'All':
        query += " AND e.lead_source = ?"
        params.append(source)
    if search:
        search_kw = f"%{search.strip()}%"
        query += " AND (e.name LIKE ? OR e.phone LIKE ? OR e.email LIKE ? OR e.property_title LIKE ? OR e.preferred_location LIKE ? OR e.message LIKE ?)"
        params.extend([search_kw, search_kw, search_kw, search_kw, search_kw, search_kw])
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_enquiries_by_owner(owner_id, status=None, source=None, limit=None, sort='newest', page=None, per_page=None, search=None):
    """Retrieve enquiries for properties owned/managed by this specific agent/owner."""
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT e.*, p.title as prop_title, p.location as prop_loc
        FROM enquiries e
        LEFT JOIN properties p ON e.property_id = p.id
        WHERE e.property_owner_id = ?
    """
    params = [owner_id]
    if status and status != 'All':
        query += " AND e.status = ?"
        params.append(status)
    if source and source != 'All':
        query += " AND e.lead_source = ?"
        params.append(source)
    if search:
        search_kw = f"%{search.strip()}%"
        query += " AND (e.name LIKE ? OR e.phone LIKE ? OR e.email LIKE ? OR e.property_title LIKE ? OR e.preferred_location LIKE ? OR e.message LIKE ?)"
        params.extend([search_kw, search_kw, search_kw, search_kw, search_kw, search_kw])

    if sort in ['oldest', 'asc']:
        query += " ORDER BY CASE WHEN e.created_at IS NULL OR e.created_at = '' THEN 1 ELSE 0 END, e.created_at ASC, e.id ASC"
    else:
        query += " ORDER BY CASE WHEN e.created_at IS NULL OR e.created_at = '' THEN 1 ELSE 0 END, e.created_at DESC, e.id DESC"

    if page is not None and per_page is not None:
        offset = max(0, (int(page) - 1) * int(per_page))
        query += f" LIMIT {int(per_page)} OFFSET {offset}"
    elif limit:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_enquiries_by_owner_count(owner_id, status=None, source=None, search=None):
    """Get total count of enquiries for properties owned/managed by this user."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as cnt FROM enquiries e WHERE e.property_owner_id = ?"
    params = [owner_id]
    if status and status != 'All':
        query += " AND e.status = ?"
        params.append(status)
    if source and source != 'All':
        query += " AND e.lead_source = ?"
        params.append(source)
    if search:
        search_kw = f"%{search.strip()}%"
        query += " AND (e.name LIKE ? OR e.phone LIKE ? OR e.email LIKE ? OR e.property_title LIKE ? OR e.preferred_location LIKE ? OR e.message LIKE ?)"
        params.extend([search_kw, search_kw, search_kw, search_kw, search_kw, search_kw])
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_enquiry_by_id(enquiry_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM enquiries WHERE id = ?", (enquiry_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_enquiry_status(enquiry_id, status, notes=None, owner_id=None, lead_source=None):
    conn = get_db()
    cursor = conn.cursor()
    set_clauses = ["status = ?"]
    params = [status]
    if notes is not None:
        set_clauses.append("admin_notes = ?")
        params.append(notes)
    if lead_source is not None and lead_source.strip():
        set_clauses.append("lead_source = ?")
        params.append(lead_source.strip())
        
    where_clause = "WHERE id = ?"
    params.append(enquiry_id)
    if owner_id:
        where_clause += " AND property_owner_id = ?"
        params.append(owner_id)

    sql = f"UPDATE enquiries SET {', '.join(set_clauses)} {where_clause}"
    cursor.execute(sql, params)

    # Synchronize updated lead source to enquiry_feedback
    if lead_source is not None and lead_source.strip():
        cursor.execute("UPDATE enquiry_feedback SET enquiry_source = ? WHERE enquiry_id = ?", (lead_source.strip(), enquiry_id))

    conn.commit()
    conn.close()

def delete_enquiry(enquiry_id, owner_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if owner_id:
        cursor.execute("DELETE FROM enquiries WHERE id = ? AND property_owner_id = ?", (enquiry_id, owner_id))
    else:
        cursor.execute("DELETE FROM enquiries WHERE id = ?", (enquiry_id,))
    conn.commit()
    conn.close()

def bulk_delete_enquiries(enquiry_ids, owner_id=None, username='admin', role='admin'):
    """Permanently delete multiple enquiry lead records in one bulk operation."""
    if not enquiry_ids:
        return {'success': True, 'count': 0, 'deleted_ids': [], 'failed_ids': [], 'message': 'No records selected.'}

    valid_ids = []
    for item in enquiry_ids:
        try:
            valid_ids.append(int(item))
        except (ValueError, TypeError):
            continue

    if not valid_ids:
        return {'success': False, 'count': 0, 'deleted_ids': [], 'failed_ids': enquiry_ids, 'message': 'No valid enquiry IDs provided.'}

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ','.join(['?'] * len(valid_ids))
    if owner_id:
        cursor.execute(f"SELECT id FROM enquiries WHERE id IN ({placeholders}) AND property_owner_id = ?", valid_ids + [owner_id])
    else:
        cursor.execute(f"SELECT id FROM enquiries WHERE id IN ({placeholders})", valid_ids)

    rows = cursor.fetchall()
    target_ids = [r['id'] for r in rows]

    if not target_ids:
        conn.close()
        return {'success': False, 'count': 0, 'deleted_ids': [], 'failed_ids': valid_ids, 'message': 'No matching enquiries found or unauthorized.'}

    t_placeholders = ','.join(['?'] * len(target_ids))

    # Unlink any feedback referencing these enquiries to prevent foreign key or data corruption
    cursor.execute(f"UPDATE enquiry_feedback SET enquiry_id = NULL WHERE enquiry_id IN ({t_placeholders})", target_ids)

    if owner_id:
        cursor.execute(f"DELETE FROM enquiries WHERE id IN ({t_placeholders}) AND property_owner_id = ?", target_ids + [owner_id])
    else:
        cursor.execute(f"DELETE FROM enquiries WHERE id IN ({t_placeholders})", target_ids)

    conn.commit()
    conn.close()

    deleted_count = len(target_ids)
    failed_ids = [i for i in valid_ids if i not in target_ids]

    log_user_activity(
        username=username,
        role=role,
        activity_type='Bulk Enquiries Deleted',
        details=f"Permanently bulk deleted {deleted_count} enquiry lead record(s) (IDs: {target_ids})"
    )

    return {
        'success': True,
        'count': deleted_count,
        'deleted_ids': target_ids,
        'failed_ids': failed_ids,
        'message': f"Successfully permanently deleted {deleted_count} enquiry record(s)."
    }

# User / Authentication Queries
def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# -----------------------------------------------------------------------------
# USER LIMITS CONFIGURATION & USAGE TRACKING
# -----------------------------------------------------------------------------

def get_default_user_limits():
    """Retrieve system default limits for users from system_settings."""
    return {
        'listings_limit': int(get_setting('default_listings_limit', 10)),
        'monthly_enquiries_limit': int(get_setting('default_monthly_enquiries_limit', 100)),
        'photos_limit': int(get_setting('default_photos_limit', 10)),
        'videos_limit': int(get_setting('default_videos_limit', 2))
    }

def update_default_user_limits(listings_limit, monthly_enquiries_limit, photos_limit, videos_limit, username='admin'):
    """Save / update default user limits in system_settings."""
    set_setting('default_listings_limit', str(int(listings_limit)))
    set_setting('default_monthly_enquiries_limit', str(int(monthly_enquiries_limit)))
    set_setting('default_photos_limit', str(int(photos_limit)))
    set_setting('default_videos_limit', str(int(videos_limit)))
    log_user_activity(
        username=username,
        role='admin',
        activity_type='Update Default User Limits',
        details=f"Listings: {listings_limit}, Monthly Enquiries: {monthly_enquiries_limit}, Photos: {photos_limit}, Videos: {videos_limit}"
    )
    return get_default_user_limits()

def reset_default_user_limits(username='admin'):
    """Reset default user limits to standard values (10 listings, 100 monthly enquiries, 10 photos, 2 videos)."""
    return update_default_user_limits(10, 100, 10, 2, username=username)

def get_effective_user_limits(user_id):
    """
    Get effective limits for a user.
    Admin gets unlimited (-1).
    Individual custom limits override defaults.
    Users with has_custom_limits=0 inherit system default limits.
    """
    user = get_user_by_id(user_id)
    if not user:
        return get_default_user_limits()

    if user.get('role') == 'admin' or user.get('id') == 1:
        return {
            'listings_limit': -1,
            'monthly_enquiries_limit': -1,
            'photos_limit': 50,
            'videos_limit': 10,
            'is_admin': True,
            'has_custom_limits': True
        }

    def_limits = get_default_user_limits()
    has_custom = bool(user.get('has_custom_limits'))
    if has_custom:
        l_lim = user.get('listing_limit')
        m_lim = user.get('monthly_enquiries_limit')
        p_lim = user.get('photos_limit') if user.get('photos_limit') is not None else user.get('upload_limit')
        v_lim = user.get('videos_limit')
        return {
            'listings_limit': int(l_lim) if l_lim is not None else def_limits['listings_limit'],
            'monthly_enquiries_limit': int(m_lim) if m_lim is not None else def_limits['monthly_enquiries_limit'],
            'photos_limit': int(p_lim) if p_lim is not None else def_limits['photos_limit'],
            'videos_limit': int(v_lim) if v_lim is not None else def_limits['videos_limit'],
            'is_admin': False,
            'has_custom_limits': True
        }
    else:
        return {
            'listings_limit': def_limits['listings_limit'],
            'monthly_enquiries_limit': def_limits['monthly_enquiries_limit'],
            'photos_limit': def_limits['photos_limit'],
            'videos_limit': def_limits['videos_limit'],
            'is_admin': False,
            'has_custom_limits': False
        }

def check_and_reset_user_monthly_enquiries(user_id):
    """
    Automatically reset the monthly enquiries usage counter at the beginning of each new calendar month.
    """
    current_month = datetime.now().strftime('%Y-%m')
    user = get_user_by_id(user_id)
    if not user:
        return
    reset_date = user.get('monthly_enquiries_reset_date') or ''
    if reset_date != current_month:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET 
                monthly_enquiries_used = 0,
                monthly_enquiries_reset_date = ?
            WHERE id = ?
        """, (current_month, user_id))
        conn.commit()
        conn.close()

def record_user_enquiry_access(user_id, count=1):
    """Increment monthly enquiries counter for a user after resetting if new month."""
    check_and_reset_user_monthly_enquiries(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
            monthly_enquiries_used = COALESCE(monthly_enquiries_used, 0) + ?
        WHERE id = ?
    """, (count, user_id))
    conn.commit()
    conn.close()

def get_user_resource_usage(user_id):
    """
    Computes current usage against assigned limits for dashboard integration.
    """
    check_and_reset_user_monthly_enquiries(user_id)
    user = get_user_by_id(user_id)
    if not user:
        return {}

    eff = get_effective_user_limits(user_id)
    conn = get_db()
    cursor = conn.cursor()

    # 1. Listings used (Active / Available)
    cursor.execute("SELECT COUNT(*) as cnt FROM properties WHERE user_id = ? AND status IN ('Active', 'Available')", (user_id,))
    active_listings = cursor.fetchone()['cnt']

    # Total properties
    cursor.execute("SELECT COUNT(*) as cnt FROM properties WHERE user_id = ?", (user_id,))
    total_listings = cursor.fetchone()['cnt']

    # 2. Monthly Enquiries used (Current calendar month)
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM enquiries 
        WHERE property_owner_id = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """, (user_id,))
    month_enqs = cursor.fetchone()['cnt']
    stored_used = int(user.get('monthly_enquiries_used') or 0)
    monthly_enqs_used = max(stored_used, month_enqs)

    # 3. Photos per listing (Max gallery images in any listing owned by this user)
    cursor.execute("SELECT gallery_images FROM properties WHERE user_id = ?", (user_id,))
    props = cursor.fetchall()

    max_photos_used = 0
    for p in props:
        try:
            g_imgs = json.loads(p['gallery_images']) if p['gallery_images'] else []
            if isinstance(g_imgs, list) and len(g_imgs) > max_photos_used:
                max_photos_used = len(g_imgs)
        except Exception:
            pass

    # 4. Videos per listing
    cursor.execute("SELECT video_urls FROM properties WHERE user_id = ?", (user_id,))
    v_props = cursor.fetchall()
    conn.close()

    max_videos_used = 0
    for p in v_props:
        try:
            v_urls = json.loads(p['video_urls']) if p['video_urls'] else []
            if isinstance(v_urls, list) and len(v_urls) > max_videos_used:
                max_videos_used = len(v_urls)
        except Exception:
            pass

    is_listings_reached = (eff['listings_limit'] != -1 and active_listings >= eff['listings_limit'])
    is_monthly_enqs_reached = (eff['monthly_enquiries_limit'] != -1 and monthly_enqs_used >= eff['monthly_enquiries_limit'])

    return {
        'listings': {
            'feature': 'Property Listings',
            'allowed': 'Unlimited' if eff['listings_limit'] == -1 else eff['listings_limit'],
            'allowed_raw': eff['listings_limit'],
            'used': active_listings,
            'total_used': total_listings,
            'is_reached': is_listings_reached
        },
        'monthly_enquiries': {
            'feature': 'Monthly Enquiries',
            'allowed': 'Unlimited' if eff['monthly_enquiries_limit'] == -1 else eff['monthly_enquiries_limit'],
            'allowed_raw': eff['monthly_enquiries_limit'],
            'used': monthly_enqs_used,
            'is_reached': is_monthly_enqs_reached
        },
        'photos': {
            'feature': 'Photos Per Listing',
            'allowed': 'Unlimited' if eff['photos_limit'] == -1 else eff['photos_limit'],
            'allowed_raw': eff['photos_limit'],
            'used': max_photos_used,
            'is_reached': False
        },
        'videos': {
            'feature': 'Videos Per Listing',
            'allowed': 'Unlimited' if eff['videos_limit'] == -1 else eff['videos_limit'],
            'allowed_raw': eff['videos_limit'],
            'used': max_videos_used,
            'is_reached': False
        },
        'has_any_limit_reached': (is_listings_reached or is_monthly_enqs_reached)
    }

# -----------------------------------------------------------------------------
# RECORDS PER PAGE PREFERENCES
# -----------------------------------------------------------------------------

def get_records_per_page_preference(user_id=None, section='leads'):
    """
    Retrieve stored records-per-page preference.
    Allowed options: 10, 50, 100, 1000. Default: 10.
    """
    valid_options = (10, 50, 100, 1000)
    if user_id and int(user_id) != 1:
        user = get_user_by_id(user_id)
        if user:
            col = 'leads_per_page' if section == 'leads' else 'feedback_per_page'
            val = user.get(col)
            try:
                if int(val) in valid_options:
                    return int(val)
            except (ValueError, TypeError):
                pass
    else:
        key = 'admin_leads_per_page' if section == 'leads' else 'admin_feedback_per_page'
        val = get_setting(key, '10')
        try:
            if int(val) in valid_options:
                return int(val)
        except (ValueError, TypeError):
            pass
    return 10

def set_records_per_page_preference(user_id=None, section='leads', per_page=10):
    """
    Persist user or admin preference for records-per-page.
    """
    valid_options = (10, 50, 100, 1000)
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 10
    if per_page not in valid_options:
        per_page = 10

    if user_id and int(user_id) != 1:
        col = 'leads_per_page' if section == 'leads' else 'feedback_per_page'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {col} = ? WHERE id = ?", (per_page, user_id))
        conn.commit()
        conn.close()
    else:
        key = 'admin_leads_per_page' if section == 'leads' else 'admin_feedback_per_page'
        set_setting(key, str(per_page))
    return per_page

def create_user(user_dict):
    conn = get_db()
    cursor = conn.cursor()
    def_limits = get_default_user_limits()
    user_dict.setdefault('phone', '')
    user_dict.setdefault('agency_name', '')
    user_dict.setdefault('rera_number', '')
    user_dict.setdefault('status', 'active')
    user_dict.setdefault('listing_limit', def_limits['listings_limit'])
    user_dict.setdefault('upload_limit', def_limits['photos_limit'])
    user_dict.setdefault('photos_limit', def_limits['photos_limit'])
    user_dict.setdefault('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])
    user_dict.setdefault('videos_limit', def_limits['videos_limit'])
    user_dict.setdefault('has_custom_limits', 0)
    user_dict.setdefault('monthly_enquiries_used', 0)
    user_dict.setdefault('monthly_enquiries_reset_date', datetime.now().strftime('%Y-%m'))
    user_dict.setdefault('leads_per_page', 10)
    user_dict.setdefault('feedback_per_page', 10)
    cursor.execute("""
        INSERT INTO users (
            username, password_hash, email, full_name, role, phone, agency_name, rera_number, status,
            listing_limit, upload_limit, photos_limit, monthly_enquiries_limit, videos_limit,
            has_custom_limits, monthly_enquiries_used, monthly_enquiries_reset_date,
            leads_per_page, feedback_per_page
        )
        VALUES (
            :username, :password_hash, :email, :full_name, :role, :phone, :agency_name, :rera_number, :status,
            :listing_limit, :upload_limit, :photos_limit, :monthly_enquiries_limit, :videos_limit,
            :has_custom_limits, :monthly_enquiries_used, :monthly_enquiries_reset_date,
            :leads_per_page, :feedback_per_page
        )
    """, user_dict)
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def update_user_profile(user_id, profile_dict):
    conn = get_db()
    cursor = conn.cursor()
    profile_dict['id'] = user_id
    cursor.execute("""
        UPDATE users SET
            full_name = :full_name,
            phone = :phone,
            agency_name = :agency_name,
            rera_number = :rera_number,
            email = :email
        WHERE id = :id
    """, profile_dict)
    conn.commit()
    conn.close()

def update_admin_profile(user_id, profile_dict):
    """Update administrator profile information including name, phone, email, agency, rera, notes, and optionally password."""
    conn = get_db()
    cursor = conn.cursor()
    profile_dict['id'] = user_id
    profile_dict.setdefault('agency_name', '')
    profile_dict.setdefault('rera_number', '')
    profile_dict.setdefault('notes', '')
    if profile_dict.get('password_hash'):
        cursor.execute("""
            UPDATE users SET
                full_name = :full_name,
                email = :email,
                phone = :phone,
                agency_name = :agency_name,
                rera_number = :rera_number,
                notes = :notes,
                password_hash = :password_hash
            WHERE id = :id
        """, profile_dict)
    else:
        cursor.execute("""
            UPDATE users SET
                full_name = :full_name,
                email = :email,
                phone = :phone,
                agency_name = :agency_name,
                rera_number = :rera_number,
                notes = :notes
            WHERE id = :id
        """, profile_dict)
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# Centralized User Management Queries for Admin
def get_all_users_with_stats(role=None, status=None, q=None):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT u.*,
               COUNT(DISTINCT p.id) as properties_count,
               SUM(CASE WHEN p.status = 'Available' THEN 1 ELSE 0 END) as active_properties_count,
               COUNT(DISTINCT e.id) as enquiries_count
        FROM users u
        LEFT JOIN properties p ON p.user_id = u.id
        LEFT JOIN enquiries e ON e.property_owner_id = u.id
        WHERE 1=1
    """
    params = []
    if role and role != 'All':
        query += " AND u.role = ?"
        params.append(role)
    if status and status != 'All':
        query += " AND u.status = ?"
        params.append(status)
    if q:
        query += " AND (u.full_name LIKE ? OR u.username LIKE ? OR u.email LIKE ? OR u.phone LIKE ? OR u.agency_name LIKE ? OR u.rera_number LIKE ?)"
        keyword = f"%{q}%"
        params.extend([keyword, keyword, keyword, keyword, keyword, keyword])

    query += " GROUP BY u.id ORDER BY u.created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    def_limits = get_default_user_limits()
    result = []
    for r in rows:
        u = dict(r)
        if u.get('has_custom_limits'):
            u['effective_listing_limit'] = u.get('listing_limit', def_limits['listings_limit'])
            u['effective_monthly_enquiries_limit'] = u.get('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])
            u['effective_photos_limit'] = u.get('photos_limit') or u.get('upload_limit', def_limits['photos_limit'])
            u['effective_videos_limit'] = u.get('videos_limit', def_limits['videos_limit'])
        else:
            u['effective_listing_limit'] = def_limits['listings_limit']
            u['effective_monthly_enquiries_limit'] = def_limits['monthly_enquiries_limit']
            u['effective_photos_limit'] = def_limits['photos_limit']
            u['effective_videos_limit'] = def_limits['videos_limit']
        result.append(u)
    return result

def get_user_by_id_with_stats(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*,
               COUNT(DISTINCT p.id) as properties_count,
               SUM(CASE WHEN p.status = 'Available' THEN 1 ELSE 0 END) as active_properties_count,
               COUNT(DISTINCT e.id) as enquiries_count
        FROM users u
        LEFT JOIN properties p ON p.user_id = u.id
        LEFT JOIN enquiries e ON e.property_owner_id = u.id
        WHERE u.id = ?
        GROUP BY u.id
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user_by_admin(user_dict):
    conn = get_db()
    cursor = conn.cursor()
    def_limits = get_default_user_limits()
    user_dict.setdefault('can_manage_feedback', 1)
    user_dict.setdefault('phone', '')
    user_dict.setdefault('agency_name', '')
    user_dict.setdefault('rera_number', '')
    user_dict.setdefault('status', 'active')
    
    is_custom = user_dict.get('has_custom_limits') or (
        user_dict.get('listing_limit') is not None and user_dict.get('listing_limit') != def_limits['listings_limit']
    ) or (
        user_dict.get('upload_limit') is not None and user_dict.get('upload_limit') != def_limits['photos_limit']
    )
    if not is_custom:
        user_dict['has_custom_limits'] = 0
        user_dict.setdefault('listing_limit', def_limits['listings_limit'])
        user_dict.setdefault('upload_limit', def_limits['photos_limit'])
        user_dict.setdefault('photos_limit', def_limits['photos_limit'])
        user_dict.setdefault('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])
        user_dict.setdefault('videos_limit', def_limits['videos_limit'])
    else:
        user_dict['has_custom_limits'] = 1
        user_dict.setdefault('listing_limit', def_limits['listings_limit'])
        user_dict.setdefault('photos_limit', user_dict.get('upload_limit', def_limits['photos_limit']))
        user_dict.setdefault('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])
        user_dict.setdefault('videos_limit', def_limits['videos_limit'])
        user_dict['upload_limit'] = user_dict['photos_limit']

    user_dict.setdefault('monthly_enquiries_used', 0)
    user_dict.setdefault('monthly_enquiries_reset_date', datetime.now().strftime('%Y-%m'))
    user_dict.setdefault('leads_per_page', 10)
    user_dict.setdefault('feedback_per_page', 10)

    cursor.execute("""
        INSERT INTO users (
            username, password_hash, email, full_name, role, phone, 
            agency_name, rera_number, status, listing_limit, upload_limit, photos_limit,
            monthly_enquiries_limit, videos_limit, has_custom_limits,
            monthly_enquiries_used, monthly_enquiries_reset_date,
            leads_per_page, feedback_per_page,
            can_post_ads, can_edit_ads, can_delete_ads, can_access_crm, 
            can_export_leads, can_feature_properties, can_manage_feedback, notes
        ) VALUES (
            :username, :password_hash, :email, :full_name, :role, :phone, 
            :agency_name, :rera_number, :status, :listing_limit, :upload_limit, :photos_limit,
            :monthly_enquiries_limit, :videos_limit, :has_custom_limits,
            :monthly_enquiries_used, :monthly_enquiries_reset_date,
            :leads_per_page, :feedback_per_page,
            :can_post_ads, :can_edit_ads, :can_delete_ads, :can_access_crm, 
            :can_export_leads, :can_feature_properties, :can_manage_feedback, :notes
        )
    """, user_dict)
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def update_user_by_admin(user_id, user_dict):
    conn = get_db()
    cursor = conn.cursor()
    user_dict['id'] = user_id
    user_dict.setdefault('can_manage_feedback', 1)
    
    if 'photos_limit' in user_dict:
        user_dict['upload_limit'] = user_dict['photos_limit']
    elif 'upload_limit' in user_dict:
        user_dict['photos_limit'] = user_dict['upload_limit']
        
    def_limits = get_default_user_limits()
    user_dict.setdefault('monthly_enquiries_limit', def_limits['monthly_enquiries_limit'])
    user_dict.setdefault('videos_limit', def_limits['videos_limit'])
    user_dict.setdefault('has_custom_limits', 1)
    
    if user_dict.get('password_hash'):
        cursor.execute("""
            UPDATE users SET
                full_name = :full_name,
                email = :email,
                phone = :phone,
                role = :role,
                agency_name = :agency_name,
                rera_number = :rera_number,
                status = :status,
                listing_limit = :listing_limit,
                upload_limit = :upload_limit,
                photos_limit = :photos_limit,
                monthly_enquiries_limit = :monthly_enquiries_limit,
                videos_limit = :videos_limit,
                has_custom_limits = :has_custom_limits,
                can_post_ads = :can_post_ads,
                can_edit_ads = :can_edit_ads,
                can_delete_ads = :can_delete_ads,
                can_access_crm = :can_access_crm,
                can_export_leads = :can_export_leads,
                can_feature_properties = :can_feature_properties,
                can_manage_feedback = :can_manage_feedback,
                notes = :notes,
                password_hash = :password_hash
            WHERE id = :id
        """, user_dict)
    else:
        cursor.execute("""
            UPDATE users SET
                full_name = :full_name,
                email = :email,
                phone = :phone,
                role = :role,
                agency_name = :agency_name,
                rera_number = :rera_number,
                status = :status,
                listing_limit = :listing_limit,
                upload_limit = :upload_limit,
                photos_limit = :photos_limit,
                monthly_enquiries_limit = :monthly_enquiries_limit,
                videos_limit = :videos_limit,
                has_custom_limits = :has_custom_limits,
                can_post_ads = :can_post_ads,
                can_edit_ads = :can_edit_ads,
                can_delete_ads = :can_delete_ads,
                can_access_crm = :can_access_crm,
                can_export_leads = :can_export_leads,
                can_feature_properties = :can_feature_properties,
                can_manage_feedback = :can_manage_feedback,
                notes = :notes
            WHERE id = :id
        """, user_dict)
    conn.commit()
    conn.close()

def toggle_user_status(user_id, status):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()

def delete_user_by_admin(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE properties SET user_id = 1 WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE enquiries SET property_owner_id = 1 WHERE property_owner_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_user_last_login(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_user_theme(user_id, theme):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET theme_preference = ? WHERE id = ?", (theme, user_id))
    conn.commit()
    conn.close()

def get_admin_user_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role != 'admin'")
    total_managed = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'agent'")
    total_agents = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'owner'")
    total_owners = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE status = 'active' AND role != 'admin'")
    active_users = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE status = 'inactive' AND role != 'admin'")
    inactive_users = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM properties WHERE user_id != 1")
    user_properties = cursor.fetchone()['total']
    conn.close()
    return {
        'total_managed': total_managed,
        'total_agents': total_agents,
        'total_owners': total_owners,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'user_properties': user_properties
    }

def get_user_active_properties_count(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM properties WHERE user_id = ? AND status != 'Deleted'", (user_id,))
    cnt = cursor.fetchone()['count']
    conn.close()
    return cnt

# Dashboard Analytics Queries
def get_dashboard_stats():
    """System-wide stats for Super Admin."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM properties")
    total_properties = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as available FROM properties WHERE status IN ('Active', 'Available')")
    active_properties = cursor.fetchone()['available']

    cursor.execute("SELECT COUNT(*) as pending FROM properties WHERE status = 'Under Review'")
    pending_properties = cursor.fetchone()['pending']

    cursor.execute("SELECT COUNT(*) as rejected FROM properties WHERE status = 'Rejected'")
    rejected_properties = cursor.fetchone()['rejected']
    
    cursor.execute("SELECT COUNT(*) as sold_rented FROM properties WHERE status IN ('Sold', 'Rented')")
    sold_rented = cursor.fetchone()['sold_rented']
    
    cursor.execute("SELECT COUNT(*) as total FROM enquiries")
    total_enquiries = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as new_leads FROM enquiries WHERE status = 'New'")
    new_enquiries = cursor.fetchone()['new_leads']

    cursor.execute("SELECT COUNT(*) as site_visits FROM enquiries WHERE status = 'Site Visit Scheduled' OR enquiry_type = 'Schedule Site Visit'")
    site_visits = cursor.fetchone()['site_visits']
    
    cursor.execute("SELECT COUNT(*) as total_agents FROM users WHERE role = 'agent'")
    total_agents = cursor.fetchone()['total_agents']

    cursor.execute("SELECT COUNT(*) as total_owners FROM users WHERE role = 'owner'")
    total_owners = cursor.fetchone()['total_owners']

    conn.close()
    return {
        'total_properties': total_properties,
        'active_properties': active_properties,
        'pending_properties': pending_properties,
        'rejected_properties': rejected_properties,
        'sold_rented': sold_rented,
        'total_enquiries': total_enquiries,
        'new_enquiries': new_enquiries,
        'site_visits': site_visits,
        'total_agents': total_agents,
        'total_owners': total_owners
    }

def get_user_dashboard_stats(user_id):
    """Personalized stats for a specific Agent or Property Owner."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM properties WHERE user_id = ?", (user_id,))
    total_properties = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as available FROM properties WHERE user_id = ? AND status IN ('Active', 'Available')", (user_id,))
    active_properties = cursor.fetchone()['available']

    cursor.execute("SELECT COUNT(*) as pending FROM properties WHERE user_id = ? AND status = 'Under Review'", (user_id,))
    pending_properties = cursor.fetchone()['pending']

    cursor.execute("SELECT COUNT(*) as rejected FROM properties WHERE user_id = ? AND status = 'Rejected'", (user_id,))
    rejected_properties = cursor.fetchone()['rejected']

    cursor.execute("SELECT COUNT(*) as sold_rented FROM properties WHERE user_id = ? AND status IN ('Sold', 'Rented')", (user_id,))
    sold_rented = cursor.fetchone()['sold_rented']

    cursor.execute("SELECT COUNT(*) as total FROM enquiries WHERE property_owner_id = ?", (user_id,))
    total_enquiries = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as new_leads FROM enquiries WHERE property_owner_id = ? AND status = 'New'", (user_id,))
    new_enquiries = cursor.fetchone()['new_leads']

    cursor.execute("""
        SELECT COUNT(*) as site_visits FROM enquiries 
        WHERE property_owner_id = ? AND (status = 'Site Visit Scheduled' OR enquiry_type = 'Schedule Site Visit')
    """, (user_id,))
    site_visits = cursor.fetchone()['site_visits']

    conn.close()
    return {
        'total_properties': total_properties,
        'active_properties': active_properties,
        'sold_rented': sold_rented,
        'total_enquiries': total_enquiries,
        'new_enquiries': new_enquiries,
        'site_visits': site_visits
    }

# -----------------------------------------------------------------------------
# CRM LEAD SOURCE MASTER CONFIGURATION & QUERIES
# -----------------------------------------------------------------------------

def get_all_lead_sources(active_only=False):
    """Retrieve lead sources from the centralized CRM Lead Source master table."""
    conn = get_db()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM lead_sources WHERE is_active = 1 ORDER BY display_order ASC, source_name ASC")
    else:
        cursor.execute("SELECT * FROM lead_sources ORDER BY display_order ASC, source_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_lead_sources():
    """Retrieve only currently active CRM lead sources for dropdowns."""
    return get_all_lead_sources(active_only=True)

def get_lead_source_by_id(source_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lead_sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_lead_source_by_name(name):
    if not name:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lead_sources WHERE LOWER(source_name) = LOWER(?)", (name.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_lead_source(source_name, description="", display_order=0, is_active=1):
    source_name = source_name.strip()
    if not source_name:
        return False, "Lead source name cannot be empty."
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO lead_sources (source_name, description, display_order, is_active, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (source_name, description.strip(), int(display_order), int(is_active)))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return True, new_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"A lead source named '{source_name}' already exists."

def update_lead_source(source_id, source_name, description="", display_order=0, is_active=1):
    source_name = source_name.strip()
    if not source_name:
        return False, "Lead source name cannot be empty."
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT source_name FROM lead_sources WHERE id = ?", (source_id,))
    old_row = cursor.fetchone()
    if not old_row:
        conn.close()
        return False, "Lead source record not found."
    
    old_name = old_row['source_name']
    try:
        cursor.execute("""
            UPDATE lead_sources
            SET source_name = ?, description = ?, display_order = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (source_name, description.strip(), int(display_order), int(is_active), source_id))
        
        # If renamed, synchronize across historical CRM enquiries and enquiry_feedback
        if old_name != source_name:
            cursor.execute("UPDATE enquiries SET lead_source = ? WHERE lead_source = ?", (source_name, old_name))
            cursor.execute("UPDATE enquiry_feedback SET enquiry_source = ? WHERE enquiry_source = ?", (source_name, old_name))

        conn.commit()
        conn.close()
        return True, "Lead source updated successfully."
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"A lead source named '{source_name}' already exists."

def delete_lead_source(source_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT source_name FROM lead_sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Lead source record not found."
    
    source_name = row['source_name']
    cursor.execute("DELETE FROM lead_sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()
    return True, f"Lead source '{source_name}' deleted."

# -----------------------------------------------------------------------------
# ENQUIRY FEEDBACK MODULE (INDEPENDENT FROM CRM LEADS)
# -----------------------------------------------------------------------------

def create_feedback(feedback_dict):
    """Create a new enquiry feedback record with all 13 required columns plus synchronized enquiry_source and enquiry_id."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO enquiry_feedback (
            enquiry_id, client_name, client_contact, enquiry_datetime, enquiry_source, project_name,
            configuration, cost, carpet, possession, website_enquiry_url,
            client_feedback, feedback_by_username, feedback_datetime
        ) VALUES (
            :enquiry_id, :client_name, :client_contact, :enquiry_datetime, :enquiry_source, :project_name,
            :configuration, :cost, :carpet, :possession, :website_enquiry_url,
            :client_feedback, :feedback_by_username, :feedback_datetime
        )
    """, {
        'enquiry_id': feedback_dict.get('enquiry_id'),
        'client_name': feedback_dict.get('client_name', '').strip(),
        'client_contact': feedback_dict.get('client_contact', '').strip(),
        'enquiry_datetime': feedback_dict.get('enquiry_datetime', '').strip() or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'enquiry_source': feedback_dict.get('enquiry_source', 'Website Direct').strip() or 'Website Direct',
        'project_name': feedback_dict.get('project_name', '').strip(),
        'configuration': feedback_dict.get('configuration', '').strip(),
        'cost': float(feedback_dict.get('cost', 0)) if feedback_dict.get('cost') else 0,
        'carpet': feedback_dict.get('carpet', '').strip(),
        'possession': feedback_dict.get('possession', '').strip(),
        'website_enquiry_url': feedback_dict.get('website_enquiry_url', '').strip(),
        'client_feedback': feedback_dict.get('client_feedback', '').strip(),
        'feedback_by_username': feedback_dict.get('feedback_by_username', '').strip(),
        'feedback_datetime': feedback_dict.get('feedback_datetime') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    conn.commit()
    feedback_id = cursor.lastrowid
    conn.close()

    # Log activity
    log_user_activity(
        username=feedback_dict.get('feedback_by_username', 'system'),
        role=feedback_dict.get('role', 'user'),
        activity_type='Feedback Added',
        details=f"Feedback #{feedback_id} recorded for client {feedback_dict.get('client_name')} on project {feedback_dict.get('project_name')} (Source: {feedback_dict.get('enquiry_source', 'Website Direct')})"
    )
    return feedback_id

def get_feedback_by_id(feedback_id):
    """Retrieve single feedback record by primary key."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM enquiry_feedback WHERE id = ?", (feedback_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_feedback(feedback_id, feedback_dict):
    """Update an existing enquiry feedback record safely without overwriting existing data with blank/null values."""
    existing = get_feedback_by_id(feedback_id)
    if not existing:
        return False

    def get_val(key, default=''):
        val = feedback_dict.get(key)
        if val is not None and str(val).strip() != '':
            return str(val).strip()
        # Retain existing database value to prevent unintended blank overwrites
        return existing.get(key) if existing.get(key) is not None else default

    cost_val = feedback_dict.get('cost')
    if cost_val is not None and str(cost_val).strip() != '':
        try:
            parsed_cost = float(cost_val)
        except (ValueError, TypeError):
            parsed_cost = existing.get('cost', 0)
    else:
        parsed_cost = existing.get('cost', 0)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE enquiry_feedback SET
            client_name = :client_name,
            client_contact = :client_contact,
            enquiry_datetime = :enquiry_datetime,
            enquiry_source = :enquiry_source,
            project_name = :project_name,
            configuration = :configuration,
            cost = :cost,
            carpet = :carpet,
            possession = :possession,
            website_enquiry_url = :website_enquiry_url,
            client_feedback = :client_feedback
        WHERE id = :id
    """, {
        'id': feedback_id,
        'client_name': get_val('client_name'),
        'client_contact': get_val('client_contact'),
        'enquiry_datetime': get_val('enquiry_datetime'),
        'enquiry_source': get_val('enquiry_source', 'Website Direct'),
        'project_name': get_val('project_name'),
        'configuration': get_val('configuration'),
        'cost': parsed_cost,
        'carpet': get_val('carpet'),
        'possession': get_val('possession'),
        'website_enquiry_url': get_val('website_enquiry_url'),
        'client_feedback': get_val('client_feedback')
    })
    conn.commit()
    conn.close()

    log_user_activity(
        username=feedback_dict.get('updated_by', 'system'),
        role=feedback_dict.get('role', 'user'),
        activity_type='Feedback Updated',
        details=f"Feedback #{feedback_id} updated for client {get_val('client_name')}"
    )
    return True

def delete_feedback(feedback_id, username='admin', role='admin'):
    """Delete an enquiry feedback record."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM enquiry_feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()

    log_user_activity(
        username=username,
        role=role,
        activity_type='Feedback Deleted',
        details=f"Feedback #{feedback_id} deleted"
    )
    return True

def bulk_delete_feedbacks(feedback_ids, username='admin', role='admin'):
    """Permanently delete multiple enquiry feedback records in one bulk operation."""
    if not feedback_ids:
        return {'success': True, 'count': 0, 'deleted_ids': [], 'failed_ids': [], 'message': 'No records selected.'}

    valid_ids = []
    for item in feedback_ids:
        try:
            valid_ids.append(int(item))
        except (ValueError, TypeError):
            continue

    if not valid_ids:
        return {'success': False, 'count': 0, 'deleted_ids': [], 'failed_ids': feedback_ids, 'message': 'No valid feedback IDs provided.'}

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ','.join(['?'] * len(valid_ids))
    cursor.execute(f"SELECT id FROM enquiry_feedback WHERE id IN ({placeholders})", valid_ids)
    rows = cursor.fetchall()
    target_ids = [r['id'] for r in rows]

    if not target_ids:
        conn.close()
        return {'success': False, 'count': 0, 'deleted_ids': [], 'failed_ids': valid_ids, 'message': 'No matching feedback records found.'}

    t_placeholders = ','.join(['?'] * len(target_ids))
    cursor.execute(f"DELETE FROM enquiry_feedback WHERE id IN ({t_placeholders})", target_ids)
    conn.commit()
    conn.close()

    deleted_count = len(target_ids)
    failed_ids = [i for i in valid_ids if i not in target_ids]

    log_user_activity(
        username=username,
        role=role,
        activity_type='Bulk Feedback Deleted',
        details=f"Permanently bulk deleted {deleted_count} feedback record(s) (IDs: {target_ids})"
    )

    return {
        'success': True,
        'count': deleted_count,
        'deleted_ids': target_ids,
        'failed_ids': failed_ids,
        'message': f"Successfully permanently deleted {deleted_count} feedback record(s)."
    }

def _build_feedback_filter_sql(filters):
    query = " WHERE 1=1"
    params = []
    if not filters:
        return query, params

    if filters.get('search'):
        term = f"%{filters['search'].strip()}%"
        query += """ AND (
            client_name LIKE ? OR 
            client_contact LIKE ? OR 
            project_name LIKE ? OR 
            enquiry_source LIKE ? OR
            feedback_by_username LIKE ? OR 
            enquiry_datetime LIKE ? OR
            client_feedback LIKE ?
        )"""
        params.extend([term, term, term, term, term, term, term])

    if filters.get('project_name'):
        query += " AND project_name = ?"
        params.append(filters['project_name'].strip())

    if filters.get('source'):
        query += " AND enquiry_source = ?"
        params.append(filters['source'].strip())

    if filters.get('feedback_by_username'):
        query += " AND feedback_by_username = ?"
        params.append(filters['feedback_by_username'].strip())

    if filters.get('date_from'):
        query += " AND enquiry_datetime >= ?"
        params.append(filters['date_from'].strip())

    if filters.get('date_to'):
        query += " AND enquiry_datetime <= ?"
        params.append(filters['date_to'].strip() + " 23:59:59")

    return query, params

def get_all_feedbacks(filters=None, page=1, per_page=10, sort='newest'):
    """Retrieve paginated feedback records matching filters, sorted by creation date & time."""
    conn = get_db()
    cursor = conn.cursor()
    where_clause, params = _build_feedback_filter_sql(filters)
    
    offset = max(0, (page - 1) * per_page)
    if sort in ['oldest', 'asc']:
        order_clause = "ORDER BY CASE WHEN feedback_datetime IS NULL OR feedback_datetime = '' THEN 1 ELSE 0 END, feedback_datetime ASC, id ASC"
    else:
        order_clause = "ORDER BY CASE WHEN feedback_datetime IS NULL OR feedback_datetime = '' THEN 1 ELSE 0 END, feedback_datetime DESC, id DESC"

    sql = f"SELECT * FROM enquiry_feedback {where_clause} {order_clause} LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_feedbacks_count(filters=None):
    """Get total count of feedback records matching filters."""
    conn = get_db()
    cursor = conn.cursor()
    where_clause, params = _build_feedback_filter_sql(filters)
    sql = f"SELECT COUNT(*) as cnt FROM enquiry_feedback {where_clause}"
    cursor.execute(sql, params)
    count = cursor.fetchone()['cnt']
    conn.close()
    return count

def get_all_feedbacks_for_export(filters=None):
    """Retrieve all feedback records matching filters for Excel download/email."""
    conn = get_db()
    cursor = conn.cursor()
    where_clause, params = _build_feedback_filter_sql(filters)
    sql = f"SELECT * FROM enquiry_feedback {where_clause} ORDER BY id ASC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_distinct_feedback_projects():
    """Get distinct project names across feedback and properties."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT project_name as name FROM enquiry_feedback WHERE project_name IS NOT NULL AND project_name != ''
        UNION
        SELECT DISTINCT title as name FROM properties WHERE title IS NOT NULL AND title != ''
        ORDER BY name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r['name'] for r in rows if r['name']]

def get_distinct_feedback_users():
    """Get distinct usernames who submitted feedback."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT feedback_by_username FROM enquiry_feedback WHERE feedback_by_username IS NOT NULL AND feedback_by_username != '' ORDER BY feedback_by_username ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r['feedback_by_username'] for r in rows if r['feedback_by_username']]

def parse_cost_from_budget(budget_str):
    """Parse numeric currency cost (INR) from customer budget text."""
    if not budget_str:
        return 0.0
    s = str(budget_str).strip().replace(',', '')
    # Match patterns like 2.5 Cr or 2.5Crore or ₹2.5 Cr
    cr_match = re.search(r'([\d\.]+)\s*(?:cr|crore)', s, re.IGNORECASE)
    if cr_match:
        try:
            return float(cr_match.group(1)) * 10000000.0
        except ValueError:
            pass
    # Match patterns like 85 L or 85 Lakh or 85 Lakhs
    lakh_match = re.search(r'([\d\.]+)\s*(?:l|lac|lakh|lakhs)', s, re.IGNORECASE)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass
    # Match direct digit string
    digits = re.search(r'(\d+)', s)
    if digits:
        try:
            return float(digits.group(1))
        except ValueError:
            pass
    return 0.0

def sync_single_enquiry_to_feedback(enquiry_id, username='Website Direct'):
    """
    Ensure an individual CRM Lead / Enquiry is immediately synchronized into enquiry_feedback.
    Requirements:
    1. Synchronizes all 11 required fields:
       - enquiry_id (Lead ID)
       - client_name
       - client_contact
       - enquiry_datetime
       - enquiry_source (synced with lead_source)
       - project_name
       - configuration
       - cost
       - carpet
       - possession
       - website_enquiry_url
    2. Maintains existing feedback comments and user metadata if record already exists.
    3. Prevents duplicate records.
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT e.*, 
               p.title as prop_title, 
               p.slug as prop_slug, 
               p.configuration as prop_config, 
               p.price as prop_price, 
               p.carpet_area as prop_carpet, 
               p.possession_status as prop_possession
        FROM enquiries e
        LEFT JOIN properties p ON (e.property_id = p.id OR (e.property_id IS NULL AND LOWER(TRIM(e.property_title)) = LOWER(TRIM(p.title))))
        WHERE e.id = ?
    """
    cursor.execute(query, (enquiry_id,))
    enq_row = cursor.fetchone()
    if not enq_row:
        conn.close()
        return None

    enq = dict(enq_row)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    client_name = (enq.get('name') or '').strip()
    client_contact = (enq.get('phone') or '').strip()
    enquiry_dt = str(enq.get('created_at') or now_str)[:19]
    enquiry_src = (enq.get('lead_source') or 'Website Direct').strip()
    enq_title = enq.get('prop_title') or enq.get('property_title') or 'General Website Enquiry'
    project_name = enq_title

    # Configuration
    config = enq.get('prop_config') or (enq.get('enquiry_type') if 'BHK' in str(enq.get('enquiry_type', '')) else '—')

    # Cost
    if enq.get('prop_price') and float(enq['prop_price']) > 0:
        cost_val = float(enq['prop_price'])
    else:
        cost_val = parse_cost_from_budget(enq.get('budget'))

    # Carpet Area
    if enq.get('prop_carpet'):
        carpet_val = f"{enq['prop_carpet']} sq ft"
    else:
        carpet_val = '—'

    # Possession
    possession_val = enq.get('prop_possession') or '—'

    # Website Enquiry URL
    url_val = (enq.get('website_enquiry_url') or '').strip()
    if not url_val or url_val in ('—', '-', 'None', 'N/A'):
        if enq.get('prop_slug'):
            url_val = f"/property/{enq['prop_slug']}"
        else:
            url_val = '—'

    # Check if already in enquiry_feedback by enquiry_id
    cursor.execute("SELECT id FROM enquiry_feedback WHERE enquiry_id = ?", (enquiry_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE enquiry_feedback SET
                client_name = ?,
                client_contact = ?,
                enquiry_source = ?,
                project_name = ?,
                configuration = ?,
                cost = ?,
                carpet = ?,
                possession = ?,
                website_enquiry_url = ?
            WHERE id = ?
        """, (
            client_name, client_contact, enquiry_src, project_name, config,
            cost_val, carpet_val, possession_val, url_val, existing['id']
        ))
        fb_id = existing['id']
    else:
        # Check if an unlinked feedback row exists for this contact
        contact_norm = re.sub(r'\D', '', client_contact)[-10:]
        unlinked = None
        if contact_norm:
            cursor.execute("SELECT id FROM enquiry_feedback WHERE enquiry_id IS NULL AND client_contact LIKE ? LIMIT 1", (f"%{contact_norm}%",))
            unlinked = cursor.fetchone()

        if unlinked:
            cursor.execute("""
                UPDATE enquiry_feedback SET
                    enquiry_id = ?,
                    client_name = ?,
                    enquiry_source = ?,
                    project_name = ?,
                    configuration = ?,
                    cost = ?,
                    carpet = ?,
                    possession = ?,
                    website_enquiry_url = ?
                WHERE id = ?
            """, (
                enquiry_id, client_name, enquiry_src, project_name, config,
                cost_val, carpet_val, possession_val, url_val, unlinked['id']
            ))
            fb_id = unlinked['id']
        else:
            msg = (enq.get('message') or '').strip()
            if msg and msg != '—':
                feedback_notes = f"Website Enquiry Notes: {msg}"
            else:
                feedback_notes = "Website enquiry received online. Awaiting client discussion & feedback."

            cursor.execute("""
                INSERT INTO enquiry_feedback (
                    enquiry_id, client_name, client_contact, enquiry_datetime, enquiry_source,
                    project_name, configuration, cost, carpet, possession,
                    website_enquiry_url, client_feedback, feedback_by_username, feedback_datetime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enquiry_id, client_name, client_contact, enquiry_dt, enquiry_src,
                project_name, config, cost_val, carpet_val, possession_val,
                url_val, feedback_notes, username, now_str
            ))
            fb_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return fb_id

def sync_website_enquiries_to_feedback(username='admin', role='admin', user_id=None):
    """
    Fetch latest enquiries directly from website enquiry database and synchronize into enquiry_feedback.
    Requirements:
    1. Fetches latest enquiries directly from website enquiry database and existing CRM enquiries.
    2. Newly generated enquiries appear without requiring manual entry.
    3. Prevents duplicate enquiries when the Refresh button is clicked multiple times.
    4. Preserves all existing feedback records.
    5. Populates all required fields: Lead ID, Name, Contact, DateTime, Source, Project, Config, Cost, Carpet, Possession, URL.
    Returns: (count_added, message)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Query all website enquiries joined with property details
    query = """
        SELECT e.*, 
               p.title as prop_title, 
               p.slug as prop_slug, 
               p.configuration as prop_config, 
               p.price as prop_price, 
               p.carpet_area as prop_carpet, 
               p.possession_status as prop_possession
        FROM enquiries e
        LEFT JOIN properties p ON (e.property_id = p.id OR (e.property_id IS NULL AND LOWER(TRIM(e.property_title)) = LOWER(TRIM(p.title))))
    """
    params = []
    if user_id and role in ('agent', 'owner'):
        query += " WHERE (e.property_owner_id = ? OR e.property_owner_id IS NULL)"
        params.append(user_id)
    
    query += " ORDER BY e.id ASC"
    cursor.execute(query, params)
    website_enquiries = cursor.fetchall()

    if not website_enquiries:
        conn.close()
        return 0, "No New Enquiries Found."

    # Fetch existing enquiry_feedback records to prevent duplicates
    cursor.execute("SELECT id, enquiry_id, client_contact, enquiry_datetime, project_name FROM enquiry_feedback")
    existing_fb = cursor.fetchall()
    
    existing_enq_ids = set()
    unlinked_fb_by_contact = {}
    for fb in existing_fb:
        if fb['enquiry_id']:
            existing_enq_ids.add(fb['enquiry_id'])
        else:
            contact_norm = re.sub(r'\D', '', str(fb['client_contact'] or ''))[-10:]
            if contact_norm and contact_norm not in unlinked_fb_by_contact:
                unlinked_fb_by_contact[contact_norm] = fb['id']

    count_added = 0
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for enq_row in website_enquiries:
        enq = dict(enq_row)
        enq_id = enq['id']
        contact_norm = re.sub(r'\D', '', str(enq['phone'] or ''))[-10:]
        enq_title = enq['prop_title'] or enq['property_title'] or 'General Website Enquiry'

        # If already linked, update any newly synced fields like website_enquiry_url or lead_source if missing
        if enq_id in existing_enq_ids:
            enq_url = (enq.get('website_enquiry_url') or '').strip()
            if enq_url and enq_url not in ('—', '-', 'None', 'N/A'):
                cursor.execute("""
                    UPDATE enquiry_feedback 
                    SET website_enquiry_url = ? 
                    WHERE enquiry_id = ? AND (website_enquiry_url IS NULL OR website_enquiry_url IN ('', '—', '-', 'None', 'N/A'))
                """, (enq_url, enq_id))
            if enq.get('lead_source'):
                cursor.execute("""
                    UPDATE enquiry_feedback 
                    SET enquiry_source = ? 
                    WHERE enquiry_id = ? AND (enquiry_source IS NULL OR enquiry_source = '')
                """, (enq['lead_source'], enq_id))
            continue

        # If an unlinked feedback record exists with this contact, link it instead of duplicating
        if contact_norm and contact_norm in unlinked_fb_by_contact:
            target_fb_id = unlinked_fb_by_contact.pop(contact_norm)
            cursor.execute("UPDATE enquiry_feedback SET enquiry_id = ? WHERE id = ?", (enq_id, target_fb_id))
            existing_enq_ids.add(enq_id)
            continue

        # Prepare details for new feedback entry
        client_name = (enq['name'] or '').strip()
        client_contact = (enq['phone'] or '').strip()
        enquiry_dt = str(enq['created_at'] or now_str)[:19]
        enquiry_src = (enq['lead_source'] or 'Website Direct').strip()
        project_name = enq_title

        # Configuration
        config = enq['prop_config'] or (enq['enquiry_type'] if 'BHK' in str(enq.get('enquiry_type', '')) else '—')
        
        # Cost
        if enq['prop_price'] and float(enq['prop_price']) > 0:
            cost_val = float(enq['prop_price'])
        else:
            cost_val = parse_cost_from_budget(enq.get('budget'))

        # Carpet Area
        if enq['prop_carpet']:
            carpet_val = f"{enq['prop_carpet']} sq ft"
        else:
            carpet_val = '—'

        # Possession
        possession_val = enq['prop_possession'] or '—'

        # Website Enquiry URL
        url_val = (enq.get('website_enquiry_url') or '').strip()
        if not url_val or url_val in ('—', '-', 'None', 'N/A'):
            if enq['prop_slug']:
                url_val = f"/property/{enq['prop_slug']}"
            else:
                url_val = '—'

        # Initial Client Feedback notes
        msg = (enq['message'] or '').strip()
        if msg and msg != '—':
            feedback_notes = f"Website Enquiry Notes: {msg}"
        else:
            feedback_notes = "Website enquiry received online. Awaiting client discussion & feedback."

        cursor.execute("""
            INSERT INTO enquiry_feedback (
                enquiry_id, client_name, client_contact, enquiry_datetime, enquiry_source,
                project_name, configuration, cost, carpet, possession,
                website_enquiry_url, client_feedback, feedback_by_username, feedback_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            enq_id, client_name, client_contact, enquiry_dt, enquiry_src,
            project_name, config, cost_val, carpet_val, possession_val,
            url_val, feedback_notes, username, now_str
        ))
        existing_enq_ids.add(enq_id)
        count_added += 1

    conn.commit()
    conn.close()

    if count_added > 0:
        log_user_activity(
            username=username,
            role=role,
            activity_type='Feedback Refreshed',
            details=f"Refreshed enquiries: Synchronized {count_added} newly received website enquiries into Feedback."
        )
        return count_added, f"Successfully refreshed! {count_added} new enquiry/enquiries imported into Feedback."
    else:
        return 0, "No New Enquiries Found."

# -----------------------------------------------------------------------------
# LIVE VISITOR & USER ACTIVITY MODULE
# -----------------------------------------------------------------------------

def track_visitor_session(session_id, ip_address, user_agent, username=None, role='visitor', is_authenticated=0):
    """Track active visitor and authenticated user sessions."""
    conn = get_db()
    cursor = conn.cursor()
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        INSERT INTO visitor_sessions (
            session_id, ip_address, user_agent, username, role, is_authenticated, last_activity, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            ip_address = excluded.ip_address,
            user_agent = excluded.user_agent,
            username = CASE WHEN excluded.username IS NOT NULL THEN excluded.username ELSE visitor_sessions.username END,
            role = CASE WHEN excluded.is_authenticated = 1 THEN excluded.role ELSE visitor_sessions.role END,
            is_authenticated = MAX(visitor_sessions.is_authenticated, excluded.is_authenticated),
            last_activity = excluded.last_activity
    """, (session_id, ip_address, user_agent, username, role, is_authenticated, now_utc, now_utc))
    conn.commit()
    conn.close()

def log_user_activity(username, role, activity_type, ip_address='', details=''):
    """Record user activity (Login, Logout, Session Expired, Feedback CRUD) into audit log."""
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now()
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    activity_date = now.strftime('%Y-%m-%d')
    activity_time = now.strftime('%H:%M:%S')

    cursor.execute("""
        INSERT INTO user_activity_logs (
            username, role, activity_type, ip_address, activity_date, activity_time, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (username or 'Anonymous', role or 'Visitor', activity_type, ip_address, activity_date, activity_time, details, now_utc))
    conn.commit()
    conn.close()

def get_live_activity_stats(active_window_minutes=5):
    """Get live visitor and user activity counts backed by real SQL database records."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Total Counts
    cursor.execute("SELECT COUNT(DISTINCT session_id) as total_visitors FROM visitor_sessions WHERE is_authenticated = 0")
    total_visitors = cursor.fetchone()['total_visitors']

    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT COUNT(*) as total_agents FROM users WHERE role = 'agent'")
    total_agents = cursor.fetchone()['total_agents']

    cursor.execute("SELECT COUNT(*) as total_owners FROM users WHERE role = 'owner'")
    total_owners = cursor.fetchone()['total_owners']

    cursor.execute("SELECT COUNT(*) as total_admins FROM users WHERE role = 'admin'")
    total_admins = cursor.fetchone()['total_admins']

    cursor.execute("SELECT COUNT(*) as total_logins FROM user_activity_logs WHERE activity_type = 'Login'")
    total_logins = cursor.fetchone()['total_logins']

    # 2. Real-time Active Counts (Within window)
    window_modifier = f"-{int(active_window_minutes)} minutes"

    # Active Website Visitors (non-authenticated sessions)
    cursor.execute("""
        SELECT COUNT(DISTINCT session_id) as active_visitors 
        FROM visitor_sessions 
        WHERE is_authenticated = 0 
          AND last_activity >= datetime('now', ?)
    """, (window_modifier,))
    active_visitors = cursor.fetchone()['active_visitors']

    # Active Logged-in Users
    cursor.execute("""
        SELECT COUNT(DISTINCT username) as active_users 
        FROM visitor_sessions 
        WHERE is_authenticated = 1 
          AND username IS NOT NULL 
          AND last_activity >= datetime('now', ?)
    """, (window_modifier,))
    active_users = cursor.fetchone()['active_users']

    # Active Agents
    cursor.execute("""
        SELECT COUNT(DISTINCT username) as active_agents 
        FROM visitor_sessions 
        WHERE is_authenticated = 1 
          AND role = 'agent' 
          AND last_activity >= datetime('now', ?)
    """, (window_modifier,))
    active_agents = cursor.fetchone()['active_agents']

    # Active Property Owners
    cursor.execute("""
        SELECT COUNT(DISTINCT username) as active_owners 
        FROM visitor_sessions 
        WHERE is_authenticated = 1 
          AND role = 'owner' 
          AND last_activity >= datetime('now', ?)
    """, (window_modifier,))
    active_owners = cursor.fetchone()['active_owners']

    # Active Admin Users
    cursor.execute("""
        SELECT COUNT(DISTINCT username) as active_admins 
        FROM visitor_sessions 
        WHERE is_authenticated = 1 
          AND role = 'admin' 
          AND last_activity >= datetime('now', ?)
    """, (window_modifier,))
    active_admins = cursor.fetchone()['active_admins']

    conn.close()
    return {
        'total_visitors': total_visitors,
        'total_registered_users': total_users,
        'total_agents': total_agents,
        'total_owners': total_owners,
        'total_admins': total_admins,
        'total_login_sessions': total_logins,
        'active_visitors': active_visitors,
        'active_users': active_users,
        'active_agents': active_agents,
        'active_owners': active_owners,
        'active_admins': active_admins,
        'active_window_minutes': active_window_minutes
    }

def get_recent_activity_logs(limit=10):
    """Retrieve the latest login and logout activities."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM user_activity_logs 
        WHERE activity_type IN ('Login', 'Logout', 'Session Expired')
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -----------------------------------------------------------------------------
# SYSTEM SETTINGS
# -----------------------------------------------------------------------------

def get_setting(key, default=None):
    """Retrieve a system setting by key."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row and row['value'] is not None:
        return row['value']
    return default

def set_setting(key, value):
    """Store or update a system setting by key."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO system_settings (key, value, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, str(value)))
    conn.commit()
    conn.close()
    return True

def get_website_name():
    """Retrieve active website/project name (default: GRN Properties)."""
    return get_setting('website_name', 'GRN Properties')

def set_website_name(name):
    """Update active website/project name."""
    name_clean = (name or '').strip()
    if not name_clean:
        return False
    set_setting('website_name', name_clean)
    set_setting('company_name', name_clean)
    return True

def get_whatsapp_default_message():
    """Retrieve default WhatsApp contact greeting with website name fallback."""
    site_name = get_website_name()
    default_msg = f"Hi {site_name}, I am looking for property consultation in Pune."
    return get_setting('whatsapp_default_message', default_msg)

def get_whatsapp_message():
    """Alias for backwards compatibility."""
    return get_whatsapp_default_message()

def set_whatsapp_message(message):
    """Store or update default WhatsApp contact greeting."""
    msg_clean = (message or '').strip()
    if not msg_clean:
        return False
    return set_setting('whatsapp_default_message', msg_clean)

def get_whatsapp_listing_title_format():
    """Retrieve format template for listing title in WhatsApp message."""
    default_fmt = "Property / Listing Name: {{listing_title}}."
    return get_setting('whatsapp_listing_title_format', default_fmt)

def get_whatsapp_listing_url_format():
    """Retrieve format template for listing URL in WhatsApp message."""
    default_fmt = "Property Details Link: {{listing_url}}"
    return get_setting('whatsapp_listing_url_format', default_fmt)

def get_whatsapp_additional_message():
    """Retrieve optional additional WhatsApp message."""
    default_add = "Please share the complete property details, pricing, location and site visit availability."
    return get_setting('whatsapp_additional_message', default_add)

def get_all_whatsapp_settings():
    """Retrieve all WhatsApp message configuration fields as a dictionary."""
    return {
        'default_message': get_whatsapp_default_message(),
        'listing_title_format': get_whatsapp_listing_title_format(),
        'listing_url_format': get_whatsapp_listing_url_format(),
        'additional_message': get_whatsapp_additional_message()
    }

def set_whatsapp_settings(default_message, listing_title_format=None, listing_url_format=None, additional_message=None):
    """Store or update all WhatsApp message configuration fields."""
    default_clean = (default_message or '').strip()
    if not default_clean:
        return False
    set_setting('whatsapp_default_message', default_clean)
    if listing_title_format is not None:
        set_setting('whatsapp_listing_title_format', listing_title_format.strip() or "Property / Listing Name: {{listing_title}}.")
    if listing_url_format is not None:
        set_setting('whatsapp_listing_url_format', listing_url_format.strip() or "Property Details Link: {{listing_url}}")
    if additional_message is not None:
        set_setting('whatsapp_additional_message', additional_message.strip())
    return True

def reset_whatsapp_settings_to_default():
    """Reset all WhatsApp message configuration fields back to factory defaults."""
    site_name = get_website_name()
    default_msg = f"Hi {site_name}, I am looking for property consultation in Pune."
    default_title_fmt = "Property / Listing Name: {{listing_title}}."
    default_url_fmt = "Property Details Link: {{listing_url}}"
    default_add = "Please share the complete property details, pricing, location and site visit availability."
    set_setting('whatsapp_default_message', default_msg)
    set_setting('whatsapp_listing_title_format', default_title_fmt)
    set_setting('whatsapp_listing_url_format', default_url_fmt)
    set_setting('whatsapp_additional_message', default_add)
    return True

def format_whatsapp_message(listing_title=None, listing_url=None, default_msg=None, title_fmt=None, url_fmt=None, add_msg=None):
    """
    Generate composite WhatsApp message in sequence:
    1. Default WhatsApp Contact Message.
    2. Listing Title (if provided).
    3. Listing URL (if provided).
    4. Additional Message (if configured).
    Skips empty/blank optional parts without leaving blank lines.
    """
    if default_msg is None:
        default_msg = get_whatsapp_default_message()
    if title_fmt is None:
        title_fmt = get_whatsapp_listing_title_format()
    if url_fmt is None:
        url_fmt = get_whatsapp_listing_url_format()
    if add_msg is None:
        add_msg = get_whatsapp_additional_message()

    parts = []
    if default_msg and default_msg.strip():
        parts.append(default_msg.strip())

    if listing_title and listing_title.strip():
        clean_title = listing_title.strip()
        fmt_t = title_fmt.strip() if title_fmt else "Property / Listing Name: {{listing_title}}."
        if '{{listing_title}}' in fmt_t:
            title_line = fmt_t.replace('{{listing_title}}', clean_title)
        elif '{listing_title}' in fmt_t:
            title_line = fmt_t.replace('{listing_title}', clean_title)
        elif fmt_t:
            title_line = f"{fmt_t} {clean_title}"
        else:
            title_line = f"Property / Listing Name: {clean_title}."
        parts.append(title_line.strip())

    if listing_url and listing_url.strip():
        clean_url = listing_url.strip()
        fmt_u = url_fmt.strip() if url_fmt else "Property Details Link: {{listing_url}}"
        if '{{listing_url}}' in fmt_u:
            url_line = fmt_u.replace('{{listing_url}}', clean_url)
        elif '{listing_url}' in fmt_u:
            url_line = fmt_u.replace('{listing_url}', clean_url)
        elif fmt_u:
            url_line = f"{fmt_u} {clean_url}"
        else:
            url_line = f"Property Details Link: {clean_url}"
        parts.append(url_line.strip())

    if add_msg and add_msg.strip():
        parts.append(add_msg.strip())

    return "\n\n".join(parts)

# -----------------------------------------------------------------------------
# OFFICE & CONTACT SETTINGS MANAGEMENT
# -----------------------------------------------------------------------------

def get_all_contact_settings(only_enabled=False):
    """Retrieve all contact settings ordered by display_order."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM contact_settings"
    if only_enabled:
        query += " WHERE is_enabled = 1"
    query += " ORDER BY display_order ASC, id ASC"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_contact_settings_dict():
    """Retrieve contact settings as a dictionary keyed by field_key."""
    settings_list = get_all_contact_settings()
    return {item['field_key']: item for item in settings_list}

def get_contact_setting(field_key, default=None):
    """Retrieve a single contact setting by field_key."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact_settings WHERE field_key = ?", (field_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return default

def update_contact_setting(field_key, value=None, is_enabled=None, display_order=None, label=None, icon=None, link_type=None):
    """Update an existing contact setting by field_key."""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    params = []

    if value is not None:
        updates.append("value = ?")
        params.append(str(value).strip())
    if is_enabled is not None:
        updates.append("is_enabled = ?")
        params.append(1 if is_enabled else 0)
    if display_order is not None:
        try:
            updates.append("display_order = ?")
            params.append(int(display_order))
        except (ValueError, TypeError):
            pass
    if label is not None:
        updates.append("label = ?")
        params.append(str(label).strip())
    if icon is not None:
        updates.append("icon = ?")
        params.append(str(icon).strip())
    if link_type is not None:
        updates.append("link_type = ?")
        params.append(str(link_type).strip())

    if not updates:
        conn.close()
        return False

    updates.append("updated_at = CURRENT_TIMESTAMP")
    sql = f"UPDATE contact_settings SET {', '.join(updates)} WHERE field_key = ?"
    params.append(field_key)
    cursor.execute(sql, tuple(params))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def add_custom_contact_setting(label, value, icon='fas fa-info-circle', link_type='none', is_enabled=1, display_order=90):
    """Add a new custom contact information field."""
    label = (label or '').strip()
    value = (value or '').strip()
    if not label or not value:
        return None

    import uuid
    safe_slug = re.sub(r'[^a-zA-Z0-9]+', '_', label.lower()).strip('_')[:20]
    field_key = f"custom_{safe_slug}_{uuid.uuid4().hex[:6]}"
    conn = get_db()
    cursor = conn.cursor()
    try:
        order_val = int(display_order)
    except (ValueError, TypeError):
        order_val = 90

    cursor.execute("""
        INSERT INTO contact_settings (field_key, label, value, icon, is_enabled, display_order, is_custom, category, link_type)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'additional', ?)
    """, (field_key, label, value, icon or 'fas fa-info-circle', 1 if is_enabled else 0, order_val, link_type or 'none'))
    conn.commit()
    conn.close()
    return field_key

def delete_contact_setting(field_key):
    """Delete a contact setting by field_key (only custom or optional items)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_settings WHERE field_key = ?", (field_key,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def reset_contact_settings_to_default():
    """Reset standard contact settings to system default values and re-enable them."""
    default_vals = {
        'corporate_office': ("Corporate Office", "Office 405, Platinum Square, Near Balewadi High Street, Baner-Balewadi Road, Pune, Maharashtra 411045", "fas fa-map-marked-alt", 10, "none"),
        'company_phone': ("Call Us", "+91 7499077170", "fas fa-phone-alt", 20, "tel"),
        'company_whatsapp': ("WhatsApp Desk", "+91 7499077170", "fab fa-whatsapp", 30, "whatsapp"),
        'company_email': ("Email Address", "contact@realestate.com", "fas fa-envelope", 40, "mailto"),
        'company_rera': ("MahaRERA Reg. No.", "MahaRERA Reg. No: A52100034982", "fas fa-shield-alt", 50, "none"),
        'branch_office': ("Branch Office", "Tower B, Phase 1, Hinjewadi IT Park, Pune, Maharashtra 411057", "fas fa-building", 60, "none"),
        'working_hours': ("Working Hours", "Mon - Sat: 9:30 AM - 7:30 PM | Sun: By Appointment", "fas fa-clock", 70, "none"),
        'google_maps_url': ("Google Maps Location", "https://maps.google.com/maps?q=Balewadi+High+Street,+Pune,+Maharashtra&t=&z=14&ie=UTF8&iwloc=&output=embed", "fas fa-map-marker-alt", 80, "url"),
    }
    conn = get_db()
    cursor = conn.cursor()
    for key, (label, val, icon, order, link_type) in default_vals.items():
        cursor.execute("""
            INSERT INTO contact_settings (field_key, label, value, icon, is_enabled, display_order, is_custom, category, link_type)
            VALUES (?, ?, ?, ?, 1, ?, 0, 'standard', ?)
            ON CONFLICT(field_key) DO UPDATE SET 
                label = excluded.label,
                value = excluded.value,
                icon = excluded.icon,
                is_enabled = 1,
                display_order = excluded.display_order,
                link_type = excluded.link_type,
                updated_at = CURRENT_TIMESTAMP
        """, (key, label, val, icon, order, link_type))
    # Also delete any custom additional items on full reset
    cursor.execute("DELETE FROM contact_settings WHERE is_custom = 1")
    conn.commit()
    conn.close()
    return True

# -----------------------------------------------------------------------------
# WEBSITE VISIBILITY MANAGEMENT
# -----------------------------------------------------------------------------

_visibility_cache = None

def get_visibility_map(force_refresh=False):
    """Retrieve key-value dictionary mapping item_key -> boolean is_visible."""
    global _visibility_cache
    if _visibility_cache is not None and not force_refresh:
        return _visibility_cache
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_key, is_visible FROM website_visibility")
    rows = cursor.fetchall()
    conn.close()
    _visibility_cache = {row['item_key']: bool(row['is_visible']) for row in rows}
    return _visibility_cache

def is_item_visible(item_key, default=True):
    """Check if a specific menu, page, section or function is currently visible."""
    v_map = get_visibility_map()
    return v_map.get(item_key, default)

def get_all_visibility_settings(category=None, search=None, status=None):
    """Retrieve full list of visibility settings with optional category and search filters."""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM website_visibility WHERE 1=1"
    params = []

    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)

    if status is not None and status != '' and status != 'All':
        if str(status) in ('1', 'true', 'active', 'on'):
            query += " AND is_visible = 1"
        elif str(status) in ('0', 'false', 'inactive', 'off'):
            query += " AND is_visible = 0"

    if search:
        kw = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR item_key LIKE ? OR description LIKE ? OR url_path LIKE ? OR category LIKE ?)"
        params.extend([kw, kw, kw, kw, kw])

    query += " ORDER BY category ASC, display_order ASC, id ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_visibility_setting(item_key, is_visible, updated_by='admin'):
    """Update visibility status for an individual menu/function."""
    global _visibility_cache
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE website_visibility 
        SET is_visible = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE item_key = ?
    """, (1 if is_visible else 0, updated_by or 'admin', item_key))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    _visibility_cache = None # invalidate cache
    return affected > 0

def bulk_update_visibility(is_visible, category=None, updated_by='admin'):
    """Bulk enable or disable visibility for all items or a specific category."""
    global _visibility_cache
    conn = get_db()
    cursor = conn.cursor()
    
    val = 1 if is_visible else 0
    if category and category != 'All':
        cursor.execute("""
            UPDATE website_visibility 
            SET is_visible = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE category = ?
        """, (val, updated_by or 'admin', category))
    else:
        cursor.execute("""
            UPDATE website_visibility 
            SET is_visible = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
        """, (val, updated_by or 'admin'))
        
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    _visibility_cache = None # invalidate cache
    return affected

def add_visibility_setting(item_key, name, category, url_path='', description='', is_visible=1, display_order=0, updated_by='admin'):
    """Add a new configurable visibility setting item or update if exists."""
    global _visibility_cache
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO website_visibility (item_key, name, category, url_path, description, is_visible, display_order, updated_by, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(item_key) DO UPDATE SET 
            name = excluded.name,
            category = excluded.category,
            url_path = excluded.url_path,
            description = excluded.description,
            is_visible = excluded.is_visible,
            display_order = excluded.display_order,
            updated_by = excluded.updated_by,
            updated_at = CURRENT_TIMESTAMP
    """, (item_key, name, category, url_path, description, 1 if is_visible else 0, display_order, updated_by or 'admin'))
    conn.commit()
    conn.close()
    _visibility_cache = None
    return True

def get_visibility_stats():
    """Get aggregated statistics on visibility items."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN is_visible = 1 THEN 1 ELSE 0 END) as visible, SUM(CASE WHEN is_visible = 0 THEN 1 ELSE 0 END) as hidden FROM website_visibility")
    row = cursor.fetchone()
    total = row['total'] or 0
    visible = row['visible'] or 0
    hidden = row['hidden'] or 0
    
    cursor.execute("""
        SELECT category, COUNT(*) as cat_total,
               SUM(CASE WHEN is_visible = 1 THEN 1 ELSE 0 END) as cat_visible,
               SUM(CASE WHEN is_visible = 0 THEN 1 ELSE 0 END) as cat_hidden
        FROM website_visibility 
        GROUP BY category 
        ORDER BY category ASC
    """)
    cat_rows = cursor.fetchall()
    conn.close()
    
    categories = [dict(c) for c in cat_rows]
    return {
        'total': total,
        'visible': visible,
        'hidden': hidden,
        'categories': categories
    }

