import sqlite3
import os

def init_db():
    # Remove existing database if it exists
    if os.path.exists('riding_website.db'):
        os.remove('riding_website.db')
    
    conn = sqlite3.connect('riding_website.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create vehicles table
    cursor.execute('''
    CREATE TABLE vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_number TEXT UNIQUE NOT NULL,
        car_model TEXT NOT NULL,
        car_type TEXT NOT NULL,
        driver_name TEXT NOT NULL,
        status TEXT DEFAULT 'available',
        rental_price REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create bookings table
    cursor.execute('''
    CREATE TABLE bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vehicle_id INTEGER,
        pickup_location TEXT NOT NULL,
        destination TEXT NOT NULL,
        pickup_time TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'pending',
        price REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Create rentals table
    cursor.execute('''
    CREATE TABLE rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vehicle_id INTEGER,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status TEXT DEFAULT 'pending',
        price REAL NOT NULL,
        requirements TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Insert sample vehicles
    sample_vehicles = [
        ('KA01AB1234', 'Toyota Camry', 'Standard', 'John Doe', 'available', 50.0),
        ('KA02CD5678', 'Honda City', 'Premium', 'Jane Smith', 'available', 75.0),
        ('KA03EF9012', 'Maruti Swift', 'Shared', 'Mike Johnson', 'available', 30.0),
        ('KA04GH3456', 'Hyundai Creta', 'Premium', 'Sarah Wilson', 'available', 80.0),
        ('KA05IJ7890', 'Toyota Innova', 'Standard', 'David Brown', 'available', 60.0),
        ('KA06KL1234', 'Honda Amaze', 'Shared', 'Lisa Anderson', 'available', 35.0),
        ('KA07MN5678', 'Hyundai i20', 'Standard', 'Tom Harris', 'available', 45.0),
        ('KA08OP9012', 'Maruti Baleno', 'Premium', 'Emma Davis', 'available', 70.0)
    ]
    
    cursor.executemany('''
    INSERT INTO vehicles (car_number, car_model, car_type, driver_name, status, rental_price)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_vehicles)
    
    # Insert a test user
    cursor.execute('''
    INSERT INTO users (username, password, email, phone)
    VALUES (?, ?, ?, ?)
    ''', ('testuser', 'testpass', 'test@example.com', '1234567890'))
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 