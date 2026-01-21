from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

# Valid cargo types
VALID_CARGO_TYPES = {'general', 'perishable', 'hazardous', 'vehicles', 'livestock'}

# Common airport codes and city mappings
LOCATION_MAPPINGS = {
    'new york': 'JFK',
    'nyc': 'JFK',
    'los angeles': 'LAX',
    'la': 'LAX',
    'chicago': 'ORD',
    'dallas': 'DFW',
    'atlanta': 'ATL',
    'london': 'LHR',
    'paris': 'CDG',
    'frankfurt': 'FRA',
    'tokyo': 'NRT',
    'hong kong': 'HKG',
    'sydney': 'SYD',
    'dubai': 'DXB',
    'mumbai': 'BOM',
    'singapore': 'SIN',
    'shanghai': 'PVG',
}

def normalize_location(location: str) -> str:
    """Convert city names to airport codes"""
    location_lower = location.lower().strip()
    
    # Check if it's already an airport code (3 letters)
    if len(location) == 3 and location.isalpha():
        return location.upper()
    
    # Check mappings
    if location_lower in LOCATION_MAPPINGS:
        return LOCATION_MAPPINGS[location_lower]
    
    return location.upper()

def validate_location(location: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate location and normalize to airport code.
    
    Returns:
        (is_valid, normalized_code, error_message)
    """
    if not location or not location.strip():
        return False, None, "Location cannot be empty"
    
    normalized = normalize_location(location)
    
    # Check if it's a valid 3-letter code
    if len(normalized) != 3 or not normalized.isalpha():
        return False, None, f"Invalid location: {location}. Please provide a valid city name or 3-letter airport code."
    
    return True, normalized, None

def validate_weight(weight: float) -> Tuple[bool, Optional[str]]:
    """
    Validate cargo weight in tonnes.
    
    Returns:
        (is_valid, error_message)
    """
    if weight is None:
        return False, "Weight is required"
    
    if weight <= 0:
        return False, "Weight must be greater than 0"
    
    if weight < 0.1:
        return False, "Minimum weight is 0.1 tonnes (100 kg)"
    
    if weight > 100:
        return False, "Maximum weight is 100 tonnes. For larger shipments, please contact us directly."
    
    return True, None

def validate_volume(volume: Optional[float]) -> Tuple[bool, Optional[str]]:
    """
    Validate cargo volume in cubic meters.
    
    Returns:
        (is_valid, error_message)
    """
    if volume is None:
        return True, None  # Volume is optional
    
    if volume <= 0:
        return False, "Volume must be greater than 0"
    
    if volume > 1000:
        return False, "Maximum volume is 1000 cubic meters"
    
    return True, None

def validate_date(date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate shipping date.
    
    Returns:
        (is_valid, normalized_date, error_message)
    """
    if not date_str:
        return False, None, "Shipping date is required"
    
    # Try to parse the date
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return False, None, "Invalid date format. Please use YYYY-MM-DD (e.g., 2026-02-15)"
    
    # Check if date is in the future
    today = datetime.now().date()
    if date_obj.date() < today:
        return False, None, "Shipping date must be in the future"
    
    # Check if date is within 1 year
    max_date = today + timedelta(days=365)
    if date_obj.date() > max_date:
        return False, None, "Shipping date must be within 1 year from today"
    
    return True, date_str, None

def validate_cargo_type(cargo_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate cargo type.
    
    Returns:
        (is_valid, normalized_type, error_message)
    """
    if not cargo_type:
        return False, None, "Cargo type is required"
    
    normalized = cargo_type.lower().strip()
    
    if normalized not in VALID_CARGO_TYPES:
        valid_types = ', '.join(VALID_CARGO_TYPES)
        return False, None, f"Invalid cargo type. Valid types are: {valid_types}"
    
    return True, normalized, None

def validate_route(origin: str, destination: str, db_session) -> Tuple[bool, Optional[str]]:
    """
    Validate that a route exists in the database.
    
    Returns:
        (is_valid, error_message)
    """
    from database import Route
    
    if origin == destination:
        return False, "Origin and destination cannot be the same"
    
    # Check if route exists
    route = db_session.query(Route).filter_by(
        origin=origin,
        destination=destination
    ).first()
    
    if not route:
        return False, f"No route available from {origin} to {destination}. Please check available routes or contact us for custom routing."
    
    return True, None

def validate_booking_id(booking_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate booking ID format.
    
    Returns:
        (is_valid, error_message)
    """
    if not booking_id:
        return False, "Booking ID is required"
    
    # Booking IDs should be alphanumeric
    if not re.match(r'^[A-Z0-9]{6,12}$', booking_id.upper()):
        return False, "Invalid booking ID format"
    
    return True, None
