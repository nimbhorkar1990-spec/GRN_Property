import unittest
import os
import time
from datetime import datetime
import json
from werkzeug.security import generate_password_hash
from app import app
import database as db

class GRNPropertiesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        conn = db.get_db()
        conn.execute("UPDATE users SET listing_limit = -1 WHERE username = 'pune_agent'")
        conn.commit()
        conn.close()
        db.bulk_update_visibility(1, updated_by='admin')
        db._visibility_cache = None

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Real Estate', response.data)
        self.assertIn(b'Find Your Dream Property', response.data)
        self.assertIn(b'Wakad', response.data)

    def test_properties_listing(self):
        response = self.client.get('/properties')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Property Listings', response.data)

    def test_property_filter_buy(self):
        response = self.client.get('/properties?purpose=Buy')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Properties', response.data)

    def test_property_filter_location(self):
        response = self.client.get('/properties?location=Baner')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Baner', response.data)

    def test_property_detail(self):
        # Fetch first available property
        props = db.get_all_properties()
        self.assertGreater(len(props), 0)
        first_prop = props[0]
        response = self.client.get(f"/property/{first_prop['slug']}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(first_prop['title'].encode('utf-8'), response.data)
        self.assertIn(b'Home Loan EMI Estimator', response.data)

    def test_about_page(self):
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'About GRN Properties' in response.data or b'About Real Estate' in response.data or b'About ' in response.data)

    def test_services_page(self):
        response = self.client.get('/services')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Services by' in response.data)

    def test_sell_page(self):
        response = self.client.get('/sell')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'List & Sell Your Property', response.data)

    def test_contact_page(self):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Contact' in response.data)

    def test_enquiry_submission(self):
        form_data = {
            'name': 'Test Lead User',
            'phone': '9876543210',
            'email': 'lead@test.com',
            'property_id': '1',
            'property_title': 'The Grand Sovereign',
            'enquiry_type': 'Property Enquiry',
            'budget': '₹2.5 Cr',
            'preferred_location': 'Balewadi',
            'message': 'Testing automated lead capture'
        }
        response = self.client.post('/enquire', data=form_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Thank you, Test Lead User!', response.data)

        # Verify lead exists in database
        enquiries = db.get_all_enquiries()
        matching = [e for e in enquiries if e['name'] == 'Test Lead User']
        self.assertGreater(len(matching), 0)

    def test_admin_auth_and_dashboard(self):
        # Unauthenticated access should redirect to login
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 302)

        # Login with correct credentials
        login_res = self.client.post('/admin/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Executive Dashboard', login_res.data)

        # Test dashboard stats
        dash_res = self.client.get('/admin/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Properties', dash_res.data)

        # Test admin properties list
        props_res = self.client.get('/admin/properties')
        self.assertEqual(props_res.status_code, 200)
        self.assertIn(b'Property Inventory', props_res.data)

        # Test admin enquiries list
        enq_res = self.client.get('/admin/enquiries')
        self.assertEqual(enq_res.status_code, 200)
        self.assertIn(b'Customer Leads & CRM Pipeline', enq_res.data)

        # Test CSV export
        export_res = self.client.get('/admin/enquiries/export')
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.mimetype, 'text/csv')

    def test_admin_crud_operations(self):
        # Login first
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})

        # 1. Add Property
        add_data = {
            'title': 'Automated Test Luxury Penthouse',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '19500000',
            'price_display': '₹1.95 Cr',
            'location': 'Wakad, Pune',
            'sub_location': 'Wakad',
            'address': 'Dange Chowk, Wakad',
            'configuration': '4 BHK Penthouse',
            'carpet_area': '2100',
            'super_area': '2700',
            'bedrooms': '4',
            'bathrooms': '4',
            'balconies': '3',
            'possession_status': 'Ready to Move',
            'rera_number': 'P52100099999',
            'featured': '1',
            'status': 'Available',
            'description': 'Spectacular automated penthouse test listing.',
            'featured_image_url': 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c',
            'gallery_image_urls': 'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3',
            'floor_plan_image_url': '',
            'amenities': ['Swimming Pool', 'Clubhouse with Banquet Hall'],
            'custom_amenities': 'Private Skydeck',
            'nearby_landmarks': 'Mumbai-Pune Expressway - 5 mins\nPhoenix Mall - 6 mins'
        }
        res_add = self.client.post('/admin/properties/add', data=add_data, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        # Check property exists (default status Under Review)
        added_prop = db.get_property_by_slug('automated-test-luxury-penthouse-wakad')
        self.assertIsNotNone(added_prop)
        self.assertEqual(added_prop['title'], 'Automated Test Luxury Penthouse')
        self.assertEqual(added_prop['status'], 'Under Review')

        # Approve listing
        res_appr = self.client.post(f"/admin/properties/approve/{added_prop['id']}", follow_redirects=True)
        self.assertEqual(res_appr.status_code, 200)
        approved_prop = db.get_property_by_id(added_prop['id'])
        self.assertEqual(approved_prop['status'], 'Active')
        self.assertEqual(approved_prop['rera_locked'], 1)

        # 2. Update Status to Sold
        res_status = self.client.post(f"/admin/properties/status/{added_prop['id']}", data={'status': 'Sold'}, follow_redirects=True)
        self.assertEqual(res_status.status_code, 200)
        updated_prop = db.get_property_by_id(added_prop['id'])
        self.assertEqual(updated_prop['status'], 'Sold')

        # 3. Delete Property
        res_del = self.client.post(f"/admin/properties/delete/{added_prop['id']}", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        deleted_prop = db.get_property_by_id(added_prop['id'])
        self.assertIsNone(deleted_prop)

    def test_enquiry_status_update(self):
        # Login
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})

        # Insert a test enquiry
        enq_id = db.insert_enquiry({
            'name': 'Status Check User',
            'phone': '9811122233',
            'email': 'status@check.com',
            'property_id': None,
            'property_title': 'General Consultation',
            'enquiry_type': 'General Enquiry',
            'budget': '₹1 Cr',
            'preferred_location': 'Hinjewadi',
            'preferred_date': '',
            'message': 'Testing status transition',
            'status': 'New',
            'admin_notes': ''
        })

        # Update status & notes
        res = self.client.post(f"/admin/enquiries/update/{enq_id}", data={
            'status': 'Site Visit Scheduled',
            'admin_notes': 'Confirmed visit for Sunday 11am'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        enq = db.get_enquiry_by_id(enq_id)
        self.assertEqual(enq['status'], 'Site Visit Scheduled')
        self.assertIn('Sunday 11am', enq['admin_notes'])

    def test_agent_workflow(self):
        # 1. Login as Agent
        login_res = self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'AGENT PORTAL', login_res.data)

        # 2. Agent Posts a Property Ad
        import time
        ts = int(time.time() * 1000)
        prop_title = f'Agent Prime 3 BHK Balewadi {ts}'
        prop_data = {
            'title': prop_title,
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '13500000',
            'price_display': '₹1.35 Cr',
            'city': 'Pune',
            'location': 'Balewadi, Pune',
            'sub_location': 'Balewadi',
            'address': 'Balewadi High Street Link',
            'configuration': '3 BHK',
            'carpet_area': '1250',
            'super_area': '1600',
            'bedrooms': '3',
            'bathrooms': '3',
            'balconies': '2',
            'possession_status': 'Ready to Move',
            'rera_number': 'P52100077889',
            'contact_person': 'Rohan Mehta',
            'contact_phone': '+91 98229 88776',
            'status': 'Available',
            'description': 'Direct agent listing with luxury amenities.',
            'featured_image_url': 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c',
            'gallery_image_urls': '',
            'floor_plan_image_url': '',
            'amenities': ['Swimming Pool', 'State-of-the-Art Fitness Gym'],
            'custom_amenities': 'Smart Automation',
            'nearby_landmarks': 'High Street - 2 mins'
        }
        res_post = self.client.post('/dashboard/properties/add', data=prop_data, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b'Under Review', res_post.data)

        # Retrieve the posted property
        posted = db.get_all_properties(filters={'q': prop_title, 'include_all_status': True})[0]
        self.assertIsNotNone(posted)
        self.assertEqual(posted['status'], 'Under Review')

        # Admin approves the listing to make it Active
        db.approve_property(posted['id'])
        self.assertIsNotNone(posted)

        # 3. Customer submits an enquiry for this Agent's property
        enq_res = self.client.post('/enquire', data={
            'name': 'Buyer for Rohan',
            'phone': '9822199887',
            'email': 'buyer@pune.com',
            'property_id': str(posted['id']),
            'property_title': posted['title'],
            'enquiry_type': 'Property Enquiry',
            'budget': '₹1.3 Cr - ₹1.4 Cr',
            'preferred_location': 'Balewadi',
            'message': 'Interested in buying this flat directly through agent Rohan.'
        }, follow_redirects=True)
        self.assertEqual(enq_res.status_code, 200)

        # 4. Check Agent CRM page
        crm_res = self.client.get('/dashboard/crm')
        self.assertEqual(crm_res.status_code, 200)
        self.assertIn(b'Buyer for Rohan', crm_res.data)

        # 5. Agent updates CRM status & notes
        agent_enquiries = db.get_enquiries_by_owner(posted['user_id'])
        matching_enq = [e for e in agent_enquiries if e['name'] == 'Buyer for Rohan'][0]

        update_res = self.client.post(f"/dashboard/crm/update/{matching_enq['id']}", data={
            'status': 'Site Visit Scheduled',
            'admin_notes': 'Spoke on WhatsApp, confirmed Saturday 4 PM visit.'
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)

        # Verify update in DB
        updated_enq = db.get_enquiry_by_id(matching_enq['id'])
        self.assertEqual(updated_enq['status'], 'Site Visit Scheduled')
        self.assertIn('Saturday 4 PM', updated_enq['admin_notes'])

        # 6. Agent exports CRM leads to CSV
        export_res = self.client.get('/dashboard/crm/export')
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.mimetype, 'text/csv')
        self.assertIn(b'Buyer for Rohan', export_res.data)

    def test_registration_workflow(self):
        import time
        ts = int(time.time())
        reg_data = {
            'role': 'owner',
            'full_name': 'Santosh Gaikwad',
            'phone': '9823011223',
            'email': f'santosh_{ts}@gmail.com',
            'username': f'santosh_{ts}',
            'agency_name': '',
            'rera_number': '',
            'password': 'ownerpassword123',
            'confirm_password': 'ownerpassword123'
        }
        res = self.client.post('/register', data=reg_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome, Santosh Gaikwad', res.data)
        self.assertIn(b'Property Owner', res.data)

    def test_excel_master_export(self):
        # 1. Test standalone function
        from excel_exporter import export_all_to_excel
        import openpyxl
        excel_path = export_all_to_excel()
        self.assertTrue(os.path.exists(excel_path))

        # Check sheets in workbook
        wb = openpyxl.load_workbook(excel_path)
        sheet_names = wb.sheetnames
        self.assertIn('Properties', sheet_names)
        self.assertIn('Customer_Leads', sheet_names)
        self.assertIn('Users_and_Agents', sheet_names)
        self.assertGreater(wb['Properties'].max_row, 1)
        wb.close()

        # 2. Test web download endpoint
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        res = self.client.get('/admin/export/excel')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_admin_user_management_and_access_control(self):
        import time
        ts = int(time.time() * 1000)
        agent_uname = f"agent_mgmt_{ts}"

        # 1. Login as Admin and view /admin/users
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        users_page = self.client.get('/admin/users')
        self.assertEqual(users_page.status_code, 200)
        self.assertIn(b'Centralized User & Account Control', users_page.data)
        self.assertIn(b'Managed Accounts', users_page.data)

        # 2. Admin creates a new Agent with quota listing_limit=1
        create_res = self.client.post('/admin/users/create', data={
            'username': agent_uname,
            'password': 'agentPassword123!',
            'full_name': 'Test Managed Agent',
            'email': f'{agent_uname}@punerealty.com',
            'phone': '9988776655',
            'role': 'agent',
            'agency_name': 'Skyline Properties',
            'rera_number': 'A52100099887',
            'status': 'active',
            'listing_limit': 1,
            'upload_limit': 6,
            'can_post_ads': 'on',
            'can_edit_ads': 'on',
            'can_delete_ads': 'on',
            'can_access_crm': 'on',
            'can_export_leads': 'on',
            'notes': 'Trial agent account limited to 1 ad'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b'created successfully', create_res.data)

        # Verify user in database
        agent = db.get_user_by_username(agent_uname)
        self.assertIsNotNone(agent)
        self.assertEqual(agent['role'], 'agent')
        self.assertEqual(agent['listing_limit'], 1)
        self.assertEqual(agent['can_post_ads'], 1)
        self.assertEqual(agent['can_access_crm'], 1)

        # 3. Logout admin and login as newly created agent
        self.client.get('/logout')
        agent_login = self.client.post('/login', data={
            'username': agent_uname,
            'password': 'agentPassword123!'
        }, follow_redirects=True)
        self.assertEqual(agent_login.status_code, 200)
        self.assertIn(b'Welcome, Test Managed Agent', agent_login.data)

        # Check properties page shows quota: 0 / 1 Live Ads
        props_page = self.client.get('/dashboard/properties')
        self.assertEqual(props_page.status_code, 200)
        self.assertIn(b'0 / 1 Live Ads', props_page.data)

        # 4. Agent posts 1st property (Allowed)
        p1_res = self.client.post('/dashboard/properties/add', data={
            'title': f'Managed Agent 2BHK {ts}',
            'category': 'Apartment',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '8500000',
            'price_display': '₹85 Lakhs',
            'location': 'Wakad',
            'sub_location': 'Datta Mandir',
            'address': 'Near Highway, Wakad',
            'configuration': '2 BHK',
            'carpet_area': '820',
            'super_area': '1050',
            'bedrooms': '2',
            'bathrooms': '2',
            'balconies': '1',
            'possession_status': 'Ready to Move',
            'rera_number': 'P52100012345',
            'status': 'Available',
            'description': 'Beautiful apartment with modern amenities.'
        }, follow_redirects=True)
        self.assertEqual(p1_res.status_code, 200)
        self.assertIn(b'Under Review', p1_res.data)

        # Verify count is now 1
        active_count = db.get_user_active_properties_count(agent['id'])
        self.assertEqual(active_count, 1)

        # 5. Agent attempts to post 2nd property -> Blocked by listing limit!
        p2_res = self.client.post('/dashboard/properties/add', data={
            'title': f'Managed Agent 3BHK {ts}',
            'category': 'Apartment',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '13500000',
            'price_display': '₹1.35 Cr',
            'location': 'Baner',
            'sub_location': 'Pan Card Club Road',
            'address': 'Baner hills view',
            'configuration': '3 BHK',
            'carpet_area': '1150',
            'status': 'Available'
        }, follow_redirects=True)
        self.assertIn(b'Listing Limit Reached', p2_res.data)

        # 6. Admin revokes CRM permission and monitors agent
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        
        # Test monitor endpoint
        monitor_res = self.client.get(f'/admin/users/{agent["id"]}/monitor')
        self.assertEqual(monitor_res.status_code, 200)
        self.assertIn(b'Test Managed Agent', monitor_res.data)
        self.assertIn(b'Managed Agent 2BHK', monitor_res.data)

        # Admin edits agent permissions: disable CRM (can_access_crm=0)
        edit_res = self.client.post(f'/admin/users/edit/{agent["id"]}', data={
            'full_name': 'Test Managed Agent Updated',
            'email': agent['email'],
            'phone': agent['phone'],
            'role': 'agent',
            'agency_name': 'Skyline Realty Group',
            'rera_number': 'A52100099887',
            'status': 'active',
            'listing_limit': 1,
            'upload_limit': 6,
            'can_post_ads': 'on',
            'can_edit_ads': 'on',
            'can_delete_ads': 'on',
            # can_access_crm not submitted -> disabled!
            # can_export_leads not submitted -> disabled!
            'notes': 'CRM access revoked by admin'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        # Check DB update
        agent_after_edit = db.get_user_by_id(agent['id'])
        self.assertEqual(agent_after_edit['can_access_crm'], 0)
        self.assertEqual(agent_after_edit['can_export_leads'], 0)

        # 7. Agent logs in again, verifies CRM is denied
        self.client.get('/logout')
        self.client.post('/login', data={'username': agent_uname, 'password': 'agentPassword123!'}, follow_redirects=True)
        crm_denied_res = self.client.get('/dashboard/crm', follow_redirects=True)
        self.assertIn(b'Permission Denied', crm_denied_res.data)

        crm_export_denied = self.client.get('/dashboard/crm/export', follow_redirects=True)
        self.assertIn(b'Permission Denied', crm_export_denied.data)

        # 8. Admin deactivates agent account
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        status_res = self.client.post(f'/admin/users/status/{agent["id"]}', data={'status': 'inactive'}, follow_redirects=True)
        self.assertEqual(status_res.status_code, 200)

        # Agent tries to login while inactive -> Rejected!
        self.client.get('/logout')
        inactive_login = self.client.post('/login', data={'username': agent_uname, 'password': 'agentPassword123!'}, follow_redirects=True)
        self.assertIn(b'deactivated or suspended', inactive_login.data)

        # 9. Super Admin Immunity: Admin cannot delete or deactivate root admin (id=1)
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        del_admin_res = self.client.post('/admin/users/delete/1', follow_redirects=True)
        self.assertIn(b'cannot be deleted', del_admin_res.data)

        deact_admin_res = self.client.post('/admin/users/status/1', data={'status': 'inactive'}, follow_redirects=True)
        self.assertIn(b'cannot be deactivated', deact_admin_res.data)

    def test_multiple_themes_option_for_all_users(self):
        import json

        # 1. Public Visitor: check homepage has theme switcher & theme engine
        home_res = self.client.get('/')
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b'themes.css', home_res.data)
        self.assertIn(b'theme.js', home_res.data)
        self.assertIn(b'Choose Appearance', home_res.data)
        self.assertIn(b'data-theme-value="sapphire-blue"', home_res.data)
        self.assertIn(b'data-theme-value="emerald-green"', home_res.data)
        self.assertIn(b'data-theme-value="amethyst-purple"', home_res.data)
        self.assertIn(b'data-theme-value="executive-light"', home_res.data)
        self.assertIn(b'data-theme-value="midnight-ivory"', home_res.data)

        # 2. Public API endpoint: test theme switching
        resp = self.client.post(
            '/api/set-theme',
            data=json.dumps({'theme': 'midnight-ivory'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['theme'], 'midnight-ivory')

        # Check cookie was set
        cookie_header = resp.headers.get('Set-Cookie', '')
        self.assertIn('grn_theme=midnight-ivory', cookie_header)

        # 3. Invalid theme fallback
        invalid_resp = self.client.post(
            '/api/set-theme',
            data=json.dumps({'theme': 'unsupported-neon'}),
            content_type='application/json'
        )
        self.assertEqual(invalid_resp.status_code, 200)
        self.assertEqual(invalid_resp.get_json()['theme'], 'luxury-gold')

        # 4. Logged-in user theme persistence in DB
        import time
        ts = int(time.time() * 1000)
        test_uname = f"theme_user_{ts}"
        self.client.post('/register', data={
            'role': 'owner',
            'full_name': 'Theme Test Owner',
            'phone': '9876543210',
            'email': f'{test_uname}@gmail.com',
            'username': test_uname,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        # Switch theme while logged in
        theme_resp = self.client.post(
            '/api/set-theme',
            data=json.dumps({'theme': 'emerald-green'}),
            content_type='application/json'
        )
        self.assertEqual(theme_resp.status_code, 200)

        # Verify DB persisted
        user_in_db = db.get_user_by_username(test_uname)
        self.assertEqual(user_in_db['theme_preference'], 'emerald-green')

        # 5. User logs out and logs back in -> theme restored from DB
        self.client.get('/logout')
        login_res = self.client.post('/login', data={
            'username': test_uname,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('user_theme'), 'emerald-green')

        # 6. Check Dashboard and Admin Portal have theme switcher
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'theme-dropdown', dash_res.data)
        self.assertIn(b'theme-float-btn', dash_res.data)

        # Admin login
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        admin_res = self.client.get('/admin/dashboard')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'theme-dropdown', admin_res.data)
        self.assertIn(b'theme-float-btn', admin_res.data)

    def test_city_name_manual_and_autocomplete(self):
        import time
        ts = int(time.time() * 1000)
        # Login as admin
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        
        # Verify add property form has city datalist
        add_form = self.client.get('/admin/properties/add')
        self.assertEqual(add_form.status_code, 200)
        self.assertIn(b'name="city"', add_form.data)
        self.assertIn(b'list="adminCitiesList"', add_form.data)
        self.assertIn(b'<datalist id="adminCitiesList">', add_form.data)
        self.assertIn(b'Mumbai', add_form.data)
        self.assertIn(b'Thane', add_form.data)

        # Submit property with manual custom city "Nashik"
        res = self.client.post('/admin/properties/add', data={
            'title': f'Nashik Vineyard Villa {ts}',
            'category': 'Luxury Villas',
            'property_type': 'Villa',
            'purpose': 'Buy',
            'price': '25000000',
            'price_display': '₹2.5 Cr',
            'city': 'Nashik',
            'location': 'Gangapur Road, Nashik',
            'sub_location': 'Gangapur Road',
            'carpet_area': '3200',
            'description': 'Exclusive vineyard villa in Nashik.',
            'rera_number': 'P51600012345'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check DB
        slug = f'nashik-vineyard-villa-{ts}-gangapur-road'
        prop = db.get_property_by_slug(slug)
        self.assertIsNotNone(prop)
        self.assertEqual(prop['city'], 'Nashik')

        # Approve and verify display on detail page
        db.approve_property(prop['id'])
        detail_res = self.client.get(f'/property/{slug}')
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn(b'Nashik', detail_res.data)

    def test_property_listing_admin_approval_workflow(self):
        import time
        ts = int(time.time() * 1000)
        # 1. Agent submits a new property advertisement
        self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        res_post = self.client.post('/dashboard/properties/add', data={
            'title': f'Pending Approval Flat {ts}',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '7500000',
            'price_display': '₹75 Lakhs',
            'city': 'Pune',
            'location': 'Wakad, Pune',
            'sub_location': 'Wakad',
            'carpet_area': '750',
            'description': 'Affordable 2 BHK flat under review.',
            'rera_number': 'P52100055443'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b'Under Review', res_post.data)

        # Verify DB status is 'Under Review'
        slug = f'pending-approval-flat-{ts}-wakad'
        prop = db.get_property_by_slug(slug)
        self.assertIsNotNone(prop)
        self.assertEqual(prop['status'], 'Under Review')

        # 2. Verify listing is NOT visible on public properties page or detail page
        self.client.get('/logout')
        public_res = self.client.get('/properties')
        self.assertNotIn(prop['title'].encode('utf-8'), public_res.data)
        
        # Public visitor viewing pending ad gets 404
        public_detail = self.client.get(f'/property/{slug}')
        self.assertEqual(public_detail.status_code, 404)

        # 3. Admin dashboard shows Pending Property Approvals section
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        pending_page = self.client.get('/admin/properties/pending')
        self.assertEqual(pending_page.status_code, 200)
        self.assertIn(b'Pending Property Approvals', pending_page.data)
        self.assertIn(prop['title'].encode('utf-8'), pending_page.data)
        self.assertIn(b'Approve', pending_page.data)
        self.assertIn(b'Reject', pending_page.data)

        # 4. Admin Approves the listing
        appr_res = self.client.post(f'/admin/properties/approve/{prop["id"]}', follow_redirects=True)
        self.assertEqual(appr_res.status_code, 200)
        self.assertIn(b'approved and activated', appr_res.data)

        # Verify status changed to 'Active' and now visible publicly
        approved_prop = db.get_property_by_id(prop['id'])
        self.assertEqual(approved_prop['status'], 'Active')
        self.assertEqual(approved_prop['rera_locked'], 1)

        self.client.get('/logout')
        public_detail = self.client.get(f'/property/{slug}')
        self.assertEqual(public_detail.status_code, 200)
        self.assertIn(prop['title'].encode('utf-8'), public_detail.data)

        # 5. Test Rejection flow on another property
        self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        self.client.post('/dashboard/properties/add', data={
            'title': f'Rejected Test Flat {ts}',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '5000000',
            'price_display': '₹50 Lakhs',
            'city': 'Pune',
            'location': 'Hinjewadi, Pune',
            'sub_location': 'Hinjewadi',
            'carpet_area': '550',
            'description': 'Under Review Hinjewadi flat.',
            'rera_number': 'P52100066778'
        }, follow_redirects=True)
        rej_prop = db.get_property_by_slug(f'rejected-test-flat-{ts}-hinjewadi')
        
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        rej_res = self.client.post(f'/admin/properties/reject/{rej_prop["id"]}', data={'rejection_reason': 'Invalid floor plan'}, follow_redirects=True)
        self.assertEqual(rej_res.status_code, 200)
        
        rej_db_prop = db.get_property_by_id(rej_prop['id'])
        self.assertEqual(rej_db_prop['status'], 'Rejected')
        self.assertEqual(rej_db_prop['rejection_reason'], 'Invalid floor plan')

        # Check agent dashboard displays rejection status
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        agent_dash = self.client.get('/dashboard/properties')
        self.assertIn(b'Rejected', agent_dash.data)

        # Clean up test properties
        conn = db.get_db()
        conn.execute("DELETE FROM properties WHERE id IN (?, ?)", (prop['id'], rej_prop['id']))
        conn.commit()
        conn.close()

    def test_maharera_registration_number_lock_after_activation(self):
        import time
        ts = int(time.time() * 1000)
        # Agent posts property
        self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        self.client.post('/dashboard/properties/add', data={
            'title': f'RERA Lock Test Flat {ts}',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '9000000',
            'price_display': '₹90 Lakhs',
            'city': 'Pune',
            'location': 'Baner, Pune',
            'sub_location': 'Baner',
            'carpet_area': '950',
            'description': 'Testing RERA lock mechanism.',
            'rera_number': 'ORIGINAL_RERA_123'
        }, follow_redirects=True)
        slug = f'rera-lock-test-flat-{ts}-baner'
        prop = db.get_property_by_slug(slug)
        self.assertEqual(prop['rera_number'], 'ORIGINAL_RERA_123')
        self.assertEqual(prop['rera_locked'], 0)

        # Before activation: can edit rera_number
        edit_res1 = self.client.post(f'/dashboard/properties/edit/{prop["id"]}', data={
            'title': 'Attempting Title Change',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '9000000',
            'price_display': '₹90 Lakhs',
            'city': 'Pune',
            'location': 'Baner, Pune',
            'sub_location': 'Baner',
            'carpet_area': '950',
            'description': 'Testing RERA update before activation.',
            'rera_number': 'UPDATED_BEFORE_ACT_456'
        }, follow_redirects=True)
        self.assertEqual(edit_res1.status_code, 200)
        prop_updated = db.get_property_by_id(prop['id'])
        self.assertEqual(prop_updated['rera_number'], 'UPDATED_BEFORE_ACT_456')

        # Admin activates the listing
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.client.post(f'/admin/properties/approve/{prop["id"]}', follow_redirects=True)
        prop_active = db.get_property_by_id(prop['id'])
        self.assertEqual(prop_active['status'], 'Active')
        self.assertEqual(prop_active['rera_locked'], 1)

        # After activation: Agent attempts to change rera_number via POST
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        
        # Check form renders rera_number as readonly
        edit_page = self.client.get(f'/dashboard/properties/edit/{prop["id"]}')
        self.assertIn(b'readonly', edit_page.data)
        self.assertIn(b'MahaRERA Registration Number is locked permanently', edit_page.data)

        # Direct POST attempt to tamper with rera_number
        self.client.post(f'/dashboard/properties/edit/{prop["id"]}', data={
            'title': 'Hacked Title',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '9000000',
            'price_display': '₹90 Lakhs',
            'city': 'Pune',
            'location': 'Baner, Pune',
            'sub_location': 'Baner',
            'carpet_area': '950',
            'description': 'Attempting tampering.',
            'rera_number': 'TAMPERED_RERA_999'
        }, follow_redirects=True)

        prop_after_tamper = db.get_property_by_id(prop['id'])
        # Original active MahaRERA number MUST be preserved!
        self.assertEqual(prop_after_tamper['rera_number'], 'UPDATED_BEFORE_ACT_456')

    def test_property_title_non_editable_during_updates(self):
        import time
        ts = int(time.time() * 1000)
        # Admin posts a property
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        original_title = f'Original Eternal Title {ts}'
        self.client.post('/admin/properties/add', data={
            'title': original_title,
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '6000000',
            'price_display': '₹60 Lakhs',
            'city': 'Pune',
            'location': 'Kothrud, Pune',
            'sub_location': 'Kothrud',
            'carpet_area': '650',
            'description': 'Testing title lock.'
        }, follow_redirects=True)
        prop = db.get_all_properties(filters={'q': original_title, 'include_all_status': True})[0]
        self.assertEqual(prop['title'], original_title)

        # Check edit page renders readonly title
        edit_page = self.client.get(f'/admin/properties/edit/{prop["id"]}')
        self.assertIn(b'readonly', edit_page.data)
        self.assertIn(b'Property Title cannot be modified once submitted', edit_page.data)

        # Admin attempts to update property with a new title via POST
        res_edit = self.client.post(f'/admin/properties/edit/{prop["id"]}', data={
            'title': f'Malicious Modified Title {ts}',
            'category': 'Apartments and Flats',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '6500000',
            'price_display': '₹65 Lakhs',
            'city': 'Pune',
            'location': 'Kothrud, Pune',
            'sub_location': 'Kothrud',
            'carpet_area': '700',
            'description': 'Updated description.'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)

        # Verify title remains exactly unchanged in DB
        prop_after_edit = db.get_property_by_id(prop['id'])
        self.assertEqual(prop_after_edit['title'], original_title)
        self.assertEqual(prop_after_edit['carpet_area'], 700) # other details allowed to update

    def test_rebranding_real_estate(self):
        # 1. Homepage branding
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'Real Estate', home.data)

        # 2. Login & Register branding
        login_res = self.client.get('/login')
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Real Estate', login_res.data)

        register_res = self.client.get('/register')
        self.assertEqual(register_res.status_code, 200)
        self.assertIn(b'Real Estate', register_res.data)

        # 3. Admin portal branding
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        admin_res = self.client.get('/admin/dashboard')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'Real Estate', admin_res.data)

    def test_ui_design_and_text_color_correction(self):
        # 1. Admin Property Form - Select Amenities color check
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        admin_prop_form = self.client.get('/admin/properties/add')
        self.assertEqual(admin_prop_form.status_code, 200)
        self.assertIn(b'amenities-section', admin_prop_form.data)
        self.assertIn(b'Select Amenities', admin_prop_form.data)
        self.assertIn(b'color: #000000 !important;', admin_prop_form.data)

        # 2. User Dashboard Property Form - Select Amenities color check
        self.client.get('/logout')
        import time
        ts = int(time.time() * 1000)
        agent_uname = f"agent_ui_{ts}"
        self.client.post('/register', data={
            'username': agent_uname,
            'password': 'password123',
            'confirm_password': 'password123',
            'email': f"{agent_uname}@test.com",
            'full_name': 'UI Agent',
            'phone': '9876543210',
            'role': 'agent'
        }, follow_redirects=True)
        self.client.post('/login', data={'username': agent_uname, 'password': 'password123'}, follow_redirects=True)
        user_prop_form = self.client.get('/dashboard/properties/add')
        self.assertEqual(user_prop_form.status_code, 200)
        self.assertIn(b'amenities-section', user_prop_form.data)
        self.assertIn(b'Select Amenities', user_prop_form.data)
        self.assertIn(b'color: #000000 !important;', user_prop_form.data)

        # 3. Verify no bg-dark or bg-black in templates
        import glob
        html_files = glob.glob('templates/**/*.html', recursive=True)
        for hf in html_files:
            with open(hf, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertNotIn('bg-dark', content, f"Found bg-dark in {hf}")
                self.assertNotIn('bg-black', content, f"Found bg-black in {hf}")

        # 4. Verify themes.css has light theme defaults and black text amenity rules
        with open('static/css/themes.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
            self.assertIn('.amenities-section', css_content)
            self.assertIn('#000000 !important;', css_content)

    def test_feedback_management_and_live_activity(self):
        # A. Database Table enquiry_feedback & Separation
        conn = db.get_db()
        cursor = conn.cursor()

        # Check enquiry_feedback table structure
        cursor.execute("PRAGMA table_info(enquiry_feedback)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_cols = [
            'id', 'client_name', 'client_contact', 'enquiry_datetime',
            'project_name', 'configuration', 'cost', 'carpet', 'possession',
            'website_enquiry_url', 'client_feedback', 'feedback_by_username',
            'feedback_datetime'
        ]
        for col in expected_cols:
            self.assertIn(col, columns, f"Missing column {col} in enquiry_feedback table")

        # Verify separation: enquiries vs enquiry_feedback
        cursor.execute("PRAGMA table_info(enquiries)")
        enquiry_cols = [row[1] for row in cursor.fetchall()]
        self.assertIn('name', enquiry_cols)
        self.assertNotIn('client_feedback', enquiry_cols)

        # Check visitor_sessions, user_activity_logs, system_settings tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('visitor_sessions', 'user_activity_logs', 'system_settings')")
        found_tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('visitor_sessions', found_tables)
        self.assertIn('user_activity_logs', found_tables)
        self.assertIn('system_settings', found_tables)
        conn.close()

        # B. Admin Feedback Management Flow
        import time
        ts = int(time.time() * 1000)
        admin_client_name = f"Dr. Sameer Joshi {ts}"

        # Login as Admin
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # View Feedback Management Page
        admin_fb_page = self.client.get('/admin/feedback')
        self.assertEqual(admin_fb_page.status_code, 200)
        self.assertIn(b'Enquiry Feedback Management', admin_fb_page.data)
        self.assertIn(b'Client Name', admin_fb_page.data)
        self.assertIn(b'Client Contact', admin_fb_page.data)
        self.assertIn(b'Feedback By', admin_fb_page.data)
        self.assertIn(b'Send Feedback to Email', admin_fb_page.data)

        # Add Feedback as Admin
        fb_post_data = {
            'client_name': admin_client_name,
            'client_contact': '+91 98230 45678',
            'enquiry_datetime': '2026-11-04 11:15:00',
            'project_name': 'Godrej River Royale',
            'configuration': '4 BHK River View',
            'cost': '27500000',
            'carpet': '2150 sq.ft.',
            'possession': 'Dec 2026',
            'website_enquiry_url': 'http://localhost:5000/property/godrej-river-royale',
            'client_feedback': 'Client highly interested in riverside tower. Booked site tour with family.'
        }
        res_add = self.client.post('/admin/feedback/add', data=fb_post_data, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(admin_client_name.encode('utf-8'), res_add.data)

        # Verify database record has all 13 fields correctly stored
        all_fb = db.get_all_feedbacks_for_export()
        matching_fb = [f for f in all_fb if f['client_name'] == admin_client_name]
        self.assertEqual(len(matching_fb), 1)
        fb_item = matching_fb[0]
        fb_id = fb_item['id']
        self.assertEqual(fb_item['client_contact'], '+91 98230 45678')
        self.assertEqual(fb_item['project_name'], 'Godrej River Royale')
        self.assertEqual(fb_item['configuration'], '4 BHK River View')
        self.assertEqual(float(fb_item['cost']), 27500000.0)
        self.assertEqual(fb_item['carpet'], '2150 sq.ft.')
        self.assertEqual(fb_item['possession'], 'Dec 2026')
        self.assertEqual(fb_item['feedback_by_username'], 'admin')
        self.assertIsNotNone(fb_item['feedback_datetime'])

        # Edit Feedback
        edit_data = dict(fb_post_data)
        edit_data['client_feedback'] = 'Client completed site tour. Requested floor plan and customized payment milestone.'
        edit_data['cost'] = '27000000'
        res_edit = self.client.post(f'/admin/feedback/edit/{fb_id}', data=edit_data, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        updated_item = db.get_feedback_by_id(fb_id)
        self.assertIn('customized payment milestone', updated_item['client_feedback'])
        self.assertEqual(float(updated_item['cost']), 27000000.0)

        # Search Feedback
        res_search = self.client.get(f'/admin/feedback?q={ts}')
        self.assertIn(admin_client_name.encode('utf-8'), res_search.data)

        res_search_empty = self.client.get('/admin/feedback?q=NonExistentClientXYZ99999')
        self.assertNotIn(admin_client_name.encode('utf-8'), res_search_empty.data)

        # Filter by Project
        res_filt_proj = self.client.get('/admin/feedback?project=Godrej+River+Royale')
        self.assertIn(admin_client_name.encode('utf-8'), res_filt_proj.data)

        # Filter by User
        res_filt_user = self.client.get('/admin/feedback?user=admin')
        self.assertIn(admin_client_name.encode('utf-8'), res_filt_user.data)

        # Export Feedback Excel (.xlsx)
        res_export = self.client.get('/admin/feedback/export')
        self.assertEqual(res_export.status_code, 200)
        self.assertEqual(res_export.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment;', res_export.headers.get('Content-Disposition', ''))

        # Configure Admin Email Setting & Send Feedback to Email
        self.client.post('/admin/settings/email', data={'admin_email': 'testadmin@grnproperties.com'}, follow_redirects=True)
        saved_email = db.get_setting('admin_email')
        self.assertEqual(saved_email, 'testadmin@grnproperties.com')

        res_send_email = self.client.post('/admin/feedback/email', data={'admin_email': 'testadmin@grnproperties.com'}, follow_redirects=True)
        self.assertEqual(res_send_email.status_code, 200)
        self.assertIn(b'Feedback Excel report', res_send_email.data)

        # C. Agent / Owner Feedback Portal & Permissions
        self.client.get('/admin/logout')
        import time
        ts = int(time.time() * 1000)
        agent_fb_uname = f"agent_fb_{ts}"
        self.client.post('/register', data={
            'username': agent_fb_uname,
            'password': 'password123',
            'confirm_password': 'password123',
            'email': f"{agent_fb_uname}@test.com",
            'full_name': 'Feedback Agent',
            'phone': '9812345678',
            'role': 'agent'
        }, follow_redirects=True)

        self.client.post('/login', data={'username': agent_fb_uname, 'password': 'password123'}, follow_redirects=True)

        # Agent accesses Feedback Management
        res_agent_fb = self.client.get('/dashboard/feedback')
        self.assertEqual(res_agent_fb.status_code, 200)
        self.assertIn(b'Client Enquiry Feedback Management', res_agent_fb.data)

        # Agent adds feedback
        agent_client_name = f"Sunil Mehra {ts}"
        agent_fb_data = {
            'client_name': agent_client_name,
            'client_contact': '+91 99887 66554',
            'enquiry_datetime': '2026-11-04 15:45:00',
            'project_name': 'VTP Sierra',
            'configuration': '2 BHK Comfort',
            'cost': '8200000',
            'carpet': '780 sq.ft.',
            'possession': 'Ready Possession',
            'website_enquiry_url': 'http://localhost:5000/property/vtp-sierra',
            'client_feedback': 'Agent direct site visit completed with buyer Sunil Mehra.'
        }
        res_agent_add = self.client.post('/dashboard/feedback/add', data=agent_fb_data, follow_redirects=True)
        self.assertEqual(res_agent_add.status_code, 200)
        self.assertIn(agent_client_name.encode('utf-8'), res_agent_add.data)

        # Check that feedback_by_username was captured as the logged-in agent
        agent_items = [f for f in db.get_all_feedbacks_for_export() if f['client_name'] == agent_client_name]
        self.assertEqual(len(agent_items), 1)
        self.assertEqual(agent_items[0]['feedback_by_username'], agent_fb_uname)

        # Agent exports feedback
        res_agent_export = self.client.get('/dashboard/feedback/export')
        self.assertEqual(res_agent_export.status_code, 200)
        self.assertEqual(res_agent_export.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # D. Permission Enforcement Test
        # Admin revokes feedback permission
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        agent_user = db.get_user_by_username(agent_fb_uname)
        conn = db.get_db()
        conn.execute("UPDATE users SET can_manage_feedback = 0 WHERE id = ?", (agent_user['id'],))
        conn.commit()
        conn.close()

        # Agent tries to access /dashboard/feedback
        self.client.get('/admin/logout')
        self.client.post('/login', data={'username': agent_fb_uname, 'password': 'password123'}, follow_redirects=True)
        res_restricted = self.client.get('/dashboard/feedback', follow_redirects=True)
        self.assertIn(b'You do not have permission to access the Feedback Management module', res_restricted.data)

        # E. Live User Activity Dashboard & API
        self.client.get('/logout')
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Admin views dashboard with live telemetry section
        admin_dash = self.client.get('/admin/dashboard')
        self.assertEqual(admin_dash.status_code, 200)
        self.assertIn(b'Live Website &amp; User Activity', admin_dash.data)
        self.assertIn(b'LIVE TELEMETRY', admin_dash.data)
        self.assertIn(b'stat_active_visitors', admin_dash.data)
        self.assertIn(b'stat_active_users', admin_dash.data)
        self.assertIn(b'activityLogTableBody', admin_dash.data)

        # Test Live Activity JSON Endpoint
        res_api = self.client.get('/admin/api/live-activity')
        self.assertEqual(res_api.status_code, 200)
        api_data = res_api.get_json()
        self.assertEqual(api_data['status'], 'success')
        self.assertIn('live_stats', api_data)
        self.assertIn('recent_activities', api_data)

        live_stats = api_data['live_stats']
        self.assertIn('active_visitors', live_stats)
        self.assertIn('active_users', live_stats)
        self.assertIn('active_agents', live_stats)
        self.assertIn('active_owners', live_stats)
        self.assertIn('active_admins', live_stats)
        self.assertIn('total_visitors', live_stats)
        self.assertIn('total_registered_users', live_stats)
        self.assertIn('total_agents', live_stats)
        self.assertIn('total_owners', live_stats)
        self.assertIn('total_admins', live_stats)
        self.assertIn('total_login_sessions', live_stats)

        # Verify recent activity logs contain login actions
        recent_acts = api_data['recent_activities']
        self.assertIsInstance(recent_acts, list)
        self.assertGreater(len(recent_acts), 0)
        login_types = [a['activity_type'] for a in recent_acts]
        self.assertIn('Login', login_types)

        # Clean up test feedback records
        db.delete_feedback(fb_id)
        if agent_items:
            db.delete_feedback(agent_items[0]['id'])

    def test_lead_source_synchronization(self):
        import time
        ts = int(time.time() * 1000)

        # 1. Verify default lead sources exist in database
        active_sources = db.get_active_lead_sources()
        source_names = [s['source_name'] for s in active_sources]
        self.assertIn('Website Direct', source_names)
        self.assertIn('WhatsApp Campaign', source_names)
        self.assertIn('MagicBricks', source_names)

        # 2. Login as admin
        self.client.get('/admin/logout')
        login_res = self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 3. Check that /admin/enquiries and /admin/feedback render the unified lead sources
        res_enq = self.client.get('/admin/enquiries')
        self.assertEqual(res_enq.status_code, 200)
        self.assertIn(b'Website Direct', res_enq.data)
        self.assertIn(b'Lead Source Settings', res_enq.data)

        res_fb = self.client.get('/admin/feedback')
        self.assertEqual(res_fb.status_code, 200)
        self.assertIn(b'Website Direct', res_fb.data)
        self.assertIn(b'Lead Source Settings', res_fb.data)

        # 4. Admin adds a new CRM Lead Source
        new_source_name = f"Podcast Ads {ts}"
        res_add_src = self.client.post('/admin/crm/lead-sources/add', data={
            'source_name': new_source_name,
            'description': 'Audio sponsorship campaign',
            'display_order': 20,
            'is_active': '1'
        }, follow_redirects=True)
        self.assertEqual(res_add_src.status_code, 200)
        self.assertIn(b"added successfully and synchronized with Enquiry Feedback", res_add_src.data)
        self.assertIn(new_source_name.encode('utf-8'), res_add_src.data)

        # Fetch created source
        src_record = db.get_lead_source_by_name(new_source_name)
        self.assertIsNotNone(src_record)
        src_id = src_record['id']

        # 5. Verify the new lead source automatically reflects in BOTH CRM Leads and Enquiry Feedback
        # Check /admin/enquiries
        res_enq_check = self.client.get('/admin/enquiries')
        self.assertIn(new_source_name.encode('utf-8'), res_enq_check.data)

        # Check /admin/feedback
        res_fb_check = self.client.get('/admin/feedback')
        self.assertIn(new_source_name.encode('utf-8'), res_fb_check.data)

        # Check API
        res_api_src = self.client.get('/admin/api/lead-sources')
        self.assertEqual(res_api_src.status_code, 200)
        api_names = [s['source_name'] for s in res_api_src.get_json()['sources']]
        self.assertIn(new_source_name, api_names)

        # 6. Admin adds an Enquiry Feedback record selecting the new source
        fb_data = {
            'client_name': f'Rajesh Bansal {ts}',
            'client_contact': '+91 98221 00000',
            'enquiry_datetime': '2026-11-05 10:00:00',
            'enquiry_source': new_source_name,
            'project_name': 'Lodha Belmondo',
            'configuration': '3 BHK Luxury',
            'cost': '18500000',
            'carpet': '1450 sq ft',
            'possession': 'Ready to Move',
            'website_enquiry_url': 'https://realestate.com/lodha-belmondo',
            'client_feedback': 'Interested in river-view golf villa units.'
        }
        res_add_fb = self.client.post('/admin/feedback/add', data=fb_data, follow_redirects=True)
        self.assertEqual(res_add_fb.status_code, 200)

        # Verify feedback in database
        feedbacks = [f for f in db.get_all_feedbacks_for_export() if f['client_name'] == f'Rajesh Bansal {ts}']
        self.assertEqual(len(feedbacks), 1)
        fb_item = feedbacks[0]
        self.assertEqual(fb_item['enquiry_source'], new_source_name)

        # 7. Add a CRM Lead with the same source
        enq_id = db.insert_enquiry({
            'name': f'Sanjay Gupta {ts}',
            'phone': '9811122233',
            'email': 'sanjay@test.com',
            'property_id': 1,
            'property_title': 'Lodha Belmondo',
            'enquiry_type': 'Property Enquiry',
            'lead_source': new_source_name,
            'budget': '₹1.8 Cr',
            'preferred_location': 'Balewadi',
            'preferred_date': '2026-11-10',
            'message': 'Looking for immediate purchase',
            'status': 'New',
            'admin_notes': ''
        })
        enq_record = db.get_enquiry_by_id(enq_id)
        self.assertEqual(enq_record['lead_source'], new_source_name)

        # 8. Admin renames the CRM Lead Source
        updated_source_name = f"Podcast & Audio Ads {ts}"
        res_edit_src = self.client.post(f'/admin/crm/lead-sources/edit/{src_id}', data={
            'source_name': updated_source_name,
            'description': 'Updated audio campaign',
            'display_order': 20,
            'is_active': '1'
        }, follow_redirects=True)
        self.assertEqual(res_edit_src.status_code, 200)

        # Verify synchronized cascade across CRM Leads and Feedback records
        updated_fb = db.get_feedback_by_id(fb_item['id'])
        self.assertEqual(updated_fb['enquiry_source'], updated_source_name)

        updated_enq = db.get_enquiry_by_id(enq_id)
        self.assertEqual(updated_enq['lead_source'], updated_source_name)

        # 9. Test filtering feedback by source
        import urllib.parse
        encoded_src = urllib.parse.quote_plus(updated_source_name)
        res_filter_fb = self.client.get(f'/admin/feedback?source={encoded_src}')
        self.assertEqual(res_filter_fb.status_code, 200)
        self.assertIn(f'Rajesh Bansal {ts}'.encode('utf-8'), res_filter_fb.data)

        # 10. Test exporting feedback filtered by source
        res_export_fb = self.client.get(f'/admin/feedback/export?source={encoded_src}')
        self.assertEqual(res_export_fb.status_code, 200)
        self.assertEqual(res_export_fb.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # 11. Delete the lead source
        res_del_src = self.client.post(f'/admin/crm/lead-sources/delete/{src_id}', follow_redirects=True)
        self.assertEqual(res_del_src.status_code, 200)

        # Clean up test feedback and enquiry
        db.delete_feedback(fb_item['id'])
        db.delete_enquiry(enq_id)

    def test_feedback_refresh_enquiries(self):
        """Test the Refresh / Reload Enquiries button and database synchronization."""
        import time
        ts = int(time.time() * 1000)

        # 1. Login as Admin
        self.client.get('/admin/logout')
        login_res = self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 2. Check that Refresh Enquiries button is present in Feedback UI
        res_fb_page = self.client.get('/admin/feedback')
        self.assertEqual(res_fb_page.status_code, 200)
        self.assertIn(b'Refresh Enquiries', res_fb_page.data)
        self.assertIn(b'btnRefreshEnquiries', res_fb_page.data)

        # 3. Synchronize existing state
        res_initial_sync = self.client.post('/admin/feedback/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_initial_sync.status_code, 200)
        json_init = res_initial_sync.get_json()
        self.assertTrue(json_init['success'])

        # 4. Immediate second click: must prevent duplicates and report "No New Enquiries Found."
        res_second_sync = self.client.post('/admin/feedback/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_second_sync.status_code, 200)
        json_second = res_second_sync.get_json()
        self.assertTrue(json_second['success'])
        self.assertEqual(json_second['count'], 0)
        self.assertEqual(json_second['message'], 'No New Enquiries Found.')

        # 5. Customer submits a new enquiry on the website
        customer_name = f"Pooja Sharma {ts}"
        customer_phone = "9833445566"
        form_data = {
            'name': customer_name,
            'phone': customer_phone,
            'email': f'pooja_{ts}@gmail.com',
            'property_id': '1',
            'property_title': 'The Grand Sovereign - Ultra Luxury 4 BHK Residence',
            'enquiry_type': 'Property Enquiry',
            'budget': '₹2.85 Cr',
            'preferred_location': 'Balewadi',
            'message': 'Interested in buying high-floor unit.'
        }
        res_enq = self.client.post('/enquire', data=form_data, follow_redirects=True)
        self.assertEqual(res_enq.status_code, 200)

        # Verify enquiry was saved in website enquiries table
        all_enqs = db.get_all_enquiries()
        matching_enq = [e for e in all_enqs if e['name'] == customer_name]
        self.assertEqual(len(matching_enq), 1)
        enq_obj = matching_enq[0]
        self.assertEqual(enq_obj['phone'], customer_phone)

        # Remove from feedback to verify that "Refresh Enquiries" imports missing CRM enquiries
        conn = db.get_db()
        conn.execute("DELETE FROM enquiry_feedback WHERE enquiry_id = ?", (enq_obj['id'],))
        conn.commit()
        conn.close()

        # 6. Admin clicks "Refresh Enquiries"
        res_refresh = self.client.post('/admin/feedback/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_refresh.status_code, 200)
        json_refresh = res_refresh.get_json()
        self.assertTrue(json_refresh['success'])
        self.assertGreaterEqual(json_refresh['count'], 1)
        self.assertIn("Successfully refreshed!", json_refresh['message'])

        # 7. Verify the new enquiry is now automatically in enquiry_feedback with all required details
        feedbacks = [f for f in db.get_all_feedbacks_for_export() if f['client_name'] == customer_name]
        self.assertEqual(len(feedbacks), 1)
        fb_record = feedbacks[0]
        self.assertEqual(fb_record['client_contact'], customer_phone)
        self.assertEqual(fb_record['project_name'], 'The Grand Sovereign - Ultra Luxury 4 BHK Residence')
        self.assertEqual(fb_record['enquiry_source'], 'Website Direct')
        self.assertEqual(fb_record['enquiry_id'], enq_obj['id'])
        self.assertGreater(float(fb_record['cost']), 0)
        self.assertIn('sq ft', fb_record['carpet'])
        self.assertTrue(fb_record['configuration'])
        self.assertTrue(fb_record['possession'])

        # 8. Repeated Refresh click: Must prevent duplicates
        res_repeat = self.client.post('/admin/feedback/refresh', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_repeat.status_code, 200)
        json_repeat = res_repeat.get_json()
        self.assertEqual(json_repeat['count'], 0)
        self.assertEqual(json_repeat['message'], 'No New Enquiries Found.')

        # Ensure still only 1 record exists in feedback
        feedbacks_after = [f for f in db.get_all_feedbacks_for_export() if f['client_name'] == customer_name]
        self.assertEqual(len(feedbacks_after), 1)

        # 9. Verify User/Agent portal displays Refresh Enquiries button
        res_user_fb = self.client.get('/dashboard/feedback')
        self.assertEqual(res_user_fb.status_code, 200)
        self.assertIn(b'Refresh Enquiries', res_user_fb.data)
        self.assertIn(b'btnUserRefreshEnquiries', res_user_fb.data)

        # 10. Clean up created test records
        db.delete_feedback(fb_record['id'])
        db.delete_enquiry(enq_obj['id'])

    def test_website_visibility_management(self):
        """Test complete website menu & function visibility management from Admin Dashboard."""
        # 1. Reset all visibility items to active state for test isolation
        db.bulk_update_visibility(1, updated_by='admin')
        stats = db.get_visibility_stats()
        self.assertGreaterEqual(stats['total'], 50)
        self.assertEqual(stats['hidden'], 0)
        self.assertTrue(db.is_item_visible('nav_about'))
        self.assertTrue(db.is_item_visible('page_about'))

        # 2. Unauthenticated access to /admin/visibility must redirect to login
        res_unauth = self.client.get('/admin/visibility')
        self.assertEqual(res_unauth.status_code, 302)

        # 3. Admin logs in and accesses /admin/visibility
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        res_admin_vis = self.client.get('/admin/visibility')
        self.assertEqual(res_admin_vis.status_code, 200)
        self.assertIn(b'Website Visibility Management', res_admin_vis.data)
        self.assertIn(b'Header Navigation', res_admin_vis.data)
        self.assertIn(b'Main Pages', res_admin_vis.data)
        self.assertIn(b'Homepage Sections', res_admin_vis.data)

        # 4. Toggle OFF nav_about and page_about via AJAX
        res_toggle_nav = self.client.post('/admin/visibility/toggle', json={
            'item_key': 'nav_about',
            'is_visible': 0
        })
        self.assertEqual(res_toggle_nav.status_code, 200)
        self.assertFalse(db.is_item_visible('nav_about'))

        res_toggle_page = self.client.post('/admin/visibility/toggle', json={
            'item_key': 'page_about',
            'is_visible': 0
        })
        self.assertEqual(res_toggle_page.status_code, 200)
        self.assertFalse(db.is_item_visible('page_about'))

        # 5. Public visitor accesses homepage: nav_about link should be hidden
        public_client = app.test_client()
        res_home = public_client.get('/')
        self.assertEqual(res_home.status_code, 200)
        # Verify 'About Us' is not in navigation header
        self.assertNotIn(b'<a class="nav-link " href="/about">About Us</a>', res_home.data)

        # 6. Public visitor directly navigates to /about: Must receive 503 Page Temporarily Unavailable
        res_direct_about = public_client.get('/about')
        self.assertEqual(res_direct_about.status_code, 503)
        self.assertIn(b'Page Temporarily Unavailable', res_direct_about.data)

        # 7. Admin directly navigates to /about: Must be allowed in Admin Preview Mode
        res_admin_about = self.client.get('/about')
        self.assertEqual(res_admin_about.status_code, 200)
        self.assertIn(b'Admin Preview Mode', res_admin_about.data)
        self.assertTrue(b'About GRN Properties' in res_admin_about.data or b'About Real Estate' in res_admin_about.data or b'About ' in res_admin_about.data)

        # 8. Test form visibility restriction: Toggle OFF form_schedule_visit
        self.client.post('/admin/visibility/toggle', json={
            'item_key': 'form_schedule_visit',
            'is_visible': 0
        })
        self.assertFalse(db.is_item_visible('form_schedule_visit'))

        # Public visitor attempts to submit schedule visit enquiry
        res_blocked_form = public_client.post('/enquire', data={
            'name': 'Intruder Lead',
            'phone': '9988776655',
            'enquiry_type': 'Schedule Site Visit'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_blocked_form.status_code, 403)
        self.assertIn(b'currently disabled', res_blocked_form.data)

        # 9. Test Bulk Enable All
        res_bulk_enable = self.client.post('/admin/visibility/bulk', data={
            'action': 'enable_all',
            'category': 'All'
        }, follow_redirects=True)
        self.assertEqual(res_bulk_enable.status_code, 200)

        # Verify all are back ON
        self.assertTrue(db.is_item_visible('nav_about'))
        self.assertTrue(db.is_item_visible('page_about'))
        self.assertTrue(db.is_item_visible('form_schedule_visit'))

        # Public visitor visits /about again: should be 200 OK
        res_restored_about = public_client.get('/about')
        self.assertEqual(res_restored_about.status_code, 200)
        self.assertTrue(b'About GRN Properties' in res_restored_about.data or b'About Real Estate' in res_restored_about.data or b'About ' in res_restored_about.data)

        # 10. Test dynamic addition of new visibility setting item
        res_add_item = self.client.post('/admin/visibility/add', data={
            'item_key': 'nav_investors',
            'name': 'Investor Relations',
            'category': 'Header Navigation',
            'url_path': '/investors',
            'description': 'Investor relations and annual reports menu',
            'is_visible': '1'
        }, follow_redirects=True)
        self.assertEqual(res_add_item.status_code, 200)
        self.assertTrue(db.is_item_visible('nav_investors'))

        # Clean up added test key
        conn = db.get_db()
        conn.execute("DELETE FROM website_visibility WHERE item_key = 'nav_investors'")
        conn.commit()
        conn.close()
        db._visibility_cache = None

        # Ensure all settings are enabled
        db.bulk_update_visibility(1, category=None, updated_by='admin')

    def test_website_enquiry_url_and_lead_feedback_sync(self):
        """
        Verify:
        Task 1: Add 'Website Enquiry URL' column in Lead CRM with database storage, auto-capturing, UI link, and CSV export.
        Task 2: Complete data synchronization between Lead CRM and Feedback module (shared IDs, instant auto-sync, update sync, no duplicates, safe deletion).
        """
        # 1. Admin login
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 2. Submit new enquiry with explicit website_enquiry_url
        test_url = "http://localhost:5000/property/panchshil-towers-kharadi"
        unique_phone = "98234" + str(int(time.time()))[-5:]
        res_submit = self.client.post('/enquire', data={
            'name': 'Rajesh Sharma',
            'phone': unique_phone,
            'email': 'rajesh@example.com',
            'property_title': 'Panchshil Towers Penthouse',
            'enquiry_type': 'Property Enquiry',
            'lead_source': 'Website Direct',
            'website_enquiry_url': test_url,
            'budget': '3.5 Cr',
            'preferred_location': 'Kharadi',
            'message': 'Interested in penthouse floor plan and site visit.'
        }, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)

        # 3. Verify enquiry record stored in database with website_enquiry_url
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enquiries WHERE phone = ? ORDER BY id DESC LIMIT 1", (unique_phone,))
        enq = cursor.fetchone()
        self.assertIsNotNone(enq)
        enq_id = enq['id']
        self.assertEqual(enq['website_enquiry_url'], test_url)
        self.assertEqual(enq['name'], 'Rajesh Sharma')

        # 4. Verify Task 2: Instant automatic synchronization into Feedback module!
        cursor.execute("SELECT * FROM enquiry_feedback WHERE enquiry_id = ?", (enq_id,))
        fb = cursor.fetchone()
        self.assertIsNotNone(fb, "Newly submitted website enquiry must be immediately available in Feedback!")
        self.assertEqual(fb['client_name'], 'Rajesh Sharma')
        self.assertEqual(fb['client_contact'], unique_phone)
        self.assertEqual(fb['enquiry_source'], 'Website Direct')
        self.assertEqual(fb['website_enquiry_url'], test_url)
        self.assertEqual(fb['project_name'], 'Panchshil Towers Penthouse')
        self.assertAlmostEqual(fb['cost'], 35000000.0)
        self.assertEqual(fb['feedback_by_username'], 'Website Direct')
        fb_id = fb['id']

        # 5. Verify Lead CRM UI displays Website Enquiry URL and Lead ID
        res_leads_ui = self.client.get('/admin/enquiries')
        self.assertEqual(res_leads_ui.status_code, 200)
        self.assertIn(b'Website Enquiry URL', res_leads_ui.data)
        self.assertIn(f'Lead #{enq_id}'.encode(), res_leads_ui.data)
        self.assertIn(test_url.encode(), res_leads_ui.data)

        # 6. Verify Lead CRM Export includes Website Enquiry URL
        res_export = self.client.get('/admin/enquiries/export')
        self.assertEqual(res_export.status_code, 200)
        self.assertIn(b'Website Enquiry URL', res_export.data)
        self.assertIn(test_url.encode(), res_export.data)

        # 7. Verify Task 2: Updating Lead Source in CRM synchronizes to Feedback module
        res_update = self.client.post(f'/admin/enquiries/update/{enq_id}', data={
            'status': 'In Progress',
            'lead_source': 'Google Search / Ads',
            'admin_notes': 'Spoke with customer; interested in 4 BHK'
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)

        # Check updated values in both modules
        cursor.execute("SELECT lead_source, status FROM enquiries WHERE id = ?", (enq_id,))
        updated_enq = cursor.fetchone()
        self.assertEqual(updated_enq['lead_source'], 'Google Search / Ads')

        cursor.execute("SELECT enquiry_source FROM enquiry_feedback WHERE id = ?", (fb_id,))
        updated_fb = cursor.fetchone()
        self.assertEqual(updated_fb['enquiry_source'], 'Google Search / Ads')

        # 8. Verify Feedback UI displays Lead #ID and clickable Website Enquiry URL
        res_fb_ui = self.client.get('/admin/feedback')
        self.assertEqual(res_fb_ui.status_code, 200)
        self.assertIn(f'Lead #{enq_id}'.encode(), res_fb_ui.data)
        self.assertIn(test_url.encode(), res_fb_ui.data)

        # 9. Test Refresh Enquiries idempotency (no duplicates generated)
        cursor.execute("SELECT COUNT(*) as cnt FROM enquiry_feedback")
        before_cnt = cursor.fetchone()['cnt']

        res_refresh = self.client.post('/admin/feedback/refresh', follow_redirects=True)
        self.assertEqual(res_refresh.status_code, 200)

        cursor.execute("SELECT COUNT(*) as cnt FROM enquiry_feedback")
        after_cnt = cursor.fetchone()['cnt']
        self.assertEqual(before_cnt, after_cnt, "Refresh Enquiries must not create duplicate feedback records!")

        # 10. Verify Safe Deletion: Deleting feedback does NOT delete the CRM lead
        res_del_fb = self.client.post(f'/admin/feedback/delete/{fb_id}', follow_redirects=True)
        self.assertEqual(res_del_fb.status_code, 200)

        # Verify feedback record is deleted
        cursor.execute("SELECT * FROM enquiry_feedback WHERE id = ?", (fb_id,))
        self.assertIsNone(cursor.fetchone())

        # Verify original CRM lead is STILL intact
        cursor.execute("SELECT * FROM enquiries WHERE id = ?", (enq_id,))
        self.assertIsNotNone(cursor.fetchone(), "Deleting feedback must NEVER delete the original CRM enquiry!")

        # 11. Clean up test lead
        db.delete_enquiry(enq_id)
        conn.close()

    def test_admin_settings_security_and_access(self):
        """Verify only authenticated Admin users can access settings; visitors and agents are blocked."""
        # 1. Unauthenticated visitor access
        visitor_client = app.test_client()
        res_vis_gen = visitor_client.get('/admin/settings?tab=general')
        self.assertEqual(res_vis_gen.status_code, 302)
        self.assertIn('/admin/login', res_vis_gen.headers.get('Location', ''))

        res_vis_wa = visitor_client.get('/admin/settings?tab=whatsapp')
        self.assertEqual(res_vis_wa.status_code, 302)
        self.assertIn('/admin/login', res_vis_wa.headers.get('Location', ''))

        # 2. Agent login and access attempt
        agent_client = app.test_client()
        agent_client.post('/login', data={'username': 'pune_agent', 'password': 'agent123'}, follow_redirects=True)
        res_agent_attempt = agent_client.get('/admin/settings')
        self.assertEqual(res_agent_attempt.status_code, 302)
        self.assertIn('/admin/login', res_agent_attempt.headers.get('Location', ''))

        # 3. Authorized Admin login
        admin_client = app.test_client()
        res_admin_login = admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)

        # 4. Access Settings Tabs
        res_general = admin_client.get('/admin/settings?tab=general')
        self.assertEqual(res_general.status_code, 200)
        self.assertIn(b'Website General Settings', res_general.data)
        self.assertIn(b'Project / Website Name', res_general.data)

        res_whatsapp = admin_client.get('/admin/settings?tab=whatsapp')
        self.assertEqual(res_whatsapp.status_code, 200)
        self.assertIn(b'WhatsApp Message Settings', res_whatsapp.data)
        self.assertIn(b'Default WhatsApp Contact Message', res_whatsapp.data)

    def test_whatsapp_message_management(self):
        """Test Admin updating WhatsApp default message, public propagation, blank validation, and reset."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Update WhatsApp message
        test_msg = "Hello Pune Realty! I would like to schedule a site visit this weekend."
        res_update = admin_client.post('/admin/settings/whatsapp', data={
            'action': 'save',
            'whatsapp_message': test_msg
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(db.get_whatsapp_message(), test_msg)

        # 2. Verify new message appears in WhatsApp links for all website visitors
        public_client = app.test_client()
        res_home = public_client.get('/')
        self.assertEqual(res_home.status_code, 200)
        # Verify URL-encoded message is present in floating button and sticky bar
        from urllib.parse import quote
        encoded_test_msg = quote(test_msg)
        self.assertIn(encoded_test_msg.encode(), res_home.data)

        # Verify on /contact page
        res_contact = public_client.get('/contact')
        self.assertEqual(res_contact.status_code, 200)
        self.assertIn(encoded_test_msg.encode(), res_contact.data)

        # 3. Test blank message validation: Should fail and keep previous message
        res_blank = admin_client.post('/admin/settings/whatsapp', data={
            'action': 'save',
            'whatsapp_message': '   '
        }, follow_redirects=True)
        self.assertIn(b'cannot be blank', res_blank.data)
        self.assertEqual(db.get_whatsapp_message(), test_msg)

        # 4. Test Reset to Default
        res_reset = admin_client.post('/admin/settings/whatsapp', data={
            'action': 'reset'
        }, follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertIn(b'reset to system default', res_reset.data)
        current_site_name = db.get_website_name()
        expected_default = f"Hi {current_site_name}, I am looking for property consultation in Pune."
        self.assertEqual(db.get_whatsapp_message(), expected_default)

    def test_whatsapp_dynamic_message_configuration(self):
        """Test full 4-field WhatsApp Message Configuration: Default greeting, Listing Title, Listing URL, and Additional Message."""
        from urllib.parse import quote

        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Update all 4 WhatsApp configuration fields
        custom_default = "Hello Pune Realty, I am interested in property consultation."
        custom_title_fmt = "Property / Listing Name: {{listing_title}}."
        custom_url_fmt = "Property Details Link: {{listing_url}}"
        custom_additional = "Please share the complete property details, pricing, location and site visit availability."

        res_update = admin_client.post('/admin/settings/whatsapp', data={
            'action': 'save',
            'whatsapp_default_message': custom_default,
            'whatsapp_listing_title_format': custom_title_fmt,
            'whatsapp_listing_url_format': custom_url_fmt,
            'whatsapp_additional_message': custom_additional
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)

        # Verify database
        cfg = db.get_all_whatsapp_settings()
        self.assertEqual(cfg['default_message'], custom_default)
        self.assertEqual(cfg['listing_title_format'], custom_title_fmt)
        self.assertEqual(cfg['listing_url_format'], custom_url_fmt)
        self.assertEqual(cfg['additional_message'], custom_additional)

        public_client = app.test_client()

        # 2. General website contact button: Default + Additional (NO Listing Title or URL)
        res_home = public_client.get('/')
        self.assertEqual(res_home.status_code, 200)
        expected_general_msg = f"{custom_default}\n\n{custom_additional}"
        self.assertIn(quote(expected_general_msg).encode(), res_home.data)
        self.assertNotIn(b'Property / Listing Name:', res_home.data)
        self.assertNotIn(b'Property Details Link:', res_home.data)

        # 3. Property Detail Page: Default + Listing Title + Listing URL + Additional
        props = db.get_all_properties()
        self.assertGreater(len(props), 1)
        prop_a = props[0]
        prop_b = props[1]

        # Test Property A
        res_prop_a = public_client.get(f"/property/{prop_a['slug']}")
        self.assertEqual(res_prop_a.status_code, 200)
        expected_url_a = f"http://localhost/property/{prop_a['slug']}"
        expected_prop_msg_a = (
            f"{custom_default}\n\n"
            f"Property / Listing Name: {prop_a['title']}.\n\n"
            f"Property Details Link: {expected_url_a}\n\n"
            f"{custom_additional}"
        )
        self.assertIn(quote(expected_prop_msg_a).encode(), res_prop_a.data)

        # Test Property B (verify dynamic title & URL are correct per property and no cross-contamination)
        res_prop_b = public_client.get(f"/property/{prop_b['slug']}")
        self.assertEqual(res_prop_b.status_code, 200)
        expected_url_b = f"http://localhost/property/{prop_b['slug']}"
        expected_prop_msg_b = (
            f"{custom_default}\n\n"
            f"Property / Listing Name: {prop_b['title']}.\n\n"
            f"Property Details Link: {expected_url_b}\n\n"
            f"{custom_additional}"
        )
        self.assertIn(quote(expected_prop_msg_b).encode(), res_prop_b.data)
        # Verify Property B does NOT have Property A's URL or title in its WhatsApp link
        self.assertNotIn(quote(expected_url_a).encode(), res_prop_b.data)

        # 4. Test with Additional Message left blank
        res_blank_add = admin_client.post('/admin/settings/whatsapp', data={
            'action': 'save',
            'whatsapp_default_message': custom_default,
            'whatsapp_listing_title_format': custom_title_fmt,
            'whatsapp_listing_url_format': custom_url_fmt,
            'whatsapp_additional_message': '   '
        }, follow_redirects=True)
        self.assertEqual(res_blank_add.status_code, 200)
        self.assertEqual(db.get_whatsapp_additional_message(), '')

        # Property page without additional message (no trailing empty lines)
        res_prop_no_add = public_client.get(f"/property/{prop_a['slug']}")
        expected_prop_msg_no_add = (
            f"{custom_default}\n\n"
            f"Property / Listing Name: {prop_a['title']}.\n\n"
            f"Property Details Link: {expected_url_a}"
        )
        self.assertIn(quote(expected_prop_msg_no_add).encode(), res_prop_no_add.data)

        # General page without additional message
        res_home_no_add = public_client.get('/')
        self.assertIn(quote(custom_default).encode(), res_home_no_add.data)

        # 5. Test Reset to Default
        res_reset = admin_client.post('/admin/settings/whatsapp', data={'action': 'reset'}, follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        cfg_reset = db.get_all_whatsapp_settings()
        self.assertEqual(cfg_reset['listing_title_format'], "Property / Listing Name: {{listing_title}}.")
        self.assertEqual(cfg_reset['listing_url_format'], "Property Details Link: {{listing_url}}")
        self.assertEqual(cfg_reset['additional_message'], "Please share the complete property details, pricing, location and site visit availability.")

    def test_website_name_management(self):
        """Test Admin updating website name, propagation to titles/footers/headers/WhatsApp, validation, and reset."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Update Project / Website Name to custom name
        new_site_name = "Apex Prime Realty"
        res_update = admin_client.post('/admin/settings/general', data={
            'action': 'save',
            'website_name': new_site_name
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(db.get_website_name(), new_site_name)

        # 2. Verify dynamic reflection across public website
        public_client = app.test_client()

        # Homepage: Title, Header, Footer
        res_home = public_client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(new_site_name.encode(), res_home.data)
        self.assertIn(f"<title>{new_site_name}".encode(), res_home.data)

        # About Us page
        res_about = public_client.get('/about')
        self.assertEqual(res_about.status_code, 200)
        self.assertIn(f"About {new_site_name}".encode(), res_about.data)

        # Contact page
        res_contact = public_client.get('/contact')
        self.assertEqual(res_contact.status_code, 200)
        self.assertIn(f"Contact {new_site_name}".encode(), res_contact.data)

        # Admin portal branding
        res_admin = admin_client.get('/admin/dashboard')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(new_site_name.encode(), res_admin.data)

        # WhatsApp default message synchronized with website name
        self.assertIn(new_site_name, db.get_whatsapp_message())

        # 3. Test blank name validation: Should fail and retain current name
        res_blank = admin_client.post('/admin/settings/general', data={
            'action': 'save',
            'website_name': '   '
        }, follow_redirects=True)
        self.assertIn(b'cannot be blank', res_blank.data)
        self.assertEqual(db.get_website_name(), new_site_name)

        # 4. Test Reset to Default
        res_reset = admin_client.post('/admin/settings/general', data={
            'action': 'reset'
        }, follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertIn(b'reset to default (GRN Properties)', res_reset.data)
        self.assertEqual(db.get_website_name(), "GRN Properties")

        # Public verification after reset
        res_home_reset = public_client.get('/')
        self.assertIn(b'GRN Properties', res_home_reset.data)

    def test_office_contact_settings_security(self):
        """Test authentication and authorization for Office & Contact settings."""
        # Unauthenticated guest
        guest_client = app.test_client()
        res_get = guest_client.get('/admin/settings?tab=contact')
        self.assertEqual(res_get.status_code, 302)
        res_post = guest_client.post('/admin/settings/contact', data={'action': 'save'})
        self.assertEqual(res_post.status_code, 302)

        # Authenticated as regular agent (not admin)
        agent_client = app.test_client()
        agent_client.post('/login', data={'username': 'pune_agent', 'password': 'password123'}, follow_redirects=True)
        res_agent_get = agent_client.get('/admin/settings?tab=contact')
        self.assertEqual(res_agent_get.status_code, 302)

    def test_office_contact_settings_update(self):
        """Test updating all Office & Contact fields and dynamic reflection across website."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        update_payload = {
            'action': 'save',
            'corporate_office': 'Tower B, Level 15, Cybercity Magarpatta, Pune 411028',
            'is_enabled_corporate_office': '1',
            'order_corporate_office': '10',
            'label_corporate_office': 'Corporate Office',
            'company_phone': '+91 9123456789',
            'is_enabled_company_phone': '1',
            'order_company_phone': '20',
            'label_company_phone': 'Call Us',
            'company_whatsapp': '+91 9988776655',
            'is_enabled_company_whatsapp': '1',
            'order_company_whatsapp': '30',
            'label_company_whatsapp': 'WhatsApp Desk',
            'company_email': 'concierge@grnproperty.com',
            'is_enabled_company_email': '1',
            'order_company_email': '40',
            'label_company_email': 'Email Address',
            'company_rera': 'A52100099999',
            'is_enabled_company_rera': '1',
            'order_company_rera': '50',
            'label_company_rera': 'MahaRERA Reg. No.',
            'branch_office': 'Solitaire Business Hub, Viman Nagar, Pune',
            'is_enabled_branch_office': '1',
            'order_branch_office': '60',
            'label_branch_office': 'Branch Office',
            'working_hours': 'Monday - Sunday: 9:00 AM - 8:00 PM',
            'is_enabled_working_hours': '1',
            'order_working_hours': '70',
            'label_working_hours': 'Working Hours',
            'google_maps_url': 'https://maps.google.com/?q=Cybercity+Pune',
            'is_enabled_google_maps_url': '1',
            'order_google_maps_url': '80',
            'label_google_maps_url': 'Google Maps Location'
        }

        res = admin_client.post('/admin/settings/contact', data=update_payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated successfully', res.data)

        # Verify database
        cd = db.get_contact_settings_dict()
        self.assertEqual(cd['corporate_office']['value'], 'Tower B, Level 15, Cybercity Magarpatta, Pune 411028')
        self.assertEqual(cd['company_phone']['value'], '+91 9123456789')
        self.assertEqual(cd['company_whatsapp']['value'], '+91 9988776655')
        self.assertEqual(cd['company_email']['value'], 'concierge@grnproperty.com')
        self.assertEqual(cd['company_rera']['value'], 'A52100099999')
        self.assertEqual(cd['branch_office']['value'], 'Solitaire Business Hub, Viman Nagar, Pune')
        self.assertEqual(cd['working_hours']['value'], 'Monday - Sunday: 9:00 AM - 8:00 PM')
        self.assertEqual(cd['google_maps_url']['value'], 'https://maps.google.com/?q=Cybercity+Pune')

        # Public verification
        public_client = app.test_client()

        # Contact Page verification
        res_contact = public_client.get('/contact')
        self.assertEqual(res_contact.status_code, 200)
        self.assertIn(b'Tower B, Level 15, Cybercity Magarpatta, Pune 411028', res_contact.data)
        self.assertIn(b'tel:919123456789', res_contact.data)
        self.assertIn(b'919988776655', res_contact.data)
        self.assertIn(b'mailto:concierge@grnproperty.com', res_contact.data)
        self.assertIn(b'A52100099999', res_contact.data)
        self.assertIn(b'Solitaire Business Hub, Viman Nagar, Pune', res_contact.data)
        self.assertIn(b'Monday - Sunday: 9:00 AM - 8:00 PM', res_contact.data)
        self.assertIn(b'https://maps.google.com/?q=Cybercity+Pune', res_contact.data)

        # Homepage & Footer verification
        res_home = public_client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b'+91 9123456789', res_home.data)
        self.assertIn(b'919988776655', res_home.data)
        self.assertIn(b'concierge@grnproperty.com', res_home.data)
        self.assertIn(b'A52100099999', res_home.data)
        self.assertIn(b'Solitaire Business Hub', res_home.data)
        self.assertIn(b'Monday - Sunday: 9:00 AM - 8:00 PM', res_home.data)

    def test_office_contact_settings_disable_fields(self):
        """Test disabling optional fields hides them from the public website."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Disable branch_office, company_rera, working_hours, and google_maps_url
        disable_payload = {
            'action': 'save',
            'corporate_office': 'Tower B, Level 15, Cybercity Magarpatta, Pune 411028',
            'is_enabled_corporate_office': '1',
            'company_phone': '+91 9123456789',
            'is_enabled_company_phone': '1',
            'company_whatsapp': '+91 9988776655',
            'is_enabled_company_whatsapp': '1',
            'company_email': 'concierge@grnproperty.com',
            'is_enabled_company_email': '1',
            'company_rera': 'A52100099999',
            # is_enabled_company_rera omitted -> disabled
            'branch_office': 'Hidden Branch Office Suite',
            # is_enabled_branch_office omitted -> disabled
            'working_hours': 'Hidden Timings 10:00 to 18:00',
            # is_enabled_working_hours omitted -> disabled
            'google_maps_url': 'https://maps.google.com/?q=Hidden',
            # is_enabled_google_maps_url omitted -> disabled
        }
        res = admin_client.post('/admin/settings/contact', data=disable_payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        public_client = app.test_client()
        res_contact = public_client.get('/contact')
        self.assertNotIn(b'Hidden Branch Office Suite', res_contact.data)
        self.assertNotIn(b'Hidden Timings 10:00 to 18:00', res_contact.data)
        self.assertNotIn(b'Find Our Office on Map', res_contact.data)

        # Footer also hides disabled fields
        res_home = public_client.get('/')
        self.assertNotIn(b'Hidden Branch Office Suite', res_home.data)
        self.assertNotIn(b'Hidden Timings 10:00 to 18:00', res_home.data)

    def test_office_contact_custom_fields(self):
        """Test adding, viewing, and deleting custom contact fields."""
        conn = db.get_db()
        conn.execute("DELETE FROM contact_settings WHERE is_custom = 1")
        conn.commit()
        conn.close()

        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Add custom contact info
        add_payload = {
            'action': 'add_custom',
            'new_label': 'NRI Investor Helpdesk',
            'new_value': '+91 9800011122',
            'new_icon': 'fas fa-globe',
            'new_link_type': 'tel',
            'new_order': '15',
            'new_enabled': '1'
        }
        res_add = admin_client.post('/admin/settings/contact', data=add_payload, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b'NRI Investor Helpdesk', res_add.data)

        # Verify on public Contact page and Footer
        public_client = app.test_client()
        res_contact = public_client.get('/contact')
        self.assertIn(b'NRI Investor Helpdesk', res_contact.data)
        self.assertIn(b'tel:919800011122', res_contact.data)

        res_home = public_client.get('/')
        self.assertIn(b'NRI Investor Helpdesk', res_home.data)

        # 2. Delete the custom contact field
        cd = db.get_contact_settings_dict()
        custom_key = None
        for k, v in cd.items():
            if v.get('label') == 'NRI Investor Helpdesk':
                custom_key = k
                break
        self.assertIsNotNone(custom_key)

        res_del = admin_client.get(f'/admin/settings/contact/custom/delete/{custom_key}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertIn(b'deleted successfully', res_del.data)

        # Verify removal
        res_contact_after = public_client.get('/contact')
        self.assertNotIn(b'NRI Investor Helpdesk', res_contact_after.data)

    def test_office_contact_validation(self):
        """Test validation rules for corporate office, phone, and email."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Blank Corporate Office
        res_corp = admin_client.post('/admin/settings/contact', data={
            'action': 'save',
            'corporate_office': '   ',
            'company_phone': '+91 7499077170',
            'company_whatsapp': '+91 7499077170',
            'company_email': 'info@grnproperties.com'
        }, follow_redirects=True)
        self.assertIn(b'Corporate Office address cannot be blank', res_corp.data)

        # Invalid Email
        res_email = admin_client.post('/admin/settings/contact', data={
            'action': 'save',
            'corporate_office': 'Valid Address',
            'company_phone': '+91 7499077170',
            'company_whatsapp': '+91 7499077170',
            'company_email': 'invalid-email-address'
        }, follow_redirects=True)
        self.assertIn(b'valid official email address', res_email.data)

        # Invalid Phone
        res_phone = admin_client.post('/admin/settings/contact', data={
            'action': 'save',
            'corporate_office': 'Valid Address',
            'company_phone': '123',
            'company_whatsapp': '+91 7499077170',
            'company_email': 'info@grnproperties.com'
        }, follow_redirects=True)
        self.assertIn(b'valid company contact phone number', res_phone.data)

    def test_office_contact_reset(self):
        """Test resetting all contact settings back to system defaults."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        res_reset = admin_client.post('/admin/settings/contact', data={'action': 'reset'}, follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertIn(b'reset to system defaults', res_reset.data)

        cd = db.get_contact_settings_dict()
        self.assertEqual(cd['company_phone']['value'], '+91 7499077170')
        self.assertEqual(cd['company_whatsapp']['value'], '+91 7499077170')
        self.assertEqual(cd['company_email']['value'], 'contact@realestate.com')

    def test_admin_profile_security(self):
        """Test authentication and authorization for Admin My Profile."""
        # 1. Unauthenticated access
        guest_client = app.test_client()
        res_get = guest_client.get('/admin/profile')
        self.assertEqual(res_get.status_code, 302)
        self.assertIn('/admin/login', res_get.headers.get('Location', ''))

        res_post = guest_client.post('/admin/profile', data={'action': 'update_profile'})
        self.assertEqual(res_post.status_code, 302)

        # 2. Non-admin agent user access attempt
        agent_client = app.test_client()
        agent_client.post('/login', data={'username': 'pune_agent', 'password': 'password123'}, follow_redirects=True)
        res_agent = agent_client.get('/admin/profile')
        self.assertEqual(res_agent.status_code, 302)
        self.assertIn('/admin/login', res_agent.headers.get('Location', ''))

    def test_admin_profile_view_and_update(self):
        """Test viewing and updating Admin profile information at any time."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. View My Profile page
        res_view = admin_client.get('/admin/profile')
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b'Administrator Profile', res_view.data)
        self.assertIn(b'Super Administrator', res_view.data)

        # 2. Update profile information
        update_data = {
            'action': 'update_profile',
            'full_name': 'Rajeshwar Patil',
            'email': 'rajeshwar.patil@grnproperties.com',
            'phone': '+91 9822334455',
            'agency_name': 'GRN Apex Corporate Desk',
            'rera_number': 'A52100088888',
            'notes': 'Senior Director of Real Estate Advisory'
        }
        res_save = admin_client.post('/admin/profile', data=update_data, follow_redirects=True)
        self.assertEqual(res_save.status_code, 200)
        self.assertIn(b'Admin profile information has been updated successfully', res_save.data)

        # Verify database record
        admin_row = db.get_user_by_username('admin')
        self.assertEqual(admin_row['full_name'], 'Rajeshwar Patil')
        self.assertEqual(admin_row['email'], 'rajeshwar.patil@grnproperties.com')
        self.assertEqual(admin_row['phone'], '+91 9822334455')
        self.assertEqual(admin_row['agency_name'], 'GRN Apex Corporate Desk')
        self.assertEqual(admin_row['rera_number'], 'A52100088888')
        self.assertEqual(admin_row['notes'], 'Senior Director of Real Estate Advisory')

        # Verify updated name appears in header/dropdown
        res_dash = admin_client.get('/admin/dashboard')
        self.assertIn(b'Rajeshwar Patil', res_dash.data)

    def test_admin_profile_validation(self):
        """Test validation rules for Admin profile fields."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Blank Full Name
        res_blank = admin_client.post('/admin/profile', data={
            'action': 'update_profile',
            'full_name': '   ',
            'email': 'admin@grnproperties.com',
            'phone': '+91 7499077170'
        }, follow_redirects=True)
        self.assertIn(b'cannot be blank', res_blank.data)

        # Invalid Email
        res_email = admin_client.post('/admin/profile', data={
            'action': 'update_profile',
            'full_name': 'Administrator',
            'email': 'invalid-email-address',
            'phone': '+91 7499077170'
        }, follow_redirects=True)
        self.assertIn(b'valid official email address', res_email.data)

        # Invalid Phone
        res_phone = admin_client.post('/admin/profile', data={
            'action': 'update_profile',
            'full_name': 'Administrator',
            'email': 'admin@grnproperties.com',
            'phone': '123'
        }, follow_redirects=True)
        self.assertIn(b'at least 8 digits', res_phone.data)

    def test_admin_profile_password_change(self):
        """Test changing Admin password from My Profile, validation, and login with new password."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        try:
            # 1. Incorrect current password
            res_wrong = admin_client.post('/admin/profile', data={
                'action': 'change_password',
                'current_password': 'wrongpassword',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            }, follow_redirects=True)
            self.assertIn(b'Current password entered is incorrect', res_wrong.data)

            # 2. Mismatched confirmation password
            res_mismatch = admin_client.post('/admin/profile', data={
                'action': 'change_password',
                'current_password': 'admin123',
                'new_password': 'newpassword123',
                'confirm_password': 'differentpassword'
            }, follow_redirects=True)
            self.assertIn(b'do not match', res_mismatch.data)

            # 3. Successful password change
            new_pass = 'AdminSecured#2026'
            res_success = admin_client.post('/admin/profile', data={
                'action': 'change_password',
                'current_password': 'admin123',
                'new_password': new_pass,
                'confirm_password': new_pass
            }, follow_redirects=True)
            self.assertIn(b'password has been changed successfully', res_success.data)

            # 4. Try logging in with old password -> should fail
            test_client = app.test_client()
            res_fail_old = test_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
            self.assertIn(b'Invalid username/email or password', res_fail_old.data)

            # 5. Login with new password -> succeeds
            res_login_new = test_client.post('/admin/login', data={'username': 'admin', 'password': new_pass}, follow_redirects=True)
            self.assertEqual(res_login_new.status_code, 200)
            self.assertIn(b'Executive Dashboard', res_login_new.data)
        finally:
            # Always restore original password 'admin123'
            from werkzeug.security import generate_password_hash
            conn = db.get_db()
            conn.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (generate_password_hash('admin123'),))
            conn.commit()
            conn.close()

    def test_feedback_edit_loading_and_safe_update(self):
        """Test API dynamic loading of feedback enquiry details for edit and safe update without overwriting blank/null."""
        # 1. Unauthenticated API access must be rejected
        anon_client = app.test_client()
        res_unauth = anon_client.get('/api/feedback/1')
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Authenticated Admin gets complete feedback record
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Create a test feedback record with known values
        import time
        ts = int(time.time() * 1000)
        fb_id = db.create_feedback({
            'client_name': f'Kiran Verma {ts}',
            'client_contact': '+91 9888877777',
            'enquiry_datetime': '2026-11-09 14:30:00',
            'enquiry_source': 'Website Direct',
            'project_name': 'Sobha Nesara Luxury',
            'configuration': '3 BHK Penthouse',
            'cost': 35000000,
            'carpet': '2200 sq ft',
            'possession': 'Immediate',
            'website_enquiry_url': 'http://127.0.0.1:5000/property/1',
            'client_feedback': 'Requires top floor unit with 2 reserved covered car parks.',
            'feedback_by_username': 'admin',
            'feedback_datetime': '2026-11-09 14:35:00',
            'role': 'admin'
        })

        try:
            # Fetch via API
            res_api = admin_client.get(f'/api/feedback/{fb_id}')
            self.assertEqual(res_api.status_code, 200)
            data = res_api.get_json()
            self.assertTrue(data['success'])
            fb = data['feedback']
            self.assertEqual(fb['id'], fb_id)
            self.assertEqual(fb['client_name'], f'Kiran Verma {ts}')
            self.assertEqual(fb['client_contact'], '+91 9888877777')
            self.assertEqual(fb['enquiry_datetime'], '2026-11-09 14:30:00')
            self.assertEqual(fb['enquiry_source'], 'Website Direct')
            self.assertEqual(fb['project_name'], 'Sobha Nesara Luxury')
            self.assertEqual(fb['configuration'], '3 BHK Penthouse')
            self.assertEqual(float(fb['cost']), 35000000.0)
            self.assertEqual(fb['carpet'], '2200 sq ft')
            self.assertEqual(fb['possession'], 'Immediate')
            self.assertEqual(fb['website_enquiry_url'], 'http://127.0.0.1:5000/property/1')
            self.assertEqual(fb['client_feedback'], 'Requires top floor unit with 2 reserved covered car parks.')
            self.assertEqual(fb['feedback_by_username'], 'admin')

            # Verify form Edit elements are present in admin feedback page
            res_page = admin_client.get('/admin/feedback')
            self.assertIn(b'editFeedbackModal', res_page.data)
            self.assertIn(b'edit_sn_badge', res_page.data)
            self.assertIn(b'edit_client_name', res_page.data)
            self.assertIn(b'edit_client_contact', res_page.data)
            self.assertIn(b'edit_enquiry_datetime', res_page.data)
            self.assertIn(b'edit_feedback_by_display', res_page.data)

            # Test safe update without wiping blank values: omit configuration, carpet, possession
            res_update = admin_client.post(f'/admin/feedback/edit/{fb_id}', data={
                'client_name': f'Kiran Verma Updated {ts}',
                'client_contact': '+91 9888877777',
                'enquiry_datetime': '2026-11-09 14:30:00',
                'enquiry_source': 'Website Direct',
                'project_name': 'Sobha Nesara Luxury',
                'client_feedback': 'Updated: Price negotiated and token paid.'
            }, follow_redirects=True)
            self.assertEqual(res_update.status_code, 200)

            # Verify in DB: updated fields changed, omitted fields safely retained!
            updated_fb = db.get_feedback_by_id(fb_id)
            self.assertEqual(updated_fb['client_name'], f'Kiran Verma Updated {ts}')
            self.assertIn('token paid', updated_fb['client_feedback'])
            self.assertEqual(updated_fb['configuration'], '3 BHK Penthouse')
            self.assertEqual(updated_fb['carpet'], '2200 sq ft')
            self.assertEqual(updated_fb['possession'], 'Immediate')
        finally:
            db.delete_feedback(fb_id)

    def test_feedback_and_crm_sorting(self):
        """Test Sort By Created Date & Time (Newest First vs Oldest First) in Feedback and Lead CRM."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Test Feedback Sorting
        # Create two test feedbacks with different created date & times
        import time
        ts = int(time.time() * 1000)
        fb_old = db.create_feedback({
            'client_name': f'Old Client {ts}',
            'client_contact': '9111111111',
            'enquiry_datetime': '2026-01-01 10:00:00',
            'feedback_datetime': '2026-01-01 10:00:00',
            'project_name': 'Project Alpha',
            'client_feedback': 'Early initial inquiry',
            'feedback_by_username': 'admin'
        })
        fb_new = db.create_feedback({
            'client_name': f'New Client {ts}',
            'client_contact': '9222222222',
            'enquiry_datetime': '2026-11-10 18:00:00',
            'feedback_datetime': '2026-11-10 18:00:00',
            'project_name': 'Project Beta',
            'client_feedback': 'Latest urgent inquiry',
            'feedback_by_username': 'admin'
        })

        try:
            # Query with sort=newest filtered to our test timestamp
            feedbacks_newest = db.get_all_feedbacks(filters={'search': str(ts)}, sort='newest', per_page=10)
            self.assertEqual(len(feedbacks_newest), 2)
            self.assertEqual(feedbacks_newest[0]['id'], fb_new, "Newest First must have newest feedback first")
            self.assertEqual(feedbacks_newest[1]['id'], fb_old, "Newest First must have older feedback second")

            # Query with sort=oldest filtered to our test timestamp
            feedbacks_oldest = db.get_all_feedbacks(filters={'search': str(ts)}, sort='oldest', per_page=10)
            self.assertEqual(len(feedbacks_oldest), 2)
            self.assertEqual(feedbacks_oldest[0]['id'], fb_old, "Oldest First must have older feedback first")
            self.assertEqual(feedbacks_oldest[1]['id'], fb_new, "Oldest First must have newest feedback second")

            # Verify sorting dropdown is in /admin/feedback and /dashboard/feedback HTML
            res_fb_ui = admin_client.get('/admin/feedback?sort=oldest')
            self.assertIn(b'Sort By Created Date & Time', res_fb_ui.data)
            self.assertIn(b'Newest First', res_fb_ui.data)
            self.assertIn(b'Oldest First', res_fb_ui.data)

            res_user_fb = admin_client.get('/dashboard/feedback?sort=newest')
            self.assertIn(b'Sort By Created Date & Time', res_user_fb.data)
        finally:
            db.delete_feedback(fb_old)
            db.delete_feedback(fb_new)

        # 2. Test Lead CRM Sorting
        # Create two test enquiries with different created_at
        enq_old_data = {
            'name': f'CRM Old Lead {ts}',
            'phone': '9333333333',
            'email': f'old_{ts}@example.com',
            'property_id': 1,
            'property_title': 'The Grand Sovereign',
            'enquiry_type': 'Property Enquiry',
            'lead_source': 'Website Direct',
            'website_enquiry_url': 'http://127.0.0.1:5000/property/1',
            'budget': '₹2.85 Cr',
            'preferred_location': 'Balewadi',
            'preferred_date': '2026-01-05',
            'message': 'Old lead enquiry',
            'status': 'New',
            'admin_notes': ''
        }
        enq_old_id = db.insert_enquiry(enq_old_data)
        conn = db.get_db()
        conn.execute("UPDATE enquiries SET created_at = '2026-01-05 08:30:00' WHERE id = ?", (enq_old_id,))
        conn.commit()
        conn.close()

        enq_new_data = {
            'name': f'CRM New Lead {ts}',
            'phone': '9444444444',
            'email': f'new_{ts}@example.com',
            'property_id': 1,
            'property_title': 'The Grand Sovereign',
            'enquiry_type': 'Property Enquiry',
            'lead_source': 'Website Direct',
            'website_enquiry_url': 'http://127.0.0.1:5000/property/1',
            'budget': '₹2.85 Cr',
            'preferred_location': 'Balewadi',
            'preferred_date': '2026-11-10',
            'message': 'New lead enquiry',
            'status': 'New',
            'admin_notes': ''
        }
        enq_new_id = db.insert_enquiry(enq_new_data)
        conn = db.get_db()
        conn.execute("UPDATE enquiries SET created_at = '2026-11-10 18:15:00' WHERE id = ?", (enq_new_id,))
        conn.commit()
        conn.close()

        try:
            # Query enquiries with sort=newest
            enqs_newest = [e for e in db.get_all_enquiries(sort='newest') if e['id'] in (enq_old_id, enq_new_id)]
            self.assertEqual(len(enqs_newest), 2)
            self.assertEqual(enqs_newest[0]['id'], enq_new_id, "Newest First in CRM must rank newer lead higher")
            self.assertEqual(enqs_newest[1]['id'], enq_old_id, "Newest First in CRM must rank older lead second")

            # Query enquiries with sort=oldest
            enqs_oldest = [e for e in db.get_all_enquiries(sort='oldest') if e['id'] in (enq_old_id, enq_new_id)]
            self.assertEqual(len(enqs_oldest), 2)
            self.assertEqual(enqs_oldest[0]['id'], enq_old_id, "Oldest First in CRM must rank older lead higher")
            self.assertEqual(enqs_oldest[1]['id'], enq_new_id, "Oldest First in CRM must rank newer lead second")

            # Verify sorting dropdown is in /admin/enquiries and /dashboard/crm HTML
            res_crm_admin = admin_client.get('/admin/enquiries?sort=oldest')
            self.assertIn(b'Sort By Created Date & Time', res_crm_admin.data)

            res_crm_user = admin_client.get('/dashboard/crm?sort=newest')
            self.assertIn(b'Sort By Created Date & Time', res_crm_user.data)
        finally:
            db.delete_enquiry(enq_old_id)
            db.delete_enquiry(enq_new_id)

    def test_settings_submenus_structure_and_navigation(self):
        """Test the 5 Settings submenus structure (Pending Approval, Properties, User Management, Feedback, Website Visibility)."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        res_dash = admin_client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Verify all 5 submenus are present in the Settings dropdown
        self.assertIn(b'1. Pending Approval', res_dash.data)
        self.assertIn(b'2. Properties', res_dash.data)
        self.assertIn(b'3. User Management', res_dash.data)
        self.assertIn(b'4. Feedback', res_dash.data)
        self.assertIn(b'5. Website Visibility', res_dash.data)

        # Verify each submenu link resolves with HTTP 200 OK
        res_pending = admin_client.get('/admin/properties/pending')
        self.assertEqual(res_pending.status_code, 200)

        res_props = admin_client.get('/admin/properties')
        self.assertEqual(res_props.status_code, 200)

        res_users = admin_client.get('/admin/users')
        self.assertEqual(res_users.status_code, 200)

        res_fb = admin_client.get('/admin/feedback')
        self.assertEqual(res_fb.status_code, 200)

        res_vis = admin_client.get('/admin/visibility')
        self.assertEqual(res_vis.status_code, 200)

        # Verify Settings page also displays the 5 submenus
        res_settings = admin_client.get('/admin/settings')
        self.assertEqual(res_settings.status_code, 200)
        self.assertIn(b'Settings Submenus', res_settings.data)
        self.assertIn(b'1. Pending Approval', res_settings.data)
        self.assertIn(b'5. Website Visibility', res_settings.data)

    def test_admin_main_menu_duplicates_removed(self):
        """Task 2: Test that duplicate menu options (Pending Approval, Properties, User Management) are removed from the main navbar but remain in Settings."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        res = admin_client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Extract the main navbar list
        import re
        nav_match = re.search(r'<ul class="navbar-nav[^"]*">(.*?)</ul>\s*<div class="d-flex align-items-center gap-3">', html, re.DOTALL)
        self.assertIsNotNone(nav_match, "Main navbar list should exist")
        nav_html = nav_match.group(1)

        # Split navbar top-level items from the Settings dropdown menu
        dropdown_match = re.search(r'<ul class="dropdown-menu[^"]*" aria-labelledby="settingsDropdown"[^>]*>(.*?)</ul>\s*</li>', nav_html, re.DOTALL)
        self.assertIsNotNone(dropdown_match, "Settings dropdown menu should exist inside navbar")
        settings_menu_html = dropdown_match.group(1)

        # Remove the settings dropdown content from nav_html to inspect only top-level navbar items
        top_level_nav = nav_html.replace(settings_menu_html, '')

        # Pending Approval, Properties, and User Management must NOT be top-level navbar links
        self.assertNotIn('/admin/properties/pending', top_level_nav)
        self.assertNotIn('/admin/properties', top_level_nav)
        self.assertNotIn('/admin/users', top_level_nav)

        # But they MUST be present inside the Settings submenu
        self.assertIn('/admin/properties/pending', settings_menu_html)
        self.assertIn('1. Pending Approval', settings_menu_html)
        self.assertIn('/admin/properties', settings_menu_html)
        self.assertIn('2. Properties', settings_menu_html)
        self.assertIn('/admin/users', settings_menu_html)
        self.assertIn('3. User Management', settings_menu_html)

    def test_bulk_delete_enquiries(self):
        """Task 1: Test bulk delete functionality in Leads & Enquiries for Admin and CRM Users, with feedback unlinking."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Create two test enquiry records
        e1_id = db.insert_enquiry({
            'name': 'Bulk Test Client One',
            'phone': '+91 9999900001',
            'email': 'bulk1@example.com',
            'property_id': None,
            'property_title': 'Baner Bulk Project',
            'enquiry_type': 'Buy',
            'budget': '80 Lakhs',
            'preferred_location': 'Baner, Pune',
            'preferred_date': '2026-11-20',
            'message': 'Bulk delete test message 1',
            'lead_source': 'Website Direct',
            'website_enquiry_url': 'http://localhost:5000/property/1',
            'status': 'New'
        })
        e2_id = db.insert_enquiry({
            'name': 'Bulk Test Client Two',
            'phone': '+91 9999900002',
            'email': 'bulk2@example.com',
            'property_id': None,
            'property_title': 'Kothrud Bulk Project',
            'enquiry_type': 'Buy',
            'budget': '1.2 Cr',
            'preferred_location': 'Kothrud, Pune',
            'preferred_date': '2026-11-22',
            'message': 'Bulk delete test message 2',
            'lead_source': 'Meta Ads',
            'website_enquiry_url': 'http://localhost:5000/property/2',
            'status': 'New'
        })

        # 2. Add a feedback record linked to e1
        fb_id = db.create_feedback({
            'client_name': 'Bulk Test Client One',
            'client_contact': '+91 9999900001',
            'enquiry_datetime': '2026-11-10 12:00',
            'enquiry_source': 'Website Direct',
            'project_name': 'Baner Bulk Project',
            'configuration': '2 BHK',
            'cost': 8000000,
            'carpet_area': '750 sq.ft',
            'possession': 'Dec 2026',
            'website_enquiry_url': 'http://localhost:5000/property/1',
            'client_feedback': 'Interested in Baner property',
            'feedback_by_user_id': 1,
            'feedback_by_username': 'admin',
            'enquiry_id': e1_id
        })

        # Verify e1 and e2 exist
        self.assertIsNotNone(db.get_enquiry_by_id(e1_id))
        self.assertIsNotNone(db.get_enquiry_by_id(e2_id))
        fb_rec = db.get_feedback_by_id(fb_id)
        self.assertEqual(fb_rec['enquiry_id'], e1_id)

        # 3. Test bulk deletion via Admin POST
        res = admin_client.post('/admin/enquiries/bulk-delete', data={
            'enquiry_ids': [str(e1_id), str(e2_id)]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Successfully permanently deleted 2 selected enquiry record(s)', res.data)

        # Verify records are deleted
        self.assertIsNone(db.get_enquiry_by_id(e1_id))
        self.assertIsNone(db.get_enquiry_by_id(e2_id))

        # Verify linked feedback was unlinked (enquiry_id = None), NOT deleted
        fb_after = db.get_feedback_by_id(fb_id)
        self.assertIsNotNone(fb_after)
        self.assertIsNone(fb_after['enquiry_id'])

        # Clean up test feedback
        db.delete_feedback(fb_id)

    def test_bulk_delete_feedbacks(self):
        """Task 1: Test bulk delete functionality in Feedback section for Admin and authorized Users."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        fb1_id = db.create_feedback({
            'client_name': 'Feedback Bulk Client 1',
            'client_contact': '+91 9999900011',
            'enquiry_datetime': '2026-11-10 14:00',
            'enquiry_source': 'Walk-in',
            'project_name': 'Hinjewadi IT Towers',
            'configuration': '3 BHK',
            'cost': 11000000,
            'carpet_area': '1050 sq.ft',
            'possession': 'Ready',
            'website_enquiry_url': 'http://localhost:5000/property/3',
            'client_feedback': 'Site visit scheduled for weekend',
            'feedback_by_user_id': 1,
            'feedback_by_username': 'admin'
        })
        fb2_id = db.create_feedback({
            'client_name': 'Feedback Bulk Client 2',
            'client_contact': '+91 9999900012',
            'enquiry_datetime': '2026-11-10 15:00',
            'enquiry_source': 'Referral',
            'project_name': 'Wakad Luxury Residences',
            'configuration': '4 BHK',
            'cost': 22000000,
            'carpet_area': '1800 sq.ft',
            'possession': 'Under Construction',
            'website_enquiry_url': 'http://localhost:5000/property/4',
            'client_feedback': 'Discussing home loan pre-approval',
            'feedback_by_user_id': 1,
            'feedback_by_username': 'admin'
        })

        self.assertIsNotNone(db.get_feedback_by_id(fb1_id))
        self.assertIsNotNone(db.get_feedback_by_id(fb2_id))

        # Delete in bulk
        res = admin_client.post('/admin/feedback/bulk-delete', data={
            'feedback_ids': [str(fb1_id), str(fb2_id)]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Successfully permanently deleted 2 selected feedback record(s)', res.data)

        # Verify records are deleted
        self.assertIsNone(db.get_feedback_by_id(fb1_id))
        self.assertIsNone(db.get_feedback_by_id(fb2_id))

    def test_bulk_delete_ui_and_confirmation_text(self):
        """Task 1: Test that all required UI elements and exact confirmation popup text exist across Leads & Enquiries and Feedback sections."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Admin Enquiries page
        res_enq = admin_client.get('/admin/enquiries')
        self.assertEqual(res_enq.status_code, 200)
        self.assertIn(b'Delete Selected', res_enq.data)
        self.assertIn(b'selectAllEnquiries', res_enq.data)
        self.assertIn(b'Are you sure you want to permanently delete the selected enquiry records?', res_enq.data)
        self.assertIn(b'Confirm Delete', res_enq.data)
        self.assertIn(b'Cancel', res_enq.data)

        # 2. Admin Feedback page
        res_fb = admin_client.get('/admin/feedback')
        self.assertEqual(res_fb.status_code, 200)
        self.assertIn(b'Delete Selected', res_fb.data)
        self.assertIn(b'selectAllFeedback', res_fb.data)
        self.assertIn(b'Are you sure you want to permanently delete the selected enquiry records?', res_fb.data)
        self.assertIn(b'Confirm Delete', res_fb.data)
        self.assertIn(b'Cancel', res_fb.data)

        # 3. User CRM page
        # Register and login user
        client = app.test_client()
        user_reg = client.post('/register', data={
            'username': 'bulkagent1',
            'email': 'bulkagent1@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'full_name': 'Bulk Test Agent',
            'phone': '9876543210'
        }, follow_redirects=True)
        client.post('/login', data={'username': 'bulkagent1', 'password': 'password123'}, follow_redirects=True)

        res_crm = client.get('/dashboard/crm')
        self.assertEqual(res_crm.status_code, 200)
        self.assertIn(b'Delete Selected', res_crm.data)
        self.assertIn(b'selectAllUserEnquiries', res_crm.data)
        self.assertIn(b'Are you sure you want to permanently delete the selected enquiry records?', res_crm.data)
        self.assertIn(b'Confirm Delete', res_crm.data)
        self.assertIn(b'Cancel', res_crm.data)

        # 4. User Feedback page
        res_user_fb = client.get('/dashboard/feedback')
        self.assertEqual(res_user_fb.status_code, 200)
        self.assertIn(b'Delete Selected', res_user_fb.data)
        self.assertIn(b'selectAllUserFeedback', res_user_fb.data)
        self.assertIn(b'Are you sure you want to permanently delete the selected enquiry records?', res_user_fb.data)
        self.assertIn(b'Confirm Delete', res_user_fb.data)
        self.assertIn(b'Cancel', res_user_fb.data)

    def test_default_user_limits_configuration_and_reset(self):
        """Test Admin Dashboard Default User Limits Configuration and Reset to Default."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Verify User Management page loads with Default Limits configuration card
        res = admin_client.get('/admin/users')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Default User Limits Configuration', res.data)
        self.assertIn(b'default_listings_limit', res.data)
        self.assertIn(b'default_monthly_enquiries_limit', res.data)
        self.assertIn(b'default_photos_limit', res.data)
        self.assertIn(b'default_videos_limit', res.data)
        self.assertIn(b'Reset to Default', res.data)

        # 2. Update Default Limits
        update_res = admin_client.post('/admin/users/default-limits', data={
            'default_listings_limit': '15',
            'default_monthly_enquiries_limit': '150',
            'default_photos_limit': '12',
            'default_videos_limit': '3'
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)
        self.assertIn(b'Default user limits have been successfully saved', update_res.data)

        cur_limits = db.get_default_user_limits()
        self.assertEqual(cur_limits['listings_limit'], 15)
        self.assertEqual(cur_limits['monthly_enquiries_limit'], 150)
        self.assertEqual(cur_limits['photos_limit'], 12)
        self.assertEqual(cur_limits['videos_limit'], 3)

        # 3. Reset Default Limits back to system standard
        reset_res = admin_client.post('/admin/users/default-limits/reset', follow_redirects=True)
        self.assertEqual(reset_res.status_code, 200)
        self.assertIn(b'Default user limits have been reset to system defaults', reset_res.data)

        std_limits = db.get_default_user_limits()
        self.assertEqual(std_limits['listings_limit'], 10)
        self.assertEqual(std_limits['monthly_enquiries_limit'], 100)
        self.assertEqual(std_limits['photos_limit'], 10)
        self.assertEqual(std_limits['videos_limit'], 2)

    def test_user_limits_inheritance_and_custom_override(self):
        """Test default limits inheritance for newly registered users vs custom overrides."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Ensure starting with standard defaults (10, 100, 10, 2)
        db.reset_default_user_limits()

        ts = int(time.time() * 1000)
        uname = f"limit_user_{ts}"
        # 1. Create a standard user
        user_id = db.create_user({
            'username': uname,
            'password_hash': generate_password_hash('password123'),
            'email': f"{uname}@example.com",
            'full_name': "Limits Test User",
            'role': "agent"
        })
        self.assertIsNotNone(user_id)

        user = db.get_user_by_id(user_id)
        self.assertEqual(user['has_custom_limits'], 0)
        eff = db.get_effective_user_limits(user_id)
        self.assertEqual(eff['listings_limit'], 10)
        self.assertEqual(eff['monthly_enquiries_limit'], 100)
        self.assertEqual(eff['photos_limit'], 10)
        self.assertEqual(eff['videos_limit'], 2)

        # 2. Update default limits -> user without custom limits automatically inherits new defaults
        db.update_default_user_limits(listings_limit=14, monthly_enquiries_limit=140, photos_limit=8, videos_limit=4)
        eff_updated = db.get_effective_user_limits(user_id)
        self.assertEqual(eff_updated['listings_limit'], 14)
        self.assertEqual(eff_updated['monthly_enquiries_limit'], 140)
        self.assertEqual(eff_updated['photos_limit'], 8)
        self.assertEqual(eff_updated['videos_limit'], 4)

        # 3. Admin assigns custom individual limits override
        admin_client.post(f'/admin/users/edit/{user_id}', data={
            'full_name': 'Limits Test User',
            'email': f"{uname}@example.com",
            'phone': '9876543210',
            'role': 'agent',
            'status': 'active',
            'has_custom_limits': '1',
            'listing_limit': '25',
            'monthly_enquiries_limit': '250',
            'photos_limit': '20',
            'videos_limit': '5',
            'can_post_ads': 'on',
            'can_edit_ads': 'on',
            'can_delete_ads': 'on',
            'can_access_crm': 'on',
            'can_export_leads': 'on'
        }, follow_redirects=True)

        user_custom = db.get_user_by_id(user_id)
        self.assertEqual(user_custom['has_custom_limits'], 1)
        eff_custom = db.get_effective_user_limits(user_id)
        self.assertEqual(eff_custom['listings_limit'], 25)
        self.assertEqual(eff_custom['monthly_enquiries_limit'], 250)
        self.assertEqual(eff_custom['photos_limit'], 20)
        self.assertEqual(eff_custom['videos_limit'], 5)

        # 4. Admin changes system default limits again -> user's custom limits stay unchanged!
        db.update_default_user_limits(listings_limit=8, monthly_enquiries_limit=80, photos_limit=6, videos_limit=1)
        eff_after_default_change = db.get_effective_user_limits(user_id)
        self.assertEqual(eff_after_default_change['listings_limit'], 25)
        self.assertEqual(eff_after_default_change['monthly_enquiries_limit'], 250)
        self.assertEqual(eff_after_default_change['photos_limit'], 20)
        self.assertEqual(eff_after_default_change['videos_limit'], 5)

        # Cleanup
        db.reset_default_user_limits()

    def test_user_limits_enforcement_and_resource_usage(self):
        """Test listing, photo, video, and enquiry quota enforcement and user dashboard overview."""
        ts = int(time.time() * 1000)
        uname = f"enforce_user_{ts}"
        user_id = db.create_user({
            'username': uname,
            'password_hash': generate_password_hash('password123'),
            'email': f"{uname}@example.com",
            'full_name': "Quota Enforcement User",
            'role': "agent"
        })
        # Give custom limit: 1 listing, 2 photos, 1 video, 2 monthly enquiries
        conn = db.get_db()
        conn.execute("""
            UPDATE users SET 
                has_custom_limits = 1,
                listing_limit = 1,
                photos_limit = 2,
                upload_limit = 2,
                videos_limit = 1,
                monthly_enquiries_limit = 2,
                can_post_ads = 1,
                can_access_crm = 1,
                can_export_leads = 1
            WHERE id = ?
        """, (user_id,))
        conn.commit()
        conn.close()

        client = app.test_client()
        client.post('/login', data={'username': uname, 'password': 'password123'}, follow_redirects=True)

        # Check User Dashboard displays Account Resource Limits & Current Usage table
        dash_res = client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Account Resource Limits &amp; Current Usage', dash_res.data)
        self.assertIn(b'Total Property Listings', dash_res.data)
        self.assertIn(b'Monthly Enquiries Access', dash_res.data)
        self.assertIn(b'Photos Allowed Per Listing', dash_res.data)
        self.assertIn(b'Short Videos Allowed Per Listing', dash_res.data)

        # 1. Post first property with 3 photo URLs and 2 video URLs (exceeds limits -> capped!)
        p1_res = client.post('/dashboard/properties/add', data={
            'title': f'Quota Property 1 {ts}',
            'category': 'Apartment',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '5000000',
            'location': 'Kothrud',
            'gallery_image_urls': 'https://example.com/p1.jpg\nhttps://example.com/p2.jpg\nhttps://example.com/p3.jpg',
            'video_urls': 'https://example.com/v1.mp4\nhttps://example.com/v2.mp4',
            'status': 'Available'
        }, follow_redirects=True)
        self.assertEqual(p1_res.status_code, 200)
        self.assertIn(b'Under Review', p1_res.data)

        # Check stored property in DB has capped photos and videos
        prop = db.get_all_properties(filters={'q': f'Quota Property 1 {ts}', 'include_all_status': True})[0]
        gallery = json.loads(prop['gallery_images'])
        videos = json.loads(prop['video_urls'])
        self.assertLessEqual(len(gallery), 2)
        self.assertLessEqual(len(videos), 1)

        # Make the property Active so it counts towards active listing limit
        db.approve_property(prop['id'])

        # 2. Attempt to post second property -> Blocked by listing quota!
        p2_res = client.post('/dashboard/properties/add', data={
            'title': f'Quota Property 2 {ts}',
            'category': 'Apartment',
            'property_type': 'Residential',
            'purpose': 'Buy',
            'price': '6000000',
            'location': 'Baner',
            'status': 'Available'
        }, follow_redirects=True)
        self.assertIn(b'Listing Limit Reached', p2_res.data)

        # 3. Monthly enquiry limits and automatic reset
        db.record_user_enquiry_access(user_id, count=2)
        usage = db.get_user_resource_usage(user_id)
        self.assertTrue(usage['monthly_enquiries']['is_reached'])

        # CRM page should show monthly enquiry limit warning
        crm_res = client.get('/dashboard/crm')
        self.assertIn(b'Monthly Enquiry Access Limit Reached', crm_res.data)

        # Export should be blocked
        export_res = client.get('/dashboard/crm/export', follow_redirects=True)
        self.assertIn(b'Monthly Enquiry Access Limit Reached', export_res.data)

        # Test automatic calendar month reset
        conn = db.get_db()
        conn.execute("UPDATE users SET monthly_enquiries_reset_date = '2026-10' WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        db.check_and_reset_user_monthly_enquiries(user_id)
        user_reset = db.get_user_by_id(user_id)
        self.assertEqual(user_reset['monthly_enquiries_used'], 0)
        self.assertEqual(user_reset['monthly_enquiries_reset_date'], datetime.now().strftime('%Y-%m'))

    def test_records_per_page_crm_leads_and_feedback(self):
        """Test Records Per Page (10, 50, 100, 1000) dropdown, persistence, and pagination."""
        admin_client = app.test_client()
        admin_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # 1. Admin Leads & Enquiries: verify records per page dropdown and persistence
        res1 = admin_client.get('/admin/enquiries?per_page=50')
        self.assertEqual(res1.status_code, 200)
        self.assertIn(b'50 Records', res1.data)
        self.assertIn(b'1000 Records', res1.data)
        # Preference is saved in system_settings
        self.assertEqual(db.get_records_per_page_preference(user_id=1, section='leads'), 50)

        # Admin visits without per_page parameter -> preference 50 is retained
        res1_persisted = admin_client.get('/admin/enquiries')
        self.assertEqual(res1_persisted.status_code, 200)

        # 2. Admin Feedback: select 100 records per page
        res2 = admin_client.get('/admin/feedback?per_page=100')
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b'100 Records', res2.data)
        self.assertEqual(db.get_records_per_page_preference(user_id=1, section='feedback'), 100)

        # 3. User CRM Leads & User Feedback independent selection & persistence
        ts = int(time.time() * 1000)
        uname = f"per_page_user_{ts}"
        user_id = db.create_user({
            'username': uname,
            'password_hash': generate_password_hash('password123'),
            'email': f"{uname}@example.com",
            'full_name': "Per Page User",
            'role': "agent"
        })
        user_client = app.test_client()
        user_client.post('/login', data={'username': uname, 'password': 'password123'}, follow_redirects=True)

        # User defaults to 10
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='leads'), 10)
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='feedback'), 10)

        # User selects 1000 records per page in CRM Leads
        u_crm = user_client.get('/dashboard/crm?per_page=1000')
        self.assertEqual(u_crm.status_code, 200)
        self.assertIn(b'1000 Records', u_crm.data)
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='leads'), 1000)

        # User selects 50 records per page in Feedback
        u_fb = user_client.get('/dashboard/feedback?per_page=50')
        self.assertEqual(u_fb.status_code, 200)
        self.assertIn(b'50 Records', u_fb.data)
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='feedback'), 50)

        # User refreshes CRM Leads -> 1000 remains persisted
        u_crm_reload = user_client.get('/dashboard/crm')
        self.assertEqual(u_crm_reload.status_code, 200)
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='leads'), 1000)

        # Admin preference remains intact and independent of user preference
        self.assertEqual(db.get_records_per_page_preference(user_id=1, section='leads'), 50)
        self.assertEqual(db.get_records_per_page_preference(user_id=1, section='feedback'), 100)

        # Invalid per_page reverts safely to default 10
        invalid_res = user_client.get('/dashboard/crm?per_page=9999')
        self.assertEqual(invalid_res.status_code, 200)
        self.assertEqual(db.get_records_per_page_preference(user_id=user_id, section='leads'), 10)

if __name__ == '__main__':
    unittest.main()
