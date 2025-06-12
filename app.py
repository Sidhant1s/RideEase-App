from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_cors import CORS
import sqlite3
import os
import time
import hashlib
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import json
from werkzeug.utils import secure_filename
import math
import re

app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'  # Change this in production

DB_NAME = 'riding_website.db'
SOS_DIR = 'sos_media'
DOCUMENTS_DIR = 'documents'
SECURE_STORAGE_DIR = 'secure_storage'
VEHICLE_STORAGE_DIR = 'vehicle_storage'
UPLOAD_FOLDER = 'uploads'

# Create necessary directories
for directory in [SOS_DIR, DOCUMENTS_DIR, SECURE_STORAGE_DIR, VEHICLE_STORAGE_DIR, UPLOAD_FOLDER]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")  # Debug log

# Generate encryption key
def generate_key():
    return Fernet.generate_key()

# Store encryption key securely
ENCRYPTION_KEY = generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def verify_database():
    print("Verifying database structure...")  # Debug log
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                password TEXT NOT NULL,
                gender TEXT NOT NULL,
                driver_gender_preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check vehicles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT,
                driver_name TEXT,
                driver_gender TEXT NOT NULL,
                car_model TEXT,
                car_number TEXT UNIQUE,
                car_type TEXT,
                aadhaar_number TEXT,
                status TEXT DEFAULT 'available',
                rental_price REAL,
                is_rental BOOLEAN DEFAULT 0,
                customer_gender_preference TEXT
            )
        ''')
        
        # Check bookings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER,
                service_type TEXT NOT NULL,
                pickup TEXT NOT NULL,
                destination TEXT NOT NULL,
                pickup_time TEXT NOT NULL,
                passengers INTEGER NOT NULL,
                instructions TEXT,
                status TEXT DEFAULT 'pending',
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
            )
        ''')

        # Check rentals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status TEXT DEFAULT 'pending',
                total_price REAL NOT NULL,
                requirements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
            )
        ''')
        
        # Add sample data if tables are empty
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            print("Adding sample user...")  # Debug log
            cursor.execute('''
                INSERT INTO users (name, email, phone, password, gender, driver_gender_preference)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'Test User',
                'test@example.com',
                '1234567890',
                hashlib.sha256('password123'.encode()).hexdigest(),
                'male',
                'any'
            ))
        
        cursor.execute('SELECT COUNT(*) FROM vehicles')
        if cursor.fetchone()[0] == 0:
            print("Adding sample vehicles...")  # Debug log
            # Add vehicles for booking
            cursor.execute('''
                INSERT INTO vehicles (
                    driver_name, driver_gender, car_model, car_number, 
                    car_type, status, customer_gender_preference, is_rental, rental_price
                ) VALUES 
                    ('John Doe', 'male', 'Toyota Camry', 'ABC123', 'standard', 'available', 'any', 0, NULL),
                    ('Jane Smith', 'female', 'Honda Civic', 'XYZ789', 'standard', 'available', 'any', 0, NULL),
                    ('Mike Johnson', 'male', 'Mercedes E-Class', 'DEF456', 'premium', 'available', 'any', 0, NULL),
                    ('Sarah Wilson', 'female', 'Toyota Corolla', 'GHI789', 'shared', 'available', 'any', 0, NULL)
            ''')
            
            # Add vehicles for rental
            cursor.execute('''
                INSERT INTO vehicles (
                    driver_name, driver_gender, car_model, car_number, 
                    car_type, status, customer_gender_preference, is_rental, rental_price
                ) VALUES 
                    ('David Brown', 'male', 'BMW 5 Series', 'JKL123', 'premium', 'available', 'any', 1, 100.00),
                    ('Emma Davis', 'female', 'Audi A4', 'MNO456', 'premium', 'available', 'any', 1, 90.00),
                    ('James Wilson', 'male', 'Toyota Camry', 'PQR789', 'standard', 'available', 'any', 1, 50.00),
                    ('Lisa Anderson', 'female', 'Honda Civic', 'STU123', 'standard', 'available', 'any', 1, 45.00)
            ''')
        
        conn.commit()
        print("Database verification completed successfully")  # Debug log
        
    except Exception as e:
        print(f"Error verifying database: {str(e)}")  # Debug log
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    print("Initializing database...")  # Debug log
    verify_database()
    print("Database initialized successfully!")  # Debug log

def migrate_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE bookings ADD COLUMN document_path TEXT')
    except Exception:
        pass  # Already exists
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/rental')
def rental():
    return render_template('rental.html')

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

def init_emergency_conditions(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already has emergency conditions
        cursor.execute('SELECT id FROM emergency_conditions WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            return
            
        # Initialize default emergency conditions
        cursor.execute('''
            INSERT INTO emergency_conditions (
                user_id,
                distance_threshold,
                location_condition,
                time_start,
                time_end,
                time_condition,
                speed_threshold,
                speed_condition,
                emergency_contacts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            10,  # 10km distance threshold
            'away',  # Alert when away from home
            '22:00',  # 10 PM
            '06:00',  # 6 AM
            'outside',  # Alert outside these hours
            120,  # 120 km/h speed threshold
            'above',  # Alert when speed is above threshold
            '[]'  # Empty emergency contacts list
        ))
        
        conn.commit()
        print(f"Initialized emergency conditions for user {user_id}")  # Debug log
        
    except Exception as e:
        print(f"Error initializing emergency conditions: {str(e)}")  # Debug log
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/auth/register', methods=['POST'])
def handle_register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        gender = data.get('gender')
        driver_gender_preference = data.get('driver_gender_preference')

        if not all([name, email, phone, password, gender]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        # Validate gender
        if gender not in ['male', 'female', 'other']:
            return jsonify({'success': False, 'message': 'Invalid gender'}), 400

        # Validate driver gender preference if provided
        if driver_gender_preference and driver_gender_preference not in ['male', 'female', 'any']:
            return jsonify({'success': False, 'message': 'Invalid driver gender preference'}), 400

        # Validate password strength
        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$', password):
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number'
            }), 400

        # Hash password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Email already registered'}), 400

        # Insert new user
        cursor.execute('''
            INSERT INTO users (name, email, phone, password, gender, driver_gender_preference)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, hashed_password, gender, driver_gender_preference))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Registration successful! Please login.'
        }), 201

    except Exception as e:
        print(f"Registration error: {str(e)}")  # Debug log
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500

@app.route('/api/auth/login', methods=['POST'])
def handle_login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        print(f"Login attempt for email: {email}")  # Debug log

        if not all([email, password]):
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user
        cursor.execute('SELECT id, name, password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        print(f"User found: {user is not None}")  # Debug log

        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401

        # Verify password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        print(f"Password match: {user['password'] == hashed_password}")  # Debug log

        if user['password'] != hashed_password:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401

        # Set session
        session['user_id'] = user['id']
        session['username'] = user['name']
        
        print(f"Session set - user_id: {user['id']}, username: {user['name']}")  # Debug log

        return jsonify({
            'success': True,
            'userId': user['id'],
            'username': user['name'],
            'message': 'Login successful'
        })
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.json
        user_id = data.get('userId')
        otp = data.get('otp')

        if not all([user_id, otp]):
            return jsonify({
                'success': False,
                'message': 'User ID and OTP are required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get latest OTP
        cursor.execute('''
            SELECT otp, expires_at, used
            FROM otps
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (user_id,))
        
        otp_record = cursor.fetchone()

        if not otp_record:
            return jsonify({
                'success': False,
                'message': 'No OTP found'
            }), 400

        if otp_record['used']:
            return jsonify({
                'success': False,
                'message': 'OTP already used'
            }), 400

        if time.time() > otp_record['expires_at']:
            return jsonify({
                'success': False,
                'message': 'OTP expired'
            }), 400

        if otp != otp_record['otp']:
            return jsonify({
                'success': False,
                'message': 'Invalid OTP'
            }), 400

        # Mark OTP as used
        cursor.execute('UPDATE otps SET used = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        # In production, generate a proper JWT token
        token = 'dummy_token'  # Replace with proper JWT token

        return jsonify({
            'success': True,
            'token': token,
            'message': 'Login successful'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    try:
        data = request.json
        user_id = data.get('userId')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User ID is required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user email
        cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Generate new OTP
        import random
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = time.time() + 300  # 5 minutes

        # Store new OTP
        cursor.execute('''
            INSERT INTO otps (user_id, otp, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, otp, expires_at))

        conn.commit()
        conn.close()

        # In production, send OTP via email/SMS
        print(f"New OTP for {user['email']}: {otp}")  # For development only

        return jsonify({
            'success': True,
            'message': 'New OTP sent successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

# Endpoint to get vehicles by type and category
@app.route('/vehicles', methods=['GET'])
def get_vehicles():
    vtype = request.args.get('type')  # booking or rental
    category = request.args.get('category')
    subcategory = request.args.get('subcategory')
    conn = get_db_connection()
    query = 'SELECT * FROM vehicles WHERE 1=1'
    params = []
    if vtype:
        query += ' AND type=?'
        params.append(vtype)
    if category:
        query += ' AND category=?'
        params.append(category)
    if subcategory:
        query += ' AND subcategory=?'
        params.append(subcategory)
    vehicles = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in vehicles])

def calculate_price(service_type, pickup, destination):
    # Base prices for different service types
    base_prices = {
        'standard': 50,
        'premium': 100,
        'shared': 30
    }
    
    # Get base price for the service type
    base_price = base_prices.get(service_type, 50)
    
    # In a real application, you would calculate distance between pickup and destination
    # For now, we'll use a simple multiplier
    distance_multiplier = 1.5
    
    return base_price * distance_multiplier

@app.route('/api/bookings/create', methods=['POST'])
def create_booking():
    try:
        print("\n=== Starting Booking Process ===")  # Debug log
        print(f"Request Headers: {dict(request.headers)}")  # Debug log
        print(f"Session Data: {dict(session)}")  # Debug log
        
        # Get data from request
        data = request.get_json()
        print(f"Request Data: {data}")  # Debug log
        
        # Get user ID from session or request data
        user_id = session.get('user_id') or data.get('user_id')
        print(f"User ID from session/data: {user_id}")  # Debug log
        
        if not user_id:
            print("No user ID found in session or request data")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Please log in to make a booking'
            }), 401

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verify user exists
            cursor.execute('SELECT id, name, gender, driver_gender_preference FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                print(f"User not found in database: {user_id}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'User not found. Please log in again.'
                }), 401
            
            print(f"Found user: {user['name']}")  # Debug log
            
            # Validate required fields
            required_fields = ['service_type', 'pickup', 'destination', 'pickup_time', 'passengers']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                print(f"Missing required fields: {missing_fields}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            # Extract booking details
            service_type = data.get('service_type')
            pickup = data.get('pickup')
            destination = data.get('destination')
            pickup_time = data.get('pickup_time')
            passengers = int(data.get('passengers'))
            instructions = data.get('instructions', '')

            print(f"Booking details:")  # Debug log
            print(f"- Service Type: {service_type}")
            print(f"- Pickup: {pickup}")
            print(f"- Destination: {destination}")
            print(f"- Pickup Time: {pickup_time}")
            print(f"- Passengers: {passengers}")

            # Find available vehicles
            query = '''
                SELECT v.* FROM vehicles v
                WHERE v.status = 'available'
                AND v.car_type = ?
            '''
            params = [service_type]

            # Add gender preference conditions if user has preferences
            if user['gender'] and user['driver_gender_preference']:
                query += '''
                    AND (
                        v.customer_gender_preference IS NULL 
                        OR v.customer_gender_preference = ? 
                        OR v.customer_gender_preference = 'any'
                    )
                '''
                params.append(user['gender'])

                if user['driver_gender_preference'] != 'any':
                    query += ' AND v.driver_gender = ?'
                    params.append(user['driver_gender_preference'])

            print(f"Vehicle search query: {query}")  # Debug log
            print(f"Query parameters: {params}")  # Debug log

            cursor.execute(query, params)
            available_vehicles = cursor.fetchall()
            print(f"Found {len(available_vehicles)} available vehicles")  # Debug log

            if not available_vehicles:
                return jsonify({
                    'success': False,
                    'message': 'No suitable vehicles available at the moment. Please try again later.'
                }), 404

            # Select first available vehicle
            vehicle = available_vehicles[0]
            vehicle_id = vehicle['id']
            print(f"Selected vehicle: {vehicle['car_model']} ({vehicle['car_number']})")  # Debug log

            # Calculate price
            try:
                price = calculate_price(service_type, pickup, destination)
                print(f"Calculated price: {price}")  # Debug log
            except Exception as e:
                print(f"Error calculating price: {str(e)}")  # Debug log
                price = 50.00  # Default price if calculation fails

            # Create booking
            try:
                cursor.execute('''
                    INSERT INTO bookings (
                        user_id, vehicle_id, service_type, pickup, destination, 
                        pickup_time, passengers, instructions, price, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, vehicle_id, service_type, pickup, destination,
                    pickup_time, passengers, instructions, price, 'pending'
                ))

                booking_id = cursor.lastrowid
                print(f"Created booking with ID: {booking_id}")  # Debug log

                # Update vehicle status
                cursor.execute('UPDATE vehicles SET status = ? WHERE id = ?', ('booked', vehicle_id))
                print(f"Updated vehicle {vehicle_id} status to 'booked'")  # Debug log

                conn.commit()
                print("Database transaction committed successfully")  # Debug log

                return jsonify({
                    'success': True,
                    'message': 'Booking created successfully',
                    'booking_id': booking_id,
                    'price': price,
                    'vehicle': {
                        'id': vehicle['id'],
                        'driver_name': vehicle['driver_name'],
                        'car_model': vehicle['car_model'],
                        'car_number': vehicle['car_number']
                    }
                }), 201

            except sqlite3.Error as e:
                conn.rollback()
                print(f"Database error during booking: {str(e)}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Error saving booking. Please try again.'
                }), 500

        except Exception as e:
            print(f"Error processing booking: {str(e)}")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Error processing booking. Please try again.'
            }), 500

        finally:
            conn.close()
            print("Database connection closed")  # Debug log

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        }), 500

    print("=== Booking Process Completed ===\n")  # Debug log

# Endpoint to get all bookings
@app.route('/bookings', methods=['GET'])
def get_bookings():
    try:
        user_id = request.cookies.get('user_id') or 1  # For testing
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.*, v.driver_name, v.car_model, v.car_number
            FROM bookings b
            LEFT JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        ''', (user_id,))
        
        bookings = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'bookings': [dict(row) for row in bookings]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Admin login endpoint
@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username == 'admin' and password == 'admin123':
        session['admin_logged_in'] = True
        return jsonify({'message': 'Admin login successful'})
    return jsonify({'error': 'Invalid credentials'}), 401

# Admin logout endpoint
@app.route('/admin_logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({'message': 'Logged out'})

# Helper: check admin
def is_admin():
    return session.get('admin_logged_in', False)

# Endpoint to add a vehicle (for admin/future use)
@app.route('/vehicles', methods=['POST'])
def add_vehicle():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vehicles (name, type, category, subcategory, available)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['name'],
        data['type'],
        data['category'],
        data.get('subcategory'),
        data.get('available', 1)
    ))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Vehicle added successfully'})

@app.route('/sos', methods=['POST'])
def trigger_sos():
    try:
        print("SOS trigger received")  # Debug log
        
        # Get user_id from either session or request
        user_id = session.get('user_id')
        if not user_id:
            data = request.get_json()
            user_id = data.get('userId')
            if not user_id:
                print("SOS error: No user ID found")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Please log in to use the SOS feature'
                }), 401
        
        data = request.get_json()
        if not data:
            print("SOS error: No data received")  # Debug log
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
            
        # Get location from request or geolocation
        current_location = data.get('location', {})
        if not current_location:
            # Try to get location from request headers
            current_location = {
                'latitude': request.headers.get('X-Latitude'),
                'longitude': request.headers.get('X-Longitude')
            }
            
        if not current_location.get('latitude') or not current_location.get('longitude'):
            print("SOS error: No location data")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Location data is required'
            }), 400
        
        current_speed = data.get('speed', 0)
        
        # Get emergency conditions and contacts
        should_alert, emergency_contacts = check_emergency_conditions(
            user_id, 
            current_location, 
            current_speed
        )
        
        # Record SOS trigger
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sos_triggers (
                user_id,
                latitude,
                longitude,
                speed,
                timestamp
            ) VALUES (?, ?, ?, ?, datetime('now'))
        ''', (
            user_id,
            current_location['latitude'],
            current_location['longitude'],
            current_speed
        ))
        
        trigger_id = cursor.lastrowid
        
        # Get trigger count in last 5 minutes
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM sos_triggers
            WHERE user_id = ?
            AND timestamp > datetime('now', '-5 minutes')
        ''', (user_id,))
        
        trigger_count = cursor.fetchone()['count']
        
        conn.commit()
        conn.close()
        
        # If conditions are met or this is the third trigger, notify contacts
        if should_alert or trigger_count >= 3:
            for contact in emergency_contacts:
                message = f"EMERGENCY ALERT: User {user_id} has triggered an SOS alert at location {current_location['latitude']}, {current_location['longitude']}"
                send_sms(contact['phone'], message)
        
        return jsonify({
            'success': True,
            'trigger_id': trigger_id,
            'trigger_count': trigger_count,
            'message': 'SOS alert processed successfully'
        })
        
    except Exception as e:
        print(f"SOS error: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def check_emergency_conditions(user_id, current_location, current_speed):
    try:
        print(f"Checking emergency conditions for user {user_id}")  # Debug log
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user's emergency conditions
        cursor.execute('SELECT * FROM emergency_conditions WHERE user_id = ?', (user_id,))
        conditions = cursor.fetchone()
        
        if not conditions:
            print("No emergency conditions found")  # Debug log
            return False, []
            
        should_alert = False
        emergency_contacts = json.loads(conditions['emergency_contacts']) if conditions['emergency_contacts'] else []
        
        # Check location condition
        if conditions['location_condition'] == 'away' and current_location:
            try:
                # Get user's home location
                cursor.execute('SELECT home_location FROM users WHERE id = ?', (user_id,))
                home_location = cursor.fetchone()['home_location']
                
                if home_location:
                    home_loc = json.loads(home_location)
                    distance = calculate_distance(
                        (home_loc['latitude'], home_loc['longitude']),
                        (current_location['latitude'], current_location['longitude'])
                    )
                    if distance > conditions['distance_threshold']:
                        should_alert = True
                        print(f"Location condition met: Distance {distance} > threshold {conditions['distance_threshold']}")  # Debug log
            except Exception as e:
                print(f"Error checking location condition: {str(e)}")  # Debug log
        
        # Check time condition
        if conditions['time_condition']:
            current_time = datetime.now().time()
            start_time = datetime.strptime(conditions['time_start'], '%H:%M').time()
            end_time = datetime.strptime(conditions['time_end'], '%H:%M').time()
            
            if conditions['time_condition'] == 'outside':
                if current_time < start_time or current_time > end_time:
                    should_alert = True
                    print("Time condition met: Outside allowed hours")  # Debug log
            elif conditions['time_condition'] == 'inside':
                if start_time <= current_time <= end_time:
                    should_alert = True
                    print("Time condition met: Inside specified hours")  # Debug log
        
        # Check speed condition
        if conditions['speed_condition'] and conditions['speed_threshold']:
            if (conditions['speed_condition'] == 'above' and current_speed > conditions['speed_threshold']) or \
               (conditions['speed_condition'] == 'below' and current_speed < conditions['speed_threshold']):
                should_alert = True
                print(f"Speed condition met: {current_speed} {conditions['speed_condition']} threshold {conditions['speed_threshold']}")  # Debug log
        
        return should_alert, emergency_contacts
        
    except Exception as e:
        print(f"Error checking emergency conditions: {str(e)}")  # Debug log
        return False, []
    finally:
        if 'conn' in locals():
            conn.close()

def calculate_distance(loc1, loc2):
    from math import sin, cos, sqrt, atan2, radians
    
    # Approximate radius of earth in km
    R = 6371.0
    
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance

def send_sms(phone_number, message):
    try:
        print(f"Sending SMS to {phone_number}: {message}")  # Debug log
        # In production, integrate with an SMS service provider
        # For now, we'll just log the message
        return True
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")  # Debug log
        return False

@app.route('/sos_audio', methods=['POST'])
def sos_audio():
    if 'audio' in request.files:
        audio = request.files['audio']
        audio.save(os.path.join(SOS_DIR, 'sos_audio.webm'))
        print("SOS audio received and saved.")
        return jsonify({'message': 'Audio received'})
    return jsonify({'error': 'No audio received'}), 400

@app.route('/sos_video', methods=['POST'])
def handle_sos_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video received'}), 400
            
        video = request.files['video']
        user_id = request.form.get('userId')
        vehicle_id = request.form.get('vehicleId')
        camera_type = request.form.get('cameraType', 'front')
        password = request.form.get('password')
        location = request.form.get('location')
        
        if not all([user_id, vehicle_id, password]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create secure storage directory if it doesn't exist
        secure_dir = os.path.join(SECURE_STORAGE_DIR, f'user_{user_id}')
        if not os.path.exists(secure_dir):
            os.makedirs(secure_dir)
            
        # Create vehicle-specific directory
        vehicle_dir = os.path.join(secure_dir, f'vehicle_{vehicle_id}')
        if not os.path.exists(vehicle_dir):
            os.makedirs(vehicle_dir)
        
        # Read video data
        video_data = video.read()
        
        # Encrypt the video data
        encrypted_data = cipher_suite.encrypt(video_data)
        
        # Save encrypted video with camera type in filename
        filename = f'sos_video_{camera_type}_{timestamp}.enc'
        filepath = os.path.join(vehicle_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)
        
        # Store file information in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO secure_storage (
                user_id, 
                vehicle_id, 
                file_path, 
                password_hash,
                camera_type,
                location,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            user_id, 
            vehicle_id, 
            filepath, 
            hashlib.sha256(password.encode()).hexdigest(),
            camera_type,
            location
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Video stored securely',
            'file_path': filepath
        })
        
    except Exception as e:
        print(f"Error storing video: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/vehicle_video', methods=['POST'])
def handle_vehicle_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video received'}), 400
            
        video = request.files['video']
        vehicle_id = request.form.get('vehicleId')
        camera_type = request.form.get('cameraType', 'cab')
        password = request.form.get('password')
        
        if not all([vehicle_id, password]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create vehicle storage directory
        vehicle_dir = os.path.join(VEHICLE_STORAGE_DIR, f'vehicle_{vehicle_id}')
        if not os.path.exists(vehicle_dir):
            os.makedirs(vehicle_dir)
        
        # Read video data
        video_data = video.read()
        
        # Encrypt the video data
        encrypted_data = cipher_suite.encrypt(video_data)
        
        # Save encrypted video
        filename = f'vehicle_video_{camera_type}_{timestamp}.enc'
        filepath = os.path.join(vehicle_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)
        
        # Store file information in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO secure_storage (
                vehicle_id, 
                file_path, 
                password_hash,
                camera_type,
                created_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
        ''', (
            vehicle_id, 
            filepath, 
            hashlib.sha256(password.encode()).hexdigest(),
            camera_type
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Vehicle video stored securely',
            'file_path': filepath
        })
        
    except Exception as e:
        print(f"Error storing vehicle video: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/access_secure_video', methods=['POST'])
def access_secure_video():
    try:
        data = request.json
        file_path = data.get('filePath')
        password = data.get('password')
        user_id = session.get('user_id')
        
        if not all([file_path, password, user_id]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify password and user access
        cursor.execute('''
            SELECT password_hash, user_id 
            FROM secure_storage 
            WHERE file_path = ?
        ''', (file_path,))
        
        record = cursor.fetchone()
        
        if not record:
            return jsonify({'error': 'File not found'}), 404
            
        if not hashlib.sha256(password.encode()).hexdigest() == record['password_hash']:
            return jsonify({'error': 'Invalid password'}), 401
            
        if str(record['user_id']) != str(user_id):
            return jsonify({'error': 'Unauthorized access'}), 403
            
        # Read and decrypt the file
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
            
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        
        return jsonify({
            'success': True,
            'video_data': decrypted_data.decode('latin1')
        })
        
    except Exception as e:
        print(f"Error accessing video: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Endpoint to upload a document for rental
@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'document' not in request.files:
        return jsonify({'error': 'No document uploaded'}), 400
    file = request.files['document']
    filename = file.filename
    save_path = os.path.join(DOCUMENTS_DIR, filename)
    file.save(save_path)
    return jsonify({'document_path': save_path})

# Register vehicle and upload docs
@app.route('/api/vehicles/register', methods=['POST'])
def register_vehicle():
    try:
        data = request.get_json()
        driver_name = data.get('driver_name')
        car_model = data.get('car_model')
        car_number = data.get('car_number')
        car_type = data.get('car_type')
        aadhaar_number = data.get('aadhaar_number')
        driver_gender = data.get('driver_gender')
        customer_gender_preference = data.get('customer_gender_preference')

        if not all([driver_name, car_model, car_number, car_type, aadhaar_number, driver_gender]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        # Validate driver gender
        if driver_gender not in ['male', 'female', 'other']:
            return jsonify({'success': False, 'message': 'Invalid driver gender'}), 400

        # Validate customer gender preference if provided
        if customer_gender_preference and customer_gender_preference not in ['male', 'female', 'any']:
            return jsonify({'success': False, 'message': 'Invalid customer gender preference'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if vehicle already exists
        cursor.execute('SELECT id FROM vehicles WHERE car_number = ?', (car_number,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Vehicle already registered'}), 400

        # Insert new vehicle
        cursor.execute('''
            INSERT INTO vehicles (driver_name, car_model, car_number, car_type, aadhaar_number, driver_gender, customer_gender_preference)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (driver_name, car_model, car_number, car_type, aadhaar_number, driver_gender, customer_gender_preference))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Vehicle registered successfully!'
        }), 201

    except Exception as e:
        print(f"Vehicle registration error: {str(e)}")  # Debug log
        return jsonify({'success': False, 'message': 'Vehicle registration failed. Please try again.'}), 500

# Update vehicle location
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    vehicle_id = data.get('vehicle_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    timestamp = int(time.time())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO vehicle_locations (vehicle_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)''',
        (vehicle_id, latitude, longitude, timestamp))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Location updated'})

# Get all vehicle locations (for admin)
@app.route('/get_locations', methods=['GET'])
def get_locations():
    conn = get_db_connection()
    locations = conn.execute('''SELECT v.id as vehicle_id, v.driver_name, v.car_model, v.car_number, l.latitude, l.longitude, l.timestamp FROM vehicles v JOIN vehicle_locations l ON v.id = l.vehicle_id WHERE l.id IN (SELECT MAX(id) FROM vehicle_locations GROUP BY vehicle_id)''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in locations])

@app.route('/premium_sos', methods=['POST'])
def premium_sos():
    try:
        data = request.json
        contact = data.get('contact')
        user_id = data.get('userId')
        vehicle_id = data.get('vehicleId')
        
        if not all([contact, user_id, vehicle_id]):
            return jsonify({
                'success': False,
                'message': 'Missing required parameters'
            }), 400
            
        # Here you would integrate with payment processing
        # For now, we'll just simulate the 2% charge
        charge_amount = 2.00  # $2.00 for premium SOS
        
        # Process the premium SOS alert
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Record the premium SOS
        cursor.execute('''
            INSERT INTO sos_triggers 
            (user_id, vehicle_id, trigger_count, last_trigger_time, is_premium)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP, 1)
        ''', (user_id, vehicle_id, 1, datetime.now(), 1))
        
        conn.commit()
        conn.close()
        
        # In production, integrate with SMS/email service
        print(f"Premium SOS alert sent to {contact['name']} at {contact['phone']}")
        print(f"Charged amount: ${charge_amount}")
        
        return jsonify({
            'success': True,
            'message': 'Premium SOS alert sent successfully',
            'charge_amount': charge_amount
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/rent', methods=['POST'])
def rent_vehicle():
    try:
        if 'user_id' not in session:
            print("Rental error: User not logged in")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Please login to rent a vehicle'
            }), 401

        data = request.json
        print(f"Received rental data: {data}")  # Debug log
        
        vehicle_id = data.get('vehicleId')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        requirements = data.get('requirements', '')
        
        print(f"Rental attempt - Vehicle ID: {vehicle_id}, User ID: {session['user_id']}")  # Debug log
        
        if not all([vehicle_id, start_date, end_date]):
            print("Rental error: Missing required fields")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
            
        try:
            # Convert dates to datetime objects
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            print(f"Rental error: Invalid date format - {str(e)}")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD'
            }), 400
        
        if start >= end:
            print("Rental error: End date must be after start date")  # Debug log
            return jsonify({
                'success': False,
                'message': 'End date must be after start date'
            }), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get vehicle details
            cursor.execute('SELECT * FROM vehicles WHERE id = ?', (vehicle_id,))
            vehicle = cursor.fetchone()
            
            if not vehicle:
                print(f"Rental error: Vehicle not found - ID: {vehicle_id}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Vehicle not found'
                }), 404
                
            print(f"Vehicle found: {vehicle['car_model']}, Status: {vehicle['status']}, Is Rental: {vehicle['is_rental']}, Price: {vehicle['rental_price']}")  # Debug log
                
            if vehicle['status'] != 'available':
                print(f"Rental error: Vehicle not available - Status: {vehicle['status']}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Vehicle is not available'
                }), 400
                
            if not vehicle['is_rental']:
                print(f"Rental error: Vehicle not available for rental - Is Rental: {vehicle['is_rental']}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'This vehicle is not available for rental'
                }), 400
                
            if not vehicle['rental_price']:
                print(f"Rental error: Vehicle has no rental price")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'This vehicle has no rental price set'
                }), 400
                
            # Calculate duration and price
            duration = (end - start).days
            total_price = vehicle['rental_price'] * duration
            
            print(f"Calculated rental - Duration: {duration} days, Total Price: {total_price}")  # Debug log
            
            # Create rental
            cursor.execute('''
                INSERT INTO rentals (user_id, vehicle_id, start_date, end_date, status, total_price, requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], vehicle_id, start_date, end_date, 'pending', total_price, requirements))
            
            rental_id = cursor.lastrowid
            
            # Update vehicle status
            cursor.execute('UPDATE vehicles SET status = ? WHERE id = ?', ('rented', vehicle_id))
            
            conn.commit()
            print(f"Rental created successfully - ID: {rental_id}")  # Debug log
            
            return jsonify({
                'success': True,
                'rental_id': rental_id,
                'status': 'pending',
                'total_price': total_price,
                'duration': duration,
                'message': 'Rental request submitted successfully'
            })
            
        except sqlite3.Error as e:
            print(f"Database error during rental: {str(e)}")  # Debug log
            conn.rollback()
            return jsonify({
                'success': False,
                'message': 'Database error occurred'
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Unexpected rental error: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/available_vehicles', methods=['GET'])
def get_available_vehicles():
    try:
        vehicle_type = request.args.get('type', 'booking')
        print(f"Fetching available vehicles for type: {vehicle_type}")  # Debug log
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if vehicle_type == 'rental':
            cursor.execute('''
                SELECT * FROM vehicles 
                WHERE status = 'available' 
                AND is_rental = 1 
                AND rental_price IS NOT NULL
            ''')
        else:
            cursor.execute('''
                SELECT * FROM vehicles 
                WHERE status = 'available' 
                AND is_rental = 0
            ''')
        
        vehicles = [dict(row) for row in cursor.fetchall()]
        print(f"Found {len(vehicles)} available vehicles")  # Debug log
        
        conn.close()
        
        return jsonify({
            'success': True,
            'vehicles': vehicles
        })
    except Exception as e:
        print(f"Error getting vehicles: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/api/contact', methods=['POST'])
def handle_contact():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')

        if not all([name, email, subject, message]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        # In a real application, you would send an email here
        print(f"Contact form submission from {name} ({email})")
        print(f"Subject: {subject}")
        print(f"Message: {message}")

        return jsonify({
            'success': True,
            'message': 'Message sent successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users with their contact information
        cursor.execute('''
            SELECT name, email, phone 
            FROM users 
            ORDER BY name
        ''')
        
        contacts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'contacts': contacts
        })
    except Exception as e:
        print(f"Error fetching contacts: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/save-emergency-conditions', methods=['POST'])
def save_emergency_conditions():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        # Save emergency conditions to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, clear existing conditions
        cursor.execute('DELETE FROM emergency_conditions WHERE user_id = ?', (user_id,))
        
        # Insert new conditions
        cursor.execute('''
            INSERT INTO emergency_conditions (
                user_id, 
                distance_threshold,
                location_condition,
                specific_location,
                time_start,
                time_end,
                time_condition,
                speed_threshold,
                speed_condition,
                emergency_contacts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['location']['threshold'],
            data['location']['condition'],
            data['location']['specificLocation'],
            data['time']['start'],
            data['time']['end'],
            data['time']['condition'],
            data['speed']['threshold'],
            data['speed']['condition'],
            json.dumps(data['emergencyContacts'])
        ))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving emergency conditions: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/test/status', methods=['GET'])
def test_status():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check session
        session_status = {
            'has_session': 'user_id' in session,
            'user_id': session.get('user_id'),
            'username': session.get('username')
        }
        
        # Check database tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check users table
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        # Check vehicles table
        cursor.execute('SELECT COUNT(*) FROM vehicles')
        vehicle_count = cursor.fetchone()[0]
        
        # Check bookings table
        cursor.execute('SELECT COUNT(*) FROM bookings')
        booking_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'session': session_status,
            'database': {
                'tables': tables,
                'user_count': user_count,
                'vehicle_count': vehicle_count,
                'booking_count': booking_count
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting application...")  # Debug log
    init_db()
    migrate_db()
    print("Database initialized, starting server...")  # Debug log
    app.run(host='0.0.0.0', port=8000, debug=True) 