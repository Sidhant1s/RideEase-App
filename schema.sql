-- Create tables if they don't exist

-- Emergency conditions table
CREATE TABLE IF NOT EXISTS emergency_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    distance_threshold INTEGER,
    location_condition TEXT,
    specific_location TEXT,
    time_start TEXT,
    time_end TEXT,
    time_condition TEXT,
    speed_threshold INTEGER,
    speed_condition TEXT,
    emergency_contacts TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- SOS triggers table
CREATE TABLE IF NOT EXISTS sos_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    speed REAL DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Secure storage table
CREATE TABLE IF NOT EXISTS secure_storage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vehicle_id INTEGER,
    file_path TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    camera_type TEXT NOT NULL,
    location TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
);

-- Video access logs table
CREATE TABLE IF NOT EXISTS video_access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_type TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES secure_storage (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Video metadata table
CREATE TABLE IF NOT EXISTS video_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    duration INTEGER NOT NULL,
    resolution TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    encryption_type TEXT NOT NULL,
    upload_status TEXT NOT NULL,
    server_path TEXT,
    FOREIGN KEY (file_id) REFERENCES secure_storage (id)
);

-- Drivers table
CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    car_model TEXT NOT NULL,
    car_number TEXT NOT NULL,
    car_type TEXT NOT NULL,
    license_path TEXT NOT NULL,
    registration_path TEXT NOT NULL,
    insurance_path TEXT NOT NULL,
    photo_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    verified_at TIMESTAMP,
    rejection_reason TEXT
); 