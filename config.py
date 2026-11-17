import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'grn-properties-super-secret-key-pune-2026'
    DATABASE_DIR = os.path.join(BASE_DIR, 'GRN_Property_Database')
    os.makedirs(DATABASE_DIR, exist_ok=True)
    DATABASE = os.path.join(DATABASE_DIR, 'grn_properties.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # Company Contact & Branding Information
    COMPANY_NAME = "GRN Properties"
    COMPANY_TAGLINE = "Your Trusted Real Estate Partner"
    COMPANY_PHONE = "+91 7499077170"
    COMPANY_PHONE_RAW = "917499077170"
    COMPANY_WHATSAPP = "+91 7499077170"
    COMPANY_WHATSAPP_RAW = "917499077170"
    DEFAULT_WHATSAPP_MESSAGE = "Hi GRN Properties, I am looking for property consultation in Pune."
    COMPANY_EMAIL = "contact@realestate.com"
    COMPANY_RERA = "MahaRERA Reg. No: A52100034982"
    COMPANY_ADDRESS = "Office 405, Platinum Square, Near Balewadi High Street, Baner-Balewadi Road, Pune, Maharashtra 411045"
    
    # Standard Cities for Real Estate Operations
    CITIES = [
        "Pune",
        "Mumbai",
        "Thane",
        "Navi Mumbai",
        "Nashik",
        "Nagpur",
        "Chhatrapati Sambhajinagar",
        "Kolhapur",
        "Solapur",
        "Bengaluru",
        "Hyderabad",
        "Delhi NCR",
        "Gurgaon",
        "Noida",
        "Ahmedabad",
        "Chennai",
        "Kolkata",
        "Goa"
    ]
    
    # Pune Prime Locations
    PUNE_LOCATIONS = [
        "Wakad",
        "Hinjewadi",
        "Baner",
        "Balewadi",
        "Pimple Saudagar",
        "Tathawade",
        "Ravet",
        "Punawale",
        "PCMC",
        "Pune Central"
    ]

    PROPERTY_CATEGORIES = [
        "Residential Properties",
        "Commercial Properties",
        "Luxury Villas",
        "Apartments and Flats",
        "Bungalows",
        "Land and Plots",
        "Office Spaces",
        "Shops"
    ]

