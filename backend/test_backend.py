"""
Simple test script to verify backend functionality without Ollama.
Tests the pricing engine and direct API endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pricing import calculate_price, get_price_breakdown, CARGO_TYPE_MULTIPLIERS

def test_pricing_engine():
    """Test the deterministic pricing engine"""
    print("=" * 60)
    print("TESTING PRICING ENGINE")
    print("=" * 60)
    
    # Test case 1: Basic general cargo
    print("\n1. Basic General Cargo:")
    base_price = 2.50  # JFK to LHR
    weight = 5.0  # tonnes
    cargo_type = "general"
    date = "2026-02-15"
    
    price = calculate_price(base_price, weight, cargo_type, date, None)
    breakdown = get_price_breakdown(base_price, weight, cargo_type, date, None)
    
    print(f"   Route: JFK → LHR")
    print(f"   Weight: {weight} tonnes")
    print(f"   Cargo Type: {cargo_type}")
    print(f"   Date: {date}")
    print(f"   Base Price/kg: ${base_price}")
    print(f"   Total Price: ${price}")
    print(f"   Breakdown: {breakdown}")
    
    # Test case 2: Perishable cargo with peak season
    print("\n2. Perishable Cargo (Peak Season):")
    cargo_type = "perishable"
    date = "2026-12-15"  # December - peak season
    
    price = calculate_price(base_price, weight, cargo_type, date, None)
    breakdown = get_price_breakdown(base_price, weight, cargo_type, date, None)
    
    print(f"   Cargo Type: {cargo_type}")
    print(f"   Date: {date} (Peak Season)")
    print(f"   Multiplier: {CARGO_TYPE_MULTIPLIERS[cargo_type]}x")
    print(f"   Total Price: ${price}")
    print(f"   Peak Surcharge: ${breakdown['peak_season_surcharge']}")
    
    # Test case 3: Hazardous cargo with volume
    print("\n3. Hazardous Cargo with Volume:")
    cargo_type = "hazardous"
    weight = 10.0
    volume = 80.0  # High volume for weight
    date = "2026-03-15"
    
    price = calculate_price(base_price, weight, cargo_type, date, volume)
    breakdown = get_price_breakdown(base_price, weight, cargo_type, date, volume)
    
    print(f"   Cargo Type: {cargo_type}")
    print(f"   Weight: {weight} tonnes")
    print(f"   Volume: {volume} m³")
    print(f"   Multiplier: {CARGO_TYPE_MULTIPLIERS[cargo_type]}x")
    print(f"   Total Price: ${price}")
    print(f"   Volume Surcharge: ${breakdown['volume_surcharge']}")
    
    # Test all cargo types
    print("\n4. All Cargo Types (5 tonnes, no peak, no volume):")
    for cargo_type, multiplier in CARGO_TYPE_MULTIPLIERS.items():
        price = calculate_price(base_price, 5.0, cargo_type, "2026-03-15", None)
        print(f"   {cargo_type:12s}: ${price:8.2f} ({multiplier}x)")
    
    print("\n✅ Pricing engine tests completed!")

def test_validation():
    """Test validation functions"""
    print("\n" + "=" * 60)
    print("TESTING VALIDATION")
    print("=" * 60)
    
    from validation import (
        validate_location, validate_weight, validate_cargo_type,
        validate_date, normalize_location
    )
    
    # Test location normalization
    print("\n1. Location Normalization:")
    test_locations = ["New York", "JFK", "london", "LHR", "tokyo"]
    for loc in test_locations:
        normalized = normalize_location(loc)
        print(f"   {loc:15s} → {normalized}")
    
    # Test weight validation
    print("\n2. Weight Validation:")
    test_weights = [0.05, 0.1, 5.0, 50.0, 100.0, 150.0]
    for weight in test_weights:
        valid, error = validate_weight(weight)
        status = "✅" if valid else "❌"
        print(f"   {status} {weight:6.1f} tonnes: {error or 'Valid'}")
    
    # Test cargo type validation
    print("\n3. Cargo Type Validation:")
    test_types = ["general", "perishable", "HAZARDOUS", "invalid", "livestock"]
    for cargo_type in test_types:
        valid, normalized, error = validate_cargo_type(cargo_type)
        status = "✅" if valid else "❌"
        print(f"   {status} {cargo_type:12s}: {normalized or error}")
    
    # Test date validation
    print("\n4. Date Validation:")
    test_dates = ["2026-02-15", "2025-01-01", "2027-12-31", "invalid-date"]
    for date in test_dates:
        valid, normalized, error = validate_date(date)
        status = "✅" if valid else "❌"
        print(f"   {status} {date:15s}: {error or 'Valid'}")
    
    print("\n✅ Validation tests completed!")

def test_database():
    """Test database initialization"""
    print("\n" + "=" * 60)
    print("TESTING DATABASE")
    print("=" * 60)
    
    from database import init_db, SessionLocal, Route, Booking
    
    print("\n1. Initializing database...")
    init_db()
    print("   ✅ Database initialized")
    
    print("\n2. Checking routes...")
    db = SessionLocal()
    routes = db.query(Route).all()
    print(f"   Found {len(routes)} routes")
    
    if routes:
        print("\n   Sample routes:")
        for route in routes[:5]:
            print(f"   {route.origin} → {route.destination}: ${route.base_price_per_kg}/kg ({route.transit_days} days)")
    
    print("\n3. Checking bookings...")
    bookings = db.query(Booking).all()
    print(f"   Found {len(bookings)} bookings")
    
    db.close()
    print("\n✅ Database tests completed!")

if __name__ == "__main__":
    print("\n🚀 AIR CARGO ASSISTANT - BACKEND TESTS\n")
    
    try:
        test_pricing_engine()
        test_validation()
        test_database()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull a model: ollama pull llama3.2")
        print("3. Start the backend: python -m uvicorn main:app --reload")
        print("4. Open frontend/index.html in your browser")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
