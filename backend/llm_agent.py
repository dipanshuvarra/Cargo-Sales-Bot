import httpx
import json
from typing import Dict, List, Optional
from pydantic import BaseModel

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral:7b"  # Can be changed to mistral, llama2, etc.

class Intent(BaseModel):
    """Extracted user intent"""
    intent_type: str  # quote, book, cancel, track, clarification, greeting
    confidence: float
    needs_confirmation: bool = False

class Slots(BaseModel):
    """Extracted slot values from user input"""
    origin: Optional[str] = None
    destination: Optional[str] = None
    weight: Optional[float] = None
    volume: Optional[float] = None
    cargo_type: Optional[str] = None
    shipping_date: Optional[str] = None
    booking_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None

class LLMResponse(BaseModel):
    """Structured LLM response"""
    intent: Intent
    slots: Slots
    missing_slots: List[str]
    clarification_question: Optional[str] = None
    response_text: Optional[str] = None

async def call_ollama(prompt: str, system_prompt: str) -> str:
    """
    Call Ollama API for LLM inference.
    
    Args:
        prompt: User prompt
        system_prompt: System instructions
    
    Returns:
        LLM response text
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:",
                    "stream": False,
                    "format": "json"
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            print(f"Ollama API error: {e}")
            raise

async def extract_intent_and_slots(user_message: str, conversation_history: List[Dict] = None) -> LLMResponse:
    """
    Extract intent and slots from user message using Ollama.
    
    This function uses the LLM ONLY for:
    - Understanding user intent
    - Extracting slot values from natural language
    - Identifying missing information
    - Generating clarification questions
    
    The LLM does NOT:
    - Calculate prices
    - Access or modify the database
    - Make booking decisions
    
    Args:
        user_message: User's input message
        conversation_history: Previous conversation context
    
    Returns:
        Structured LLMResponse with intent and slots
    """
    
    # Build conversation context with slot accumulation
    context = ""
    
    if conversation_history:
        # Extract previously mentioned slot values from history
        for msg in conversation_history[-5:]:  # Last 5 messages for better context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context += f"{role}: {content}\n"
    
    system_prompt = """You are an air cargo booking assistant. Your job is to extract intent and information from user messages.

CRITICAL: Use the conversation history to remember information the user has already provided. If the user mentioned origin, destination, weight, cargo type, or date in previous messages, carry those values forward even if not mentioned in the current message.

VALID INTENTS:
- quote: User wants a price quote
- book: User wants to create a booking
- cancel: User wants to cancel a booking
- track: User wants to track a booking
- greeting: User is greeting or making small talk
- clarification: User is answering a follow-up question or providing additional info

VALID CARGO TYPES: general, perishable, hazardous, vehicles, livestock

SLOTS TO EXTRACT:
- origin: Origin city or airport code
- destination: Destination city or airport code
- weight: Weight in tonnes (convert from kg, lbs, tons if needed)
- volume: Volume in cubic meters
- cargo_type: Type of cargo
- shipping_date: Date in YYYY-MM-DD format (if user says "March 15" or similar, convert to 2026-03-15)
- booking_id: Booking reference number
- customer_name: Customer's name
- customer_email: Customer's email

CONTEXT MEMORY RULES:
1. Review the conversation history above
2. Extract ALL slot values mentioned in ANY previous message
3. Combine them with new information from the current message
4. If a slot was filled in a previous turn, include it in the current response
5. Only mark slots as missing if they were NEVER mentioned in the conversation

INTENT DETECTION:
- If user is providing additional info (like answering "March 15" after being asked for a date), set intent to "clarification"
- Carry forward the original intent (quote/book) from context

REQUIRED SLOTS BY INTENT:
- quote needs: origin, destination, weight, cargo_type, shipping_date
- book needs: all quote fields plus customer_name
- cancel needs: booking_id
- track needs: booking_id

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact schema:

{
  "intent": {
    "type": "quote|book|cancel|track|greeting|clarification",
    "confidence": 0.0-1.0,
    "needs_confirmation": false
  },
  "slots": {
    "origin": "string or null",
    "destination": "string or null",
    "weight": number or null,
    "volume": number or null,
    "cargo_type": "string or null",
    "shipping_date": "YYYY-MM-DD or null",
    "booking_id": "string or null",
    "customer_name": "string or null",
    "customer_email": "string or null"
  },
  "missing_slots": ["list", "of", "missing", "required", "slots"],
  "clarification_question": "string or null",
  "response_text": "string or null"
}

IMPORTANT: Return ONLY the JSON object, no other text or explanation."""

    full_prompt = f"{context}\nUser: {user_message}"
    
    print(f"\n{'='*60}")
    print(f"LLM CONTEXT DEBUG")
    print(f"{'='*60}")
    print(f"User message: {user_message}")
    print(f"Conversation history length: {len(conversation_history) if conversation_history else 0}")
    print(f"Context being sent:\n{context[:500] if context else 'No context'}")
    print(f"{'='*60}\n")
    
    try:
        # Call Ollama
        llm_output = await call_ollama(full_prompt, system_prompt)
        print(f"DEBUG: LLM raw output: {llm_output[:500]}")  # Print first 500 chars
        
        # Parse JSON response
        try:
            parsed = json.loads(llm_output)
            print(f"DEBUG: Parsed JSON: {json.dumps(parsed, indent=2)[:500]}")
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from LLM response")
        
        # Validate and construct response with type conversion
        try:
            intent_data = parsed.get("intent", {})
            
            # Ensure all fields are the right type
            if "type" in intent_data:
                intent_data["intent_type"] = str(intent_data["type"])
                del intent_data["type"]  # Remove old key
            else:
                intent_data["intent_type"] = "clarification"
                
            if "confidence" in intent_data:
                try:
                    intent_data["confidence"] = float(intent_data["confidence"])
                except:
                    intent_data["confidence"] = 0.8
            else:
                intent_data["confidence"] = 0.8
                
            if "needs_confirmation" not in intent_data:
                intent_data["needs_confirmation"] = False
            
            intent = Intent(**intent_data)
        except Exception as intent_error:
            print(f"Error creating Intent: {intent_error}")
            print(f"Intent data was: {intent_data}")
            # Fallback intent
            intent = Intent(intent_type="clarification", confidence=0.5, needs_confirmation=False)
        
        # Handle slots with type conversion
        try:
            slots_data = parsed.get("slots", {})
            if "weight" in slots_data and slots_data["weight"] is not None:
                try:
                    slots_data["weight"] = float(slots_data["weight"])
                except:
                    slots_data["weight"] = None
            if "volume" in slots_data and slots_data["volume"] is not None:
                try:
                    slots_data["volume"] = float(slots_data["volume"])
                except:
                    slots_data["volume"] = None
                    
            slots = Slots(**slots_data)
        except Exception as slots_error:
            print(f"Error creating Slots: {slots_error}")
            print(f"Slots data was: {slots_data if 'slots_data' in locals() else 'No data'}")
            # Fallback slots
            slots = Slots()
        missing_slots = parsed.get("missing_slots", [])
        clarification_question = parsed.get("clarification_question")
        response_text = parsed.get("response_text")
        
        print(f"Extracted Intent: {intent.intent_type}")
        print(f"Extracted Slots: {slots.dict(exclude_none=True)}")
        print(f"Missing Slots: {missing_slots}")
        print(f"{'='*60}\n")
        
        return LLMResponse(
            intent=intent,
            slots=slots,
            missing_slots=missing_slots,
            clarification_question=clarification_question,
            response_text=response_text
        )
        
    except Exception as e:
        print(f"Error in LLM processing: {e}")
        print(f"LLM output was: {llm_output if 'llm_output' in locals() else 'No output'}")
        import traceback
        traceback.print_exc()
        # Fallback response
        return LLMResponse(
            intent=Intent(type="clarification", confidence=0.5, needs_confirmation=False),
            slots=Slots(),
            missing_slots=[],
            clarification_question="I'm sorry, I didn't understand that. Could you please rephrase?",
            response_text=None
        )

def generate_response_text(intent_type: str, slots: Slots, additional_info: Dict = None) -> str:
    """
    Generate natural language response based on intent and slots.
    This is simple template-based, not LLM-generated.
    
    Args:
        intent_type: Type of intent
        slots: Extracted slots
        additional_info: Additional context (e.g., price, booking_id)
    
    Returns:
        Response text
    """
    additional_info = additional_info or {}
    
    if intent_type == "quote":
        if additional_info.get("price"):
            return f"Your quote from {slots.origin} to {slots.destination} for {slots.weight} tonnes of {slots.cargo_type} cargo on {slots.shipping_date} is ${additional_info['price']:.2f}. Would you like to book this shipment?"
        else:
            return "I can help you get a quote. I need some information first."
    
    elif intent_type == "book":
        if additional_info.get("booking_id"):
            return f"Great! Your booking has been confirmed. Your booking ID is {additional_info['booking_id']}. You'll receive a confirmation email shortly."
        else:
            return "I'll help you create a booking. Let me confirm the details with you."
    
    elif intent_type == "cancel":
        if additional_info.get("cancelled"):
            return f"Your booking {slots.booking_id} has been cancelled successfully."
        else:
            return f"Are you sure you want to cancel booking {slots.booking_id}? Please confirm."
    
    elif intent_type == "track":
        if additional_info.get("status"):
            return f"Booking {slots.booking_id} status: {additional_info['status']}"
        else:
            return "I'll help you track your booking. What's your booking ID?"
    
    elif intent_type == "greeting":
        return "Hello! I'm your air cargo booking assistant. I can help you get quotes, create bookings, track shipments, or cancel bookings. How can I help you today?"
    
    else:
        return "How can I assist you with your air cargo needs today?"
