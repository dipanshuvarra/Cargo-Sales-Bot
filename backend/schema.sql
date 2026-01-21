-- Routes table: stores available air cargo routes with pricing
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    base_price_per_kg REAL NOT NULL,
    transit_days INTEGER NOT NULL,
    UNIQUE(origin, destination)
);

-- Bookings table: stores cargo bookings with soft delete support
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT UNIQUE NOT NULL,
    customer_name TEXT,
    customer_email TEXT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    weight REAL NOT NULL,
    volume REAL,
    cargo_type TEXT NOT NULL,
    shipping_date TEXT NOT NULL,
    price REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK(status IN ('pending', 'confirmed', 'cancelled', 'archived'))
);

-- Audit logs table: tracks all API requests with latency
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    request_data TEXT,
    response_status INTEGER,
    user_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bookings_booking_id ON bookings(booking_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_routes_origin_dest ON routes(origin, destination);

-- Seed data: common international air cargo routes
INSERT OR IGNORE INTO routes (origin, destination, base_price_per_kg, transit_days) VALUES
('JFK', 'LHR', 2.50, 1),
('JFK', 'CDG', 2.60, 1),
('JFK', 'FRA', 2.55, 1),
('LAX', 'NRT', 3.20, 2),
('LAX', 'HKG', 3.50, 2),
('LAX', 'SYD', 4.00, 3),
('ORD', 'LHR', 2.45, 1),
('ORD', 'FRA', 2.50, 1),
('DFW', 'CDG', 2.70, 1),
('ATL', 'LHR', 2.40, 1),
('LHR', 'JFK', 2.50, 1),
('LHR', 'DXB', 2.80, 2),
('LHR', 'SIN', 3.80, 3),
('FRA', 'PVG', 3.60, 2),
('FRA', 'HKG', 3.70, 2),
('CDG', 'JFK', 2.60, 1),
('DXB', 'BOM', 2.20, 1),
('DXB', 'SIN', 3.00, 2),
('SIN', 'SYD', 3.20, 2),
('HKG', 'LAX', 3.50, 2),
('NRT', 'LAX', 3.20, 2),
('SYD', 'LAX', 4.00, 3);
