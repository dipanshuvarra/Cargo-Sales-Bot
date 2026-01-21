from datetime import datetime
from typing import Optional

# Cargo type pricing multipliers
CARGO_TYPE_MULTIPLIERS = {
    'general': 1.0,
    'perishable': 1.5,
    'hazardous': 2.0,
    'vehicles': 1.8,
    'livestock': 2.5
}

# Peak season date ranges (month ranges)
PEAK_SEASONS = [
    (11, 12),  # November-December (holiday season)
    (6, 8),    # June-August (summer)
]

def calculate_price(
    base_price_per_kg: float,
    weight: float,
    cargo_type: str,
    shipping_date: str,
    volume: Optional[float] = None
) -> float:
    """
    Deterministic pricing calculation based on business rules.
    No LLM involvement - pure rule-based logic.
    
    Args:
        base_price_per_kg: Base price from routes table
        weight: Weight in tonnes
        cargo_type: Type of cargo (general, perishable, hazardous, vehicles, livestock)
        shipping_date: Shipping date (YYYY-MM-DD)
        volume: Volume in cubic meters (optional)
    
    Returns:
        Total price in USD
    """
    # Convert weight from tonnes to kg
    weight_kg = weight * 1000
    
    # Base calculation
    base_cost = base_price_per_kg * weight_kg
    
    # Apply cargo type multiplier
    cargo_multiplier = CARGO_TYPE_MULTIPLIERS.get(cargo_type.lower(), 1.0)
    cost_with_cargo = base_cost * cargo_multiplier
    
    # Volume surcharge if density is low (volume > weight in tonnes * 6)
    volume_surcharge = 0
    if volume and volume > (weight * 6):
        # Charge for volumetric weight
        volumetric_weight_kg = volume * 167  # Standard air cargo conversion
        if volumetric_weight_kg > weight_kg:
            volume_surcharge = (volumetric_weight_kg - weight_kg) * base_price_per_kg * 0.5
    
    # Peak season surcharge
    peak_multiplier = 1.0
    try:
        date_obj = datetime.strptime(shipping_date, '%Y-%m-%d')
        month = date_obj.month
        for start_month, end_month in PEAK_SEASONS:
            if start_month <= month <= end_month:
                peak_multiplier = 1.15  # 15% surcharge
                break
    except ValueError:
        pass  # Invalid date format, skip peak season check
    
    # Final price calculation
    final_price = (cost_with_cargo + volume_surcharge) * peak_multiplier
    
    # Round to 2 decimal places
    return round(final_price, 2)

def get_price_breakdown(
    base_price_per_kg: float,
    weight: float,
    cargo_type: str,
    shipping_date: str,
    volume: Optional[float] = None
) -> dict:
    """
    Get detailed price breakdown for transparency.
    
    Returns:
        Dictionary with price components
    """
    weight_kg = weight * 1000
    base_cost = base_price_per_kg * weight_kg
    cargo_multiplier = CARGO_TYPE_MULTIPLIERS.get(cargo_type.lower(), 1.0)
    
    breakdown = {
        'base_cost': round(base_cost, 2),
        'cargo_type': cargo_type,
        'cargo_multiplier': cargo_multiplier,
        'cargo_surcharge': round(base_cost * (cargo_multiplier - 1), 2),
    }
    
    # Volume surcharge
    volume_surcharge = 0
    if volume and volume > (weight * 6):
        volumetric_weight_kg = volume * 167
        if volumetric_weight_kg > weight_kg:
            volume_surcharge = (volumetric_weight_kg - weight_kg) * base_price_per_kg * 0.5
    breakdown['volume_surcharge'] = round(volume_surcharge, 2)
    
    # Peak season
    peak_multiplier = 1.0
    try:
        date_obj = datetime.strptime(shipping_date, '%Y-%m-%d')
        month = date_obj.month
        for start_month, end_month in PEAK_SEASONS:
            if start_month <= month <= end_month:
                peak_multiplier = 1.15
                break
    except ValueError:
        pass
    
    breakdown['peak_season_multiplier'] = peak_multiplier
    subtotal = (base_cost * cargo_multiplier) + volume_surcharge
    breakdown['peak_season_surcharge'] = round(subtotal * (peak_multiplier - 1), 2)
    breakdown['total'] = round(subtotal * peak_multiplier, 2)
    
    return breakdown
