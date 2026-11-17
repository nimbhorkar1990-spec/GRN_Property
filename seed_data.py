import json
import sqlite3
from werkzeug.security import generate_password_hash
from database import init_db, get_db

def seed():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, ('admin', hashed_pw, 'admin@grnproperties.com', 'GRN Admin', 'admin'))
        print("Admin user created (Username: admin, Password: admin123)")

    # Seed sample Agent
    cursor.execute("SELECT id FROM users WHERE username = ?", ('pune_agent',))
    agent_row = cursor.fetchone()
    if not agent_row:
        hashed_pw = generate_password_hash('agent123')
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role, phone, agency_name, rera_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('pune_agent', hashed_pw, 'agent.rohan@eliterealtypune.com', 'Rohan Mehta', 'agent', '+91 98229 88776', 'Elite Realty Channel Partner', 'A52100099882'))
        agent_id = cursor.lastrowid
        print("Sample Agent created (Username: pune_agent, Password: agent123)")
    else:
        agent_id = agent_row['id']

    # Seed sample Property Owner
    cursor.execute("SELECT id FROM users WHERE username = ?", ('property_owner',))
    owner_row = cursor.fetchone()
    if not owner_row:
        hashed_pw = generate_password_hash('owner123')
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('property_owner', hashed_pw, 'sunita.kulkarni@gmail.com', 'Dr. Sunita Kulkarni', 'owner', '+91 98224 55443'))
        owner_id = cursor.lastrowid
        print("Sample Owner created (Username: property_owner, Password: owner123)")
    else:
        owner_id = owner_row['id']

    # Assign some properties and enquiries to agent and owner
    cursor.execute("UPDATE properties SET user_id = ? WHERE id IN (2, 3)", (agent_id,))
    cursor.execute("UPDATE properties SET user_id = ? WHERE id = 4", (owner_id,))
    cursor.execute("UPDATE enquiries SET property_owner_id = ? WHERE property_id IN (2, 3)", (agent_id,))
    cursor.execute("UPDATE enquiries SET property_owner_id = ? WHERE property_id = 4", (owner_id,))

    # Check if properties exist
    cursor.execute("SELECT COUNT(*) as count FROM properties")
    prop_count = cursor.fetchone()['count']
    
    if prop_count == 0:
        properties = [
            {
                "title": "The Grand Sovereign - Ultra Luxury 4 BHK Residence",
                "slug": "the-grand-sovereign-ultra-luxury-4-bhk-balewadi",
                "category": "Luxury Villas",
                "property_type": "Residential",
                "purpose": "Buy",
                "price": 28500000,
                "price_display": "₹2.85 Cr",
                "location": "Balewadi High Street, Pune",
                "sub_location": "Balewadi",
                "address": "Opposite Cummins India, Balewadi High Street Link Road, Pune 411045",
                "configuration": "4 BHK + Maid Room",
                "carpet_area": 2450,
                "super_area": 3180,
                "bedrooms": 4,
                "bathrooms": 5,
                "balconies": 3,
                "possession_status": "Ready to Move",
                "rera_number": "P52100028912",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Experience uncompromised opulence at The Grand Sovereign in Balewadi. Offering an expansive 4 BHK footprint with panoramic skyline views, double-height ceiling living hall, designer Italian marble flooring, and smart home automation. Situated footsteps away from Balewadi High Street cafes and prime corporate hubs.",
                "amenities": json.dumps([
                    "Infinity Lap Pool", "State-of-the-Art Fitness Gym", "Sky Lounge & Cigar Room", 
                    "24/7 Multi-Tier Security", "Dedicated Concierge", "EV Fast Charging Bays", 
                    "Covered Double Parking", "Landscaped Zen Garden", "Clubhouse with Banquet Hall"
                ]),
                "nearby_landmarks": json.dumps([
                    "Balewadi High Street - 2 mins", "Mumbai-Pune Expressway - 8 mins", 
                    "Jupiter Hospital - 10 mins", "Hinjewadi IT Park - 12 mins"
                ])
            },
            {
                "title": "Emerald Palms - Premium 3 BHK Smart Living",
                "slug": "emerald-palms-premium-3-bhk-baner",
                "category": "Apartments and Flats",
                "property_type": "Residential",
                "purpose": "Buy",
                "price": 14500000,
                "price_display": "₹1.45 Cr",
                "location": "Baner, Pune",
                "sub_location": "Baner",
                "address": "Near Pancard Club Road, Baner Hills, Pune 411045",
                "configuration": "3 BHK",
                "carpet_area": 1280,
                "super_area": 1690,
                "bedrooms": 3,
                "bathrooms": 3,
                "balconies": 2,
                "possession_status": "Ready to Move",
                "rera_number": "P52100031890",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Emerald Palms combines serenity with prime urban connectivity. Enjoy breathtaking views of Baner Hill biodiversity park, smart digital locks, modular European kitchen, high-speed fibre connectivity, and extensive lifestyle amenities tailored for modern tech leaders and families.",
                "amenities": json.dumps([
                    "Swimming Pool & Kids Pool", "Fully Equipped Gymnasium", "Jogging & Cycling Track",
                    "Multipurpose Sports Court", "Power Backup 100%", "CCTV Surveillance",
                    "Children's Adventure Play Area", "Party Lawn with BBQ Station"
                ]),
                "nearby_landmarks": json.dumps([
                    "Baner Hill Nature Reserve - 3 mins", "The Orchid Hotel - 5 mins",
                    "Symbiosis International School - 8 mins", "Pune-Bangalore Highway - 4 mins"
                ])
            },
            {
                "title": "Cyber Heights - Grade A Commercial Office Space",
                "slug": "cyber-heights-grade-a-commercial-office-hinjewadi",
                "category": "Office Spaces",
                "property_type": "Commercial",
                "purpose": "Buy",
                "price": 22000000,
                "price_display": "₹2.20 Cr",
                "location": "Hinjewadi Phase 1, Pune",
                "sub_location": "Hinjewadi",
                "address": "Rajiv Gandhi Infotech Park, Phase 1, Hinjewadi, Pune 411057",
                "configuration": "Furnished Grade A Office",
                "carpet_area": 1850,
                "super_area": 2500,
                "bedrooms": 0,
                "bathrooms": 2,
                "balconies": 0,
                "possession_status": "Ready to Move",
                "rera_number": "P52100040112",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Premium commercial office setup in the epicenter of Hinjewadi Phase 1 IT hub. Features 35 ergonomic workstations, 2 director cabins, high-tech boardroom with video conference support, cafeteria, and private server room. Outstanding rental yield of 8.2% with verified blue-chip tenant interest.",
                "amenities": json.dumps([
                    "High-Speed Passenger Elevators", "100% DG Power Backup", "Multi-Level Basement Parking",
                    "Central VRV Air Conditioning", "Fire Sprinkler & Smoke Detection", "Cafeteria & Food Court",
                    "High-Bandwidth Dual Fiber Mesh", "Access Controlled Turnstiles"
                ]),
                "nearby_landmarks": json.dumps([
                    "Infosys Campus Phase 1 - 2 mins", "Wipro Circle - 3 mins",
                    "Hinjewadi Metro Station - 4 mins", "Courtyard by Marriott - 5 mins"
                ])
            },
            {
                "title": "Skyline Serenity - Elegant 2 BHK Luxury Flat",
                "slug": "skyline-serenity-elegant-2-bhk-wakad",
                "category": "Apartments and Flats",
                "property_type": "Residential",
                "purpose": "Buy",
                "price": 8200000,
                "price_display": "₹82 Lakhs",
                "location": "Wakad, Pune",
                "sub_location": "Wakad",
                "address": "Near Bhumkar Chowk, Datta Mandir Road, Wakad, Pune 411057",
                "configuration": "2 BHK",
                "carpet_area": 840,
                "super_area": 1120,
                "bedrooms": 2,
                "bathrooms": 2,
                "balconies": 2,
                "possession_status": "Ready to Move",
                "rera_number": "P52100025740",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1560185127-6ed189bf02f4?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Vastu compliant, east-facing 2 BHK flat situated in the heart of Wakad. Features sun-drenched master suite with private balcony, designer sanitary ware, modular kitchen cabinets, and premium vitrified tiles. Perfect choice for IT professionals wanting zero commute time to Hinjewadi.",
                "amenities": json.dumps([
                    "Swimming Pool", "Gymnasium", "Kids Play Park", "Senior Citizen Sitout",
                    "Covered Car Parking", "Rainwater Harvesting", "Intercom Facility"
                ]),
                "nearby_landmarks": json.dumps([
                    "Bhumkar Chowk - 2 mins", "Indira College of Engineering - 5 mins",
                    "Phoenix Mall of the Millennium Wakad - 6 mins", "Aditya Birla Hospital - 10 mins"
                ])
            },
            {
                "title": "Villa Royale - Triplex Independent Luxury Bungalow",
                "slug": "villa-royale-triplex-independent-luxury-bungalow-pimple-saudagar",
                "category": "Bungalows",
                "property_type": "Residential",
                "purpose": "Buy",
                "price": 39500000,
                "price_display": "₹3.95 Cr",
                "location": "Pimple Saudagar, Pune",
                "sub_location": "Pimple Saudagar",
                "address": "Kunal Icon Road, Pimple Saudagar, PCMC, Pune 411027",
                "configuration": "5 BHK Triplex Bungalow",
                "carpet_area": 3800,
                "super_area": 4650,
                "bedrooms": 5,
                "bathrooms": 6,
                "balconies": 4,
                "possession_status": "Ready to Move",
                "rera_number": "P52100018442",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1000&q=80",
                    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "An architectural masterpiece in prestigious Pimple Saudagar. Private elevator, heated private rooftop pool, lush landscaped perimeter lawn, 3-car private garage, home theatre room, and servant quarters. Complete privacy and unmatched craftsmanship for distinguished homeowners.",
                "amenities": json.dumps([
                    "Private Rooftop Swimming Pool", "Internal Private Elevator", "Home Theatre Acoustic Room",
                    "3-Car Covered Port", "Solar Water & Solar Rooftop Array", "Lush Landscaped Lawns",
                    "Full Smart Home Automation", "Perimeter Infrared Security"
                ]),
                "nearby_landmarks": json.dumps([
                    "Linear Garden Pimple Saudagar - 2 mins", "Govind Garden Restaurant - 3 mins",
                    "PK International School - 5 mins", "Aundh Commercial District - 7 mins"
                ])
            },
            {
                "title": "Apex Commercial Square - High Street Retail Showroom",
                "slug": "apex-commercial-square-high-street-retail-tathawade",
                "category": "Shops",
                "property_type": "Commercial",
                "purpose": "Buy",
                "price": 16500000,
                "price_display": "₹1.65 Cr",
                "location": "Tathawade, Pune",
                "sub_location": "Tathawade",
                "address": "Mumbai-Bangalore Highway Service Road, Tathawade, Pune 411033",
                "configuration": "Ground + Mezzanine Retail Shop",
                "carpet_area": 950,
                "super_area": 1400,
                "bedrooms": 0,
                "bathrooms": 1,
                "balconies": 0,
                "possession_status": "Ready to Move",
                "rera_number": "P52100037801",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Highway-frontage premium commercial retail shop with monumental 28-foot glass facade. Unmatched visibility on the prime Pune-Bangalore highway corridor. Excellent for luxury fashion, fine dining restaurant, banks, electronics showroom, or premium medical clinic.",
                "amenities": json.dumps([
                    "Prominent Highway Road Frontage", "Customer Surface Parking", "Mezzanine Floor Capability",
                    "3-Phase Industrial Power Connection", "Fire Safety Compliance", "24/7 Security Patrol"
                ]),
                "nearby_landmarks": json.dumps([
                    "JSPM Tathawade Campus - 3 mins", "Bhumkar Chowk - 5 mins",
                    "Sayaji Hotel - 6 mins", "Wakad Flyover - 7 mins"
                ])
            },
            {
                "title": "Silver Oak Meadows - Gated NA Villa Plot",
                "slug": "silver-oak-meadows-gated-na-villa-plot-punawale",
                "category": "Land and Plots",
                "property_type": "Land",
                "purpose": "Buy",
                "price": 6500000,
                "price_display": "₹65 Lakhs",
                "location": "Punawale, Pune",
                "sub_location": "Punawale",
                "address": "Malwadi Road, Punawale, PCMC, Pune 411033",
                "configuration": "Residential Villa Plot",
                "carpet_area": 2200,
                "super_area": 2200,
                "bedrooms": 0,
                "bathrooms": 0,
                "balconies": 0,
                "possession_status": "Ready for Registration",
                "rera_number": "P52100019230",
                "featured": 0,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Clear Collector-Sanctioned NA (Non-Agricultural) residential villa plot inside a secured gated community. 100% title clear, compound wall demarcated, with underground storm water drainage, electricity feeder line, wide tar roads, and lush tree plantation.",
                "amenities": json.dumps([
                    "Secured Gated Community Entry", "40-Foot Internal Tar Roads", "Underground Electricity Cables",
                    "Dedicated Water Supply Line", "Street Lighting System", "Demarcated Plot Boundaries"
                ]),
                "nearby_landmarks": json.dumps([
                    "Punawale Highway Exit - 4 mins", "Lotus Business School - 6 mins",
                    "Ravet Bridge - 8 mins", "Hinjewadi Flyover - 12 mins"
                ])
            },
            {
                "title": "Celestial Towers - Modern 3 BHK Luxury Haven",
                "slug": "celestial-towers-modern-3-bhk-luxury-ravet",
                "category": "Apartments and Flats",
                "property_type": "Residential",
                "purpose": "Buy",
                "price": 10500000,
                "price_display": "₹1.05 Cr",
                "location": "Ravet, PCMC, Pune",
                "sub_location": "Ravet",
                "address": "Near BRTS Road, Ravet, PCMC, Pune 412101",
                "configuration": "3 BHK Premium",
                "carpet_area": 1150,
                "super_area": 1510,
                "bedrooms": 3,
                "bathrooms": 3,
                "balconies": 2,
                "possession_status": "Dec 2026",
                "rera_number": "P52100034502",
                "featured": 1,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Rising high above Ravet's skyline, Celestial Towers offers premium 3 BHK homes crafted for elevated modern lifestyles. Featuring 3-side open residences with expansive sundecks, podium clubhouse, Olympic-length swimming pool, and easy access to both Expressway and Akurdi Railway station.",
                "amenities": json.dumps([
                    "Podium Clubhouse", "Olympic Size Swimming Pool", "Indoor Badminton Court",
                    "Cricket Practice Pitch", "Electric Car Fast Charge Points", "24/7 CCTV & Guards"
                ]),
                "nearby_landmarks": json.dumps([
                    "Ravet BRTS Terminal - 2 mins", "DY Patil International University - 4 mins",
                    "Mumbai-Pune Expressway Toll - 6 mins", "Sentosa Water Park - 7 mins"
                ])
            },
            {
                "title": "TechVista Executive - Corporate Office Floor for Rent",
                "slug": "techvista-executive-corporate-office-hinjewadi-rent",
                "category": "Commercial Properties",
                "property_type": "Commercial",
                "purpose": "Rent",
                "price": 85000,
                "price_display": "₹85,000 / month",
                "location": "Hinjewadi Phase 2, Pune",
                "sub_location": "Hinjewadi",
                "address": "Tech Park Boulevard, Phase 2, Hinjewadi, Pune 411057",
                "configuration": "Fully Furnished 24-Seat Office",
                "carpet_area": 1200,
                "super_area": 1600,
                "bedrooms": 0,
                "bathrooms": 2,
                "balconies": 0,
                "possession_status": "Immediate",
                "rera_number": "P52100036611",
                "featured": 0,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Plug-and-play modern corporate office space ready for immediate occupation in Hinjewadi Phase 2. Includes 24 plug-and-work cubicles, 2 executive cabins, 1 conference room, reception area, pantry, and high-speed Wi-Fi network routing. Ideal for IT startups and branch consulting offices.",
                "amenities": json.dumps([
                    "Plug-and-Play Furnishing", "100% Power Backup", "Dedicated Reserved Parking",
                    "Cafeteria On Premise", "Biometric Access Control", "24/7 Security"
                ]),
                "nearby_landmarks": json.dumps([
                    "Tech Mahindra Hinjewadi - 3 mins", "TCS Phase 2 - 5 mins",
                    "Megapolis Circle - 7 mins", "Ginger Hotel Hinjewadi - 8 mins"
                ])
            },
            {
                "title": "Kalyani Aura - Elegant 2 BHK Rental Flat",
                "slug": "kalyani-aura-elegant-2-bhk-rental-wakad",
                "category": "Apartments and Flats",
                "property_type": "Residential",
                "purpose": "Rent",
                "price": 32000,
                "price_display": "₹32,000 / month",
                "location": "Wakad, Pune",
                "sub_location": "Wakad",
                "address": "Near Kaspate Vasti, Wakad, Pune 411057",
                "configuration": "2 BHK Semi-Furnished",
                "carpet_area": 890,
                "super_area": 1150,
                "bedrooms": 2,
                "bathrooms": 2,
                "balconies": 2,
                "possession_status": "Immediate",
                "rera_number": "P52100021980",
                "featured": 0,
                "status": "Available",
                "featured_image": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
                "gallery_images": json.dumps([
                    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1000&q=80"
                ]),
                "floor_plan_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=800&q=80",
                "description": "Spacious semi-furnished 2 BHK apartment with modular kitchen, wardrobes, LED lighting, and geysers in Kaspate Vasti, Wakad. Very close to key shopping marts, clinics, schools, and quick transit to Hinjewadi Phase 1.",
                "amenities": json.dumps([
                    "Clubhouse", "Gymnasium", "Children Play Area", "Covered Car Parking",
                    "24/7 Security", "Intercom", "Power Backup for Lifts"
                ]),
                "nearby_landmarks": json.dumps([
                    "Kaspate Vasti Chowk - 2 mins", "EuroSchool Wakad - 4 mins",
                    "Sayaji Hotel - 6 mins", "Wakad Bus Stop - 5 mins"
                ])
            }
        ]

        for p in properties:
            cursor.execute("""
                INSERT INTO properties (
                    title, slug, category, property_type, purpose, price, price_display,
                    location, sub_location, address, configuration, carpet_area, super_area,
                    bedrooms, bathrooms, balconies, possession_status, rera_number,
                    featured, status, featured_image, gallery_images, floor_plan_image,
                    description, amenities, nearby_landmarks
                ) VALUES (
                    :title, :slug, :category, :property_type, :purpose, :price, :price_display,
                    :location, :sub_location, :address, :configuration, :carpet_area, :super_area,
                    :bedrooms, :bathrooms, :balconies, :possession_status, :rera_number,
                    :featured, :status, :featured_image, :gallery_images, :floor_plan_image,
                    :description, :amenities, :nearby_landmarks
                )
            """, p)
        print(f"Seeded {len(properties)} realistic Pune properties.")

    # Check if enquiries exist
    cursor.execute("SELECT COUNT(*) as count FROM enquiries")
    enq_count = cursor.fetchone()['count']
    if enq_count == 0:
        sample_enquiries = [
            {
                "name": "Rajesh Sharma",
                "phone": "+91 98234 56789",
                "email": "rajesh.sharma@techfirm.com",
                "property_id": 1,
                "property_title": "The Grand Sovereign - Ultra Luxury 4 BHK Residence",
                "enquiry_type": "Schedule Site Visit",
                "budget": "₹2.5 Cr - ₹3 Cr",
                "preferred_location": "Balewadi",
                "preferred_date": "2026-11-05 at 11:30 AM",
                "message": "Interested in visiting the 4 BHK sample flat this weekend. Please confirm availability.",
                "status": "Site Visit Scheduled",
                "admin_notes": "Client is VP at Hinjewadi IT company. Confirmed site visit for Saturday morning."
            },
            {
                "name": "Pooja Kulkarni",
                "phone": "+91 97654 32100",
                "email": "pooja.kulkarni@gmail.com",
                "property_id": 2,
                "property_title": "Emerald Palms - Premium 3 BHK Smart Living",
                "enquiry_type": "Property Enquiry",
                "budget": "₹1.3 Cr - ₹1.6 Cr",
                "preferred_location": "Baner",
                "preferred_date": "",
                "message": "Looking for 3 BHK in Baner with possession within 3 months. What is the latest all-inclusive pricing?",
                "status": "In Progress",
                "admin_notes": "Shared cost sheet and floor plan via WhatsApp."
            },
            {
                "name": "Amitabh Deshmukh",
                "phone": "+91 99221 44556",
                "email": "amitabh.d@enterprises.in",
                "property_id": 3,
                "property_title": "Cyber Heights - Grade A Commercial IT Office",
                "enquiry_type": "Property Enquiry",
                "budget": "₹2 Cr - ₹2.5 Cr",
                "preferred_location": "Hinjewadi",
                "preferred_date": "",
                "message": "Need commercial property for company expansion. Want details about rental yields and maintenance charges.",
                "status": "New",
                "admin_notes": ""
            },
            {
                "name": "Vikram Patel",
                "phone": "+91 98901 88776",
                "email": "vikram.patel@consulting.com",
                "property_id": None,
                "property_title": "General Consultation - Wakad / Tathawade",
                "enquiry_type": "General Enquiry",
                "budget": "₹70 Lakhs - ₹90 Lakhs",
                "preferred_location": "Wakad",
                "preferred_date": "",
                "message": "Planning to invest in a 2 BHK near Mumbai-Pune Expressway for good rental income. Please suggest top projects.",
                "status": "New",
                "admin_notes": ""
            }
        ]
        for e in sample_enquiries:
            cursor.execute("""
                INSERT INTO enquiries (
                    name, phone, email, property_id, property_title, enquiry_type,
                    budget, preferred_location, preferred_date, message, status, admin_notes
                ) VALUES (
                    :name, :phone, :email, :property_id, :property_title, :enquiry_type,
                    :budget, :preferred_location, :preferred_date, :message, :status, :admin_notes
                )
            """, e)
        print(f"Seeded {len(sample_enquiries)} sample leads/enquiries.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed()

