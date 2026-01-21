from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import secrets

from database import get_db, Route, Booking, AuditLog
from pricing import calculate_price, get_price_breakdown
from validation import (
    validate_location, validate_weight, validate_volume,
    validate_date, validate_cargo_type, validate_route, validate_booking_id
)
from llm_agent import extract_intent_and_slots, generate_response_text

router = APIRouter()

# Request/Response models
class QuoteRequest(BaseModel):
    origin: str
    destination: str
    weight: float
    volume: Optional[float] = None
    cargo_type: str
    shipping_date: str

class QuoteResponse(BaseModel):
    origin: str
    destination: str
    weight: float
    cargo_type: str
    shipping_date: str
    price: float
    breakdown: dict
    transit_days: int

class BookingRequest(BaseModel):
    origin: str
    destination: str
    weight: float
    volume: Optional[float] = None
    cargo_type: str
    shipping_date: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    confirmed: bool = False

class BookingResponse(BaseModel):
    booking_id: str
    status: str
    price: float
    message: str

class CancelRequest(BaseModel):
    booking_id: str
    confirmed: bool = False

class TrackResponse(BaseModel):
    booking_id: str
    status: str
    origin: str
    destination: str
    weight: float
    cargo_type: str
    shipping_date: str
    price: float
    created_at: str

class ConversationRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = None
    pending_confirmation: Optional[dict] = None
    accumulated_slots: Optional[dict] = None

class ConversationResponse(BaseModel):
    response: str
    intent: str
    needs_confirmation: bool = False
    confirmation_data: Optional[dict] = None
    data: Optional[dict] = None
    accumulated_slots: Optional[dict] = None

@router.post("/quote", response_model=QuoteResponse)
async def get_quote(request: QuoteRequest, db: Session = Depends(get_db)):
    """
    Get a price quote for air cargo shipment.
    Uses deterministic pricing - no LLM involvement.
    """
    # Validate and normalize origin
    valid, origin, error = validate_location(request.origin)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate and normalize destination
    valid, destination, error = validate_location(request.destination)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate weight
    valid, error = validate_weight(request.weight)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate volume
    valid, error = validate_volume(request.volume)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate date
    valid, normalized_date, error = validate_date(request.shipping_date)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate cargo type
    valid, cargo_type, error = validate_cargo_type(request.cargo_type)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate route exists
    valid, error = validate_route(origin, destination, db)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Get route information
    route = db.query(Route).filter_by(origin=origin, destination=destination).first()
    
    # Calculate price
    price = calculate_price(
        route.base_price_per_kg,
        request.weight,
        cargo_type,
        normalized_date,
        request.volume
    )
    
    # Get breakdown
    breakdown = get_price_breakdown(
        route.base_price_per_kg,
        request.weight,
        cargo_type,
        normalized_date,
        request.volume
    )
    
    return QuoteResponse(
        origin=origin,
        destination=destination,
        weight=request.weight,
        cargo_type=cargo_type,
        shipping_date=normalized_date,
        price=price,
        breakdown=breakdown,
        transit_days=route.transit_days
    )

@router.post("/book", response_model=BookingResponse)
async def create_booking(request: BookingRequest, db: Session = Depends(get_db)):
    """
    Create a new booking.
    Requires explicit confirmation (confirmed=True).
    """
    # Check confirmation
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Booking requires confirmation. Set confirmed=True to proceed."
        )
    
    # Validate all fields (same as quote)
    valid, origin, error = validate_location(request.origin)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, destination, error = validate_location(request.destination)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, error = validate_weight(request.weight)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, error = validate_volume(request.volume)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, normalized_date, error = validate_date(request.shipping_date)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, cargo_type, error = validate_cargo_type(request.cargo_type)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    valid, error = validate_route(origin, destination, db)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Get route and calculate price
    route = db.query(Route).filter_by(origin=origin, destination=destination).first()
    price = calculate_price(
        route.base_price_per_kg,
        request.weight,
        cargo_type,
        normalized_date,
        request.volume
    )
    
    # Generate booking ID
    booking_id = f"CRG{secrets.token_hex(4).upper()}"
    
    # Create booking
    booking = Booking(
        booking_id=booking_id,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        origin=origin,
        destination=destination,
        weight=request.weight,
        volume=request.volume,
        cargo_type=cargo_type,
        shipping_date=normalized_date,
        price=price,
        status='confirmed'
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return BookingResponse(
        booking_id=booking_id,
        status='confirmed',
        price=price,
        message=f"Booking confirmed! Your booking ID is {booking_id}"
    )

@router.post("/cancel")
async def cancel_booking(request: CancelRequest, db: Session = Depends(get_db)):
    """
    Cancel a booking (soft delete).
    Requires explicit confirmation.
    """
    # Check confirmation
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Cancellation requires confirmation. Set confirmed=True to proceed."
        )
    
    # Validate booking ID
    valid, error = validate_booking_id(request.booking_id)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Find booking
    booking = db.query(Booking).filter_by(
        booking_id=request.booking_id.upper()
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status == 'cancelled':
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    
    # Soft delete - update status
    booking.status = 'cancelled'
    booking.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"Booking {request.booking_id} has been cancelled successfully",
        "booking_id": request.booking_id,
        "status": "cancelled"
    }

@router.get("/track/{booking_id}", response_model=TrackResponse)
async def track_booking(booking_id: str, db: Session = Depends(get_db)):
    """
    Track a booking by ID.
    """
    # Validate booking ID
    valid, error = validate_booking_id(booking_id)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Find booking
    booking = db.query(Booking).filter_by(
        booking_id=booking_id.upper()
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return TrackResponse(
        booking_id=booking.booking_id,
        status=booking.status,
        origin=booking.origin,
        destination=booking.destination,
        weight=booking.weight,
        cargo_type=booking.cargo_type,
        shipping_date=booking.shipping_date,
        price=booking.price,
        created_at=booking.created_at.isoformat()
    )

@router.get("/bookings")
async def list_bookings(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all bookings with optional status filter.
    """
    query = db.query(Booking)
    
    if status:
        query = query.filter_by(status=status)
    
    bookings = query.order_by(Booking.created_at.desc()).limit(limit).all()
    
    return {
        "bookings": [
            {
                "booking_id": b.booking_id,
                "status": b.status,
                "origin": b.origin,
                "destination": b.destination,
                "weight": b.weight,
                "cargo_type": b.cargo_type,
                "shipping_date": b.shipping_date,
                "price": b.price,
                "created_at": b.created_at.isoformat()
            }
            for b in bookings
        ],
        "count": len(bookings)
    }

@router.post("/conversation", response_model=ConversationResponse)
async def conversation(request: ConversationRequest, db: Session = Depends(get_db)):
    """
    Main conversational endpoint using LLM for intent/slot extraction.
    
    The LLM extracts intent and slots, then business logic handles the rest.
    """
    # Extract intent and slots using LLM
    llm_response = await extract_intent_and_slots(
        request.message,
        request.conversation_history
    )
    
    
    # Merge extracted slots with accumulated slots
    new_slots = llm_response.slots.dict(exclude_none=True)
    accumulated = request.accumulated_slots or {}
    
    # Update accumulated slots with new values (only if not None)
    for key, value in new_slots.items():
        if value is not None:
            accumulated[key] = value
            
    # Create a Slots object from the merged data
    # We need to import Slots from llm_agent, but it's not exported in __init__
    # So we'll just populate the llm_response.slots object
    for key, value in accumulated.items():
        if hasattr(llm_response.slots, key):
            setattr(llm_response.slots, key, value)
            
    intent_type = llm_response.intent.intent_type
    slots = llm_response.slots
    
    # Handle pending confirmation
    if request.pending_confirmation:
        confirmation_type = request.pending_confirmation.get("type")
        
        # Check if user confirmed
        user_msg_lower = request.message.lower()
        confirmed = any(word in user_msg_lower for word in ["yes", "confirm", "sure", "ok", "proceed"])
        cancelled = any(word in user_msg_lower for word in ["no", "cancel", "stop", "nevermind"])
        
        if confirmed:
            if confirmation_type == "book":
                # Create booking
                booking_data = request.pending_confirmation.get("data", {})
                try:
                    booking_request = BookingRequest(**booking_data, confirmed=True)
                    booking_response = await create_booking(booking_request, db)
                    return ConversationResponse(
                        response=booking_response.message,
                        intent="book",
                        needs_confirmation=False,
                        data={"booking_id": booking_response.booking_id, "price": booking_response.price}
                    )
                except HTTPException as e:
                    return ConversationResponse(
                        response=f"Error creating booking: {e.detail}",
                        intent="book",
                        needs_confirmation=False
                    )
            
            elif confirmation_type == "cancel":
                # Cancel booking
                booking_id = request.pending_confirmation.get("booking_id")
                try:
                    cancel_response = await cancel_booking(
                        CancelRequest(booking_id=booking_id, confirmed=True),
                        db
                    )
                    return ConversationResponse(
                        response=cancel_response["message"],
                        intent="cancel",
                        needs_confirmation=False
                    )
                except HTTPException as e:
                    return ConversationResponse(
                        response=f"Error cancelling booking: {e.detail}",
                        intent="cancel",
                        needs_confirmation=False
                    )
        
        elif cancelled:
            return ConversationResponse(
                response="Okay, I've cancelled that action. How else can I help you?",
                intent="clarification",
                needs_confirmation=False
            )
    
    # Handle different intents
    if intent_type == "greeting":
        return ConversationResponse(
            response="Hello! I'm your air cargo booking assistant. I can help you get quotes, create bookings, track shipments, or cancel bookings. How can I help you today?",
            intent="greeting",
            needs_confirmation=False,
            accumulated_slots=accumulated
        )
    
    elif intent_type == "quote":
        # Check if all required slots are present
        if llm_response.missing_slots:
            # Re-check missing slots against accumulated data
            actually_missing = []
            for slot in llm_response.missing_slots:
                if not accumulated.get(slot):
                    actually_missing.append(slot)
            
            if actually_missing:
                question = llm_response.clarification_question or f"I need some more information. Please provide: {', '.join(actually_missing)}"
                return ConversationResponse(
                    response=question,
                    intent="quote",
                    needs_confirmation=False,
                    data={"accumulated_slots": accumulated},  # Show what we have so far
                    accumulated_slots=accumulated
                )
        
        # Get quote
        try:
            quote_request = QuoteRequest(
                origin=slots.origin,
                destination=slots.destination,
                weight=slots.weight,
                volume=slots.volume,
                cargo_type=slots.cargo_type,
                shipping_date=slots.shipping_date
            )
            quote_response = await get_quote(quote_request, db)
            
            response_text = f"Your quote from {quote_response.origin} to {quote_response.destination} for {quote_response.weight} tonnes of {quote_response.cargo_type} cargo on {quote_response.shipping_date} is ${quote_response.price:.2f} (estimated {quote_response.transit_days} days transit). Would you like to book this shipment?"
            
            return ConversationResponse(
                response=response_text,
                intent="quote",
                needs_confirmation=False,
                data={"price": quote_response.price, "quote": quote_response.dict()},
                accumulated_slots=accumulated
            )
        except HTTPException as e:
            return ConversationResponse(
                response=f"I couldn't generate a quote: {e.detail}",
                intent="quote",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
    
    elif intent_type == "book":
        # Check if all required slots are present
        required_slots = ["origin", "destination", "weight", "cargo_type", "shipping_date"]
        missing = [s for s in required_slots if not getattr(slots, s)]
        
        if missing:
            question = llm_response.clarification_question or f"To create a booking, I need: {', '.join(missing)}"
            return ConversationResponse(
                response=question,
                intent="book",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
        
        # Prepare booking data and ask for confirmation
        booking_data = {
            "origin": slots.origin,
            "destination": slots.destination,
            "weight": slots.weight,
            "volume": slots.volume,
            "cargo_type": slots.cargo_type,
            "shipping_date": slots.shipping_date,
            "customer_name": slots.customer_name,
            "customer_email": slots.customer_email
        }
        
        # Get price for confirmation message
        try:
            quote_request = QuoteRequest(**{k: v for k, v in booking_data.items() if k in QuoteRequest.__fields__})
            quote_response = await get_quote(quote_request, db)
            
            confirmation_msg = f"I'll create a booking from {slots.origin} to {slots.destination} for {slots.weight} tonnes of {slots.cargo_type} cargo on {slots.shipping_date}. The total price is ${quote_response.price:.2f}. Please confirm to proceed."
            
            return ConversationResponse(
                response=confirmation_msg,
                intent="book",
                needs_confirmation=True,
                confirmation_data={"type": "book", "data": booking_data},
                accumulated_slots=accumulated
            )
        except HTTPException as e:
            return ConversationResponse(
                response=f"Error preparing booking: {e.detail}",
                intent="book",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
    
    elif intent_type == "cancel":
        if not slots.booking_id:
            return ConversationResponse(
                response="What's your booking ID?",
                intent="cancel",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
        
        # Ask for confirmation
        return ConversationResponse(
            response=f"Are you sure you want to cancel booking {slots.booking_id}? Please confirm.",
            intent="cancel",
            needs_confirmation=True,
            confirmation_data={"type": "cancel", "booking_id": slots.booking_id},
            accumulated_slots=accumulated
        )
    
    elif intent_type == "track":
        if not slots.booking_id:
            return ConversationResponse(
                response="What's your booking ID?",
                intent="track",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
        
        # Track booking
        try:
            track_response = await track_booking(slots.booking_id, db)
            response_text = f"Booking {track_response.booking_id}: Status is '{track_response.status}'. Route: {track_response.origin} to {track_response.destination}, {track_response.weight} tonnes of {track_response.cargo_type}, shipping on {track_response.shipping_date}. Price: ${track_response.price:.2f}"
            
            return ConversationResponse(
                response=response_text,
                intent="track",
                needs_confirmation=False,
                data=track_response.dict(),
                accumulated_slots=accumulated
            )
        except HTTPException as e:
            return ConversationResponse(
                response=f"Error tracking booking: {e.detail}",
                intent="track",
                needs_confirmation=False,
                accumulated_slots=accumulated
            )
    
    else:
        # Clarification or unknown
        response = llm_response.clarification_question or "I'm not sure I understand. I can help you with quotes, bookings, tracking, or cancellations. What would you like to do?"
        return ConversationResponse(
            response=response,
            intent="clarification",
            needs_confirmation=False,
            accumulated_slots=accumulated
        )
