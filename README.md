# GRN PROPERTIES – Professional Real Estate Website

A modern, luxurious, fully responsive real estate agent web application built with **Python (Flask)**, **SQLite**, **Bootstrap 5**, and custom **Black & Gold styling**. Designed specifically for high-end residential and commercial real estate markets in Pune (Wakad, Hinjewadi, Baner, Balewadi, Pimple Saudagar, Tathawade, Ravet, Punawale, PCMC).

---

## 🌟 Key Features

### 1. Luxury Black & Gold Design
- **Theme Palette**: Obsidian Black (`#0A0B0E`), Pure Gold (`#D4AF37`), Light Champagne (`#F2D07C`), and Crisp Off-White.
- **Typography**: Google Fonts (*Cinzel* for architectural serif headings and *Plus Jakarta Sans* / *Montserrat* for crisp UI text).
- **Smooth Animations**: Subtle glassmorphism, card lifts, glowing borders, and pulsating WhatsApp triggers.
- **Responsive Layout**: Pixel-perfect on smartphones, tablets, laptops, and ultra-wide screens.

### 2. Powerful Homepage
- **Branded Navigation**: Logo, Home, Buy, Sell, Rent, Commercial, All Properties, About Us, Contact.
- **Dynamic Property Search Bar**:
  - Purpose switcher (Buy / Rent / Commercial)
  - Pune Micro-market location filter (Wakad, Hinjewadi, Baner, Balewadi, etc.)
  - Property Category & Type filter
  - Configuration selector (1 BHK, 2 BHK, 3 BHK, 4 BHK+, Villa, Plot, Commercial)
  - Budget selector
- **Featured Properties Showcase**: Handpicked premium properties with prices, specs, and instant inquiry modals.
- **Category Explorer**: 8 dedicated property categories (Residential, Commercial, Luxury Villas, Apartments, Bungalows, Land/Plots, Office Spaces, Shops).
- **Pune Micro-Market Focus**: Highlighting appreciation and yields in Hinjewadi, Wakad, Baner, Balewadi, etc.
- **Why Choose GRN PROPERTIES**: Highlighting 100% MahaRERA verified titles, zero brokerage on direct builder projects, and end-to-end legal/loan assistance.
- **Client Testimonials**: Authentic experiences from Pune IT executives, business owners, and doctors.
- **Instant Lead Capture Section**: Direct advisor inquiry form.

### 3. Comprehensive Property Listings (`/properties`)
- Dynamic multi-parameter filtering:
  - Buy / Rent purpose
  - Category filter pills
  - Pune localities
  - Configuration (BHK)
  - Price range slider/inputs (Min / Max)
  - Keyword search
  - Sorting (Latest, Price: Low to High, Price: High to Low, Largest Area)
- Real-time property count indicator and reset filters capability.

### 4. Property Details Page (`/property/<slug>`)
- High-resolution interactive image gallery with thumbnail switcher.
- Key specification cards (Configuration, Carpet Area, Possession, Bathrooms, Status).
- MahaRERA registration badge and verification note.
- Full architectural description and key highlights.
- Amenities grid with custom gold icons.
- Strategic connectivity and nearby transit distances.
- **Interactive Home Loan EMI Estimator** with dynamic interest rates and tenure adjustments.
- **Direct Agent Contact Sidebar**:
  - One-click WhatsApp inquiry with pre-filled property reference
  - Click-to-call helpline button
  - Schedule a Site Visit modal
  - On-page quick message form
- Similar / recommended properties in the same Pune micro-market.

### 5. Lead Generation & CRM Pipeline
- Captures customer name, mobile number, email, property interested in, budget, preferred location, preferred site visit date, and remarks.
- Stores all enquiries in SQLite database.
- Universal **"Schedule a Site Visit"** modal accessible across all pages and property cards.
- **"Sell / List Your Property"** dedicated owner intake page (`/sell`).
- **Bulk Delete / Multiple Selection**:
  - Bulk select enquiries via individual and "Select All" checkboxes.
  - Delete Selected action with confirmation popup (`Are you sure you want to permanently delete the selected enquiry records?`).
  - Automatic relationship handling: unlinks linked feedback records safely without accidental data deletion.
  - Audit logging of all bulk deletion events.

### 6. Client Enquiry Feedback & Activity Auditing
- 13 comprehensive feedback columns including configuration, cost, carpet area, possession, website enquiry URL, and user feedback notes.
- **Bulk Delete / Multiple Selection**: Select multiple feedback entries with Select All, Deselect All, and confirmed bulk deletion.
- Auto-sync with CRM leads and real-time activity tracking.

### 7. Clean Admin Navigation Architecture
- **Streamlined Main Navbar**: Dashboard, Leads & Enquiries, Feedback, Website Visibility, and Settings.
- **Organized Settings Submenus**:
  1. Pending Approval
  2. Properties
  3. User Management
  4. Feedback
  5. Website Visibility
  (plus Website General Settings, Office & Contact Settings, WhatsApp Message Settings, and My Profile).
- Floating WhatsApp button with pulsing animation.
- Mobile-friendly fixed bottom contact bar.

### 6. Agent & Property Owner Portal (`/dashboard`)
- **Role-Based Registration & Login (`/register`, `/login`)**:
  - Separate account types for **Real Estate Agents** (with Agency Name & MahaRERA number) and **Property Owners** (individual sellers/landlords).
- **Post Property Ads (`/dashboard/properties/add`)**:
  - Form capturing title, category, type, purpose (Buy/Rent), price, carpet area, configuration, location, street address, photo uploads or URLs, floor plans, amenities, and connectivity landmarks.
- **Manage My Property Ads (`/dashboard/properties`)**:
  - View all listings posted by the user.
  - 1-click status toggle (`Available` / `Sold` / `Rented`).
  - Edit or delete listings.
- **Lead CRM & Customer Pipeline (`/dashboard/crm`)**:
  - Automatically captures and routes buyer/tenant inquiries for properties posted by that user.
  - Status pipeline: `New`, `In Progress`, `Site Visit Scheduled`, `Closed`.
  - Real-time lead keyword search.
  - **1-Click WhatsApp Direct Contact**: Launches WhatsApp with pre-filled greeting and property reference.
  - **1-Click Phone Calling**: Direct dialing link.
  - **CRM Follow-Up & Negotiation Notes**: Log call details, client preferences, and scheduled site visits.
  - **Export My Leads (CSV)**: Export all customer leads for offline records.

### 7. Secure Admin Dashboard (`/admin`)
- **Protected Authentication**: Username/password session authentication with `werkzeug.security` password hashing.
- **Executive Analytics**: Total properties, active listings, sold/rented units, total leads, new unread leads, and scheduled site visits.
- **Property Inventory Management**:
  - View all properties in a responsive data table
  - Add new property with multi-image upload or web URLs
  - Edit property details, floor plans, landmarks, and amenities
  - 1-click status update (`Available` / `Sold` / `Rented`)
  - Delete property listing
- **Customer CRM & Enquiry Management**:
  - Filter leads by status (`New`, `In Progress`, `Site Visit Scheduled`, `Closed`)
  - Real-time keyword search across customer name, phone, or location
  - One-click WhatsApp chat and telephone dialing
  - Follow-up notes modal to log conversation details
  - **Export all leads to CSV** for offline reporting
- **Website & WhatsApp Settings (`/admin/settings`)**:
  - **Website General Settings**: Edit and update the Project / Website Name at any time with dynamic propagation to browser tab titles, header logo text, footer copyright, about/contact sections, and default greeting messages. Includes 1-click **Reset to Default** (`GRN Properties`).
  - **WhatsApp Message Settings (`/admin/settings?tab=whatsapp`)**:
    - Centralized dynamic configuration of pre-filled WhatsApp consultation inquiries across the website.
    - **4 Configurable Message Fields**:
      1. **Default WhatsApp Contact Message \***: Mandatory greeting opening all WhatsApp chats.
      2. **Listing Title**: Configurable format with dynamic placeholder `{{listing_title}}` (automatically fetches real property title; omitted on general pages).
      3. **Listing URL (Property URL)**: Configurable format with dynamic placeholder `{{listing_url}}` (automatically generates the exact property page URL; omitted on general pages).
      4. **Additional Message (Optional)**: Optional customer instructions or inquiry questions. Automatically skipped without empty lines if left blank.
    - **Dynamic Sequence**: Assembles `1. Default Greeting &bull; 2. Listing Title &bull; 3. Listing URL &bull; 4. Additional Message` with proper URL encoding.
    - **Interactive Chat Simulation & Preview**: Real-time simulation toggleable between General Website Visitor Mode and Property Listing Visitor Mode with sample property switcher.
    - **Live Testing & Reset**: Test Live WhatsApp button opening directly into WhatsApp, plus 1-click **Reset to Default**.
  - **Office & Contact Settings (`/admin/settings?tab=contact` or `/admin/contact-settings`)**:
    - Centralized management of all company office and contact information without editing code.
    - Manages: **Corporate Office**, **Call Us**, **WhatsApp Desk**, **Email Address**, **MahaRERA Reg. No.**, **Branch Office**, **Working Hours**, **Google Maps Location**, and **Additional Contact Information** (dynamic custom fields).
    - **Granular Enable/Disable**: Toggle each individual field on or off to control its visibility across the public site.
    - **Display Ordering**: Set custom numerical display order to arrange contact information dynamically.
    - **Custom Contact Touchpoints**: Add, edit, and delete dynamic additional contact channels with custom labels, icons, and protocol link handlers (`tel:`, `mailto:`, `https://`).
    - **1-Click Reset to Default**: Quickly restore all office and contact details back to factory defaults.
    - **Site-Wide Real-Time Propagation**: Immediately updates the Contact Us page, Website Footer, Top Utility Bar, About Us page, and Homepage.
    - **Strict Validation & Security**: Protected by `@admin_required` with server-side validation for address, phone digits, and email formats.
  - **Admin My Profile Management (`/admin/profile`)**:
    - Dedicated profile administration console allowing Administrators to view and update their profile credentials and personal info at any time.
    - **Personal & Office Details**: Full Name, Official Email Address, Contact Mobile/Phone, Agency/Desk Title, MahaRERA Registration Number, and Bio/Executive Notes.
    - **Live Session Syncing**: Instantly updates header user dropdowns, display greetings, and administrative logs across all views without requiring re-login.
    - **Account Security & Password Updates**: Real-time password verification requiring current password confirmation, minimum length validation (6+ characters), and confirmation match before saving hashed credentials with Werkzeug.
    - **Executive Portfolio KPI Banner**: Overview card featuring real-time metrics on properties listed, active portfolio items, and client inquiries handled.
    - **Multiple Quick Access Points**: Accessible directly from the top Admin User dropdown menu, Admin Settings navigation menu, and Dashboard Quick Action buttons.
    - **Security & Authorization**: Protected with `@admin_required`, strict server-side phone/email validation, and administrative audit logging.
  - **Enquiry Feedback Management & Dynamic Edit Loading (`/admin/feedback` & `/dashboard/feedback`)**:
    - Complete recording and tracking of prospective client consultation feedback across all 13 core metrics.
    - **Dynamic Edit Loading (`/api/feedback/<id>`)**: Automatically queries database on Edit click to load and populate all 13 fields (SN/ID, Client Name, Contact, Enquiry Date/Time, Project Name, Configuration, Cost, Carpet, Possession, Enquiry URL, Client Feedback, Feedback By Username, Feedback Date/Time).
    - **Safe Database Merging**: Prevents wiping existing data with blank/null values on form submission.
    - **Sort By Created Date & Time**: Filter and sort the entire dataset by **Newest First** or **Oldest First**, preserved across search and pagination.
  - **Lead CRM & Enquiry Pipeline (`/admin/enquiries` & `/dashboard/crm`)**:
    - Manage buyer leads and consultation requests across lead sources and deal statuses.
    - **Sort By Created Date & Time**: Filter by **Newest First** and **Oldest First** with real-time status and source filtering.
  - **Admin Settings Submenu Hierarchy**:
    - Centralized navigation structure grouping core operational modules under **Settings**:
      1. **Pending Approval** (`/admin/properties/pending`)
      2. **Properties** (`/admin/properties`)
      3. **User Management** (`/admin/users`)
      4. **Feedback** (`/admin/feedback`)
      5. **Website Visibility** (`/admin/visibility`)
      - *Configuration & Branding*: Website General Settings, Office & Contact Settings, WhatsApp Message Settings, My Profile.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+ / Flask 3.1
- **Database**: SQLite3
- **Authentication**: Werkzeug Security (`scrypt`/`pbkdf2`)
- **Frontend**: HTML5, CSS3, JavaScript (ES6)
- **UI Framework**: Bootstrap 5.3
- **Icons**: Font Awesome 6
- **Typography**: Google Fonts (*Cinzel*, *Montserrat*, *Plus Jakarta Sans*)

---

## 🚀 Quick Setup & Run Instructions

### 1. Clone or Open Workspace
Navigate to the project root directory:
```bash
cd d:\Python_Projects\GRN_Property
```

### 2. (Optional) Create & Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database & Seed Realistic Sample Data
The database schema and sample Pune properties will automatically be created on initial start, or you can run:
```bash
python seed_data.py
```
This sets up:
- **Demonstration Accounts**:
  - **Super Admin**: `admin` / `admin123`
  - **Verified Agent**: `pune_agent` / `agent123` (Rohan Mehta - Elite Realty Channel Partner)
  - **Property Owner**: `property_owner` / `owner123` (Dr. Sunita Kulkarni)
- 10 Realistic properties across Wakad, Baner, Hinjewadi, Balewadi, Pimple Saudagar, Tathawade, Ravet, and Punawale.
- Sample customer leads in various pipeline stages.

### 5. Launch the Web Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

To access the Admin Portal:
```
http://127.0.0.1:5000/admin/login
```

---

## 📁 Project Structure

```
GRN_Property/
│
├── app.py                     # Main Flask Application & Route Handlers
├── config.py                  # Configurations (Secret key, DB path, Uploads, Company info)
├── database.py                # SQLite Database schema, connection factory, and queries
├── seed_data.py               # Pre-populates realistic Pune properties & leads
├── requirements.txt           # Minimal, fast dependencies (Flask, Werkzeug)
├── README.md                  # Comprehensive Documentation & Setup Guide
├── GRN_Property_Database/     # Dedicated persistent database & spreadsheet directory
│   ├── grn_properties.db      # SQLite Database storing properties, users & enquiries
│   ├── GRN_Properties_Master_Data.xlsx # Master Excel Workbook (Properties, Leads, Users)
│   ├── Properties_Export.csv  # Spreadsheet export of all properties
│   ├── Customer_Leads_Export.csv # Spreadsheet export of all customer enquiries
│   └── Users_and_Agents_Export.csv # Spreadsheet export of registered users/agents
├── excel_exporter.py          # Standalone Excel & CSV generator and database exporter
│
├── static/
│   ├── css/
│   │   ├── style.css          # Premium Black & Gold custom styles, animations, luxury typography
│   │   └── admin.css          # Admin portal dark theme stylesheet
│   ├── js/
│   │   ├── main.js            # Client interactivity, filters, WhatsApp links, EMI calculator
│   │   └── admin.js           # Admin dashboard interactions, status updates, notes modals
│   ├── images/
│   │   ├── logo.svg           # GRN PROPERTIES luxury gold/black SVG vector logo
│   │   └── favicon.svg        # Matching gold crest favicon
│   └── uploads/               # Admin uploaded property images
│
└── templates/
    ├── base.html              # Base master template (Nav, Footer, Floating WhatsApp, Modals)
    ├── index.html             # Homepage: Hero, Search Bar, Featured, Pune Locations, Testimonials
    ├── properties.html        # Property listings with full filters (Buy/Rent, Category, Location, BHK)
    ├── property_detail.html   # Comprehensive property detail page (Gallery, Specs, Amenities, EMI, WhatsApp)
    ├── about.html             # About Us: Mission, Values, Pune Channel Partner Expertise
    ├── services.html          # Detailed Services: Buying, Selling, Commercial Leasing, NRI Services
    ├── contact.html           # Contact Page: Lead form, Office details, Google Map
    ├── sell.html              # "Sell / List Your Property" dedicated submission form
    ├── privacy.html           # Privacy Policy
    ├── terms.html             # Terms & Conditions
    ├── 404.html               # Custom 404 Page
    ├── 500.html               # Custom 500 Page
    │
    └── admin/
        ├── base_admin.html    # Admin master layout
        ├── login.html         # Admin Secure Login
        ├── dashboard.html     # Analytics KPI cards, recent leads, quick actions
        ├── properties.html    # Property inventory table (status toggle, edit, delete)
        ├── property_form.html # Add / Edit property form with multi-image upload
        └── enquiries.html     # Leads & Enquiries CRM pipeline with CSV export
```

---

## 🛡️ Company Information & MahaRERA
- **Company**: GRN PROPERTIES
- **Tagline**: Your Trusted Real Estate Partner
- **Phone**: +91 7499077170
- **WhatsApp**: +91 7499077170
- **Email**: contact@grnproperties.com
- **Office**: Office 405, Platinum Square, Near Balewadi High Street, Baner-Balewadi Road, Pune, Maharashtra 411045
- **MahaRERA**: A52100034982

---

## 🌐 Production Deployment Guide

### Using Gunicorn (Linux/Cloud VPS):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Waitress (Windows Server):
```bash
pip install waitress
waitress-serve --port=5000 app:app
```

