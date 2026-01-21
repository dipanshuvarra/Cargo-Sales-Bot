# Air Cargo Sales Assistant MVP

A voice-first air cargo booking system with FastAPI backend, SQLite database, and LLM-powered conversation using Ollama.

## Features

- 🎤 **Voice-First Interface**: Web Speech API for natural voice interaction
- 💬 **Conversational AI**: Ollama-powered intent and slot extraction
- 💰 **Deterministic Pricing**: Rule-based pricing engine (no LLM calculations)
- 📦 **Booking Management**: Create, track, and cancel bookings
- ✅ **Confirmation Flows**: Explicit confirmation for critical actions
- 📊 **Audit Logging**: Request latency tracking and audit trails
- 🔒 **Input Validation**: Comprehensive validation for safety

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database with SQLAlchemy ORM
- **Ollama**: Local LLM inference (llama3.2 or mistral)
- **Pydantic**: Data validation

### Frontend
- **Vanilla HTML/CSS/JS**: No framework dependencies
- **Web Speech API**: Voice recognition
- **Glassmorphism UI**: Modern dark mode design

## Prerequisites

1. **Python 3.8+**
2. **Ollama** installed and running
   - Install from: https://ollama.ai
   - Pull a model: `ollama pull llama3.2` or `ollama pull mistral`
3. **Modern browser** (Chrome/Edge recommended for best voice support)

## Installation

### 1. Clone or navigate to project directory

```bash
cd "d:\New folder"
```

### 2. Set up backend

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment (optional)

```bash
# Copy example env file
cp ..\.env.example .env

# Edit .env if you need to change Ollama URL or model
```

### 4. Start Ollama

Make sure Ollama is running with your chosen model:

```bash
# Check if Ollama is running
ollama list

# If not running, start it and pull a model
ollama pull llama3.2
```

## Running the Application

### 1. Start the backend server

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API documentation: http://localhost:8000/docs

### 2. Open the frontend

Simply open `frontend/index.html` in your browser:

```bash
# Windows
start ..\frontend\index.html

# Or manually open frontend/index.html in Chrome/Edge
```

## Usage

### Voice Interaction

1. Click the microphone button
2. Speak your request (e.g., "I need a quote from New York to London for 5 tonnes of general cargo")
3. The system will extract your intent and ask for missing information
4. Confirm bookings and cancellations when prompted

### Text Fallback

Type your requests in the input field if voice is not available.

### Example Queries

**Get a Quote:**
- "I need a quote from JFK to LHR for 5 tonnes of general cargo on 2026-02-15"
- "Quote from New York to London, 3 tonnes perishable, shipping March 1st"

**Create a Booking:**
- "Book this shipment" (after getting a quote)
- "I want to book 10 tonnes of vehicles from LA to Tokyo on 2026-03-20"

**Track a Booking:**
- "Track booking CRG12345678"
- "What's the status of my booking?"

**Cancel a Booking:**
- "Cancel booking CRG12345678"

## API Endpoints

### Conversational Endpoint
- `POST /api/conversation` - Main LLM-powered conversation

### Direct Endpoints
- `POST /api/quote` - Get price quote
- `POST /api/book` - Create booking (requires confirmation)
- `POST /api/cancel` - Cancel booking (requires confirmation)
- `GET /api/track/{booking_id}` - Track booking
- `GET /api/bookings` - List all bookings

## Domain Rules

### Transport Mode
- Air cargo only

### Cargo Types
- `general` - Standard cargo (1.0x multiplier)
- `perishable` - Temperature-sensitive (1.5x multiplier)
- `hazardous` - Dangerous goods (2.0x multiplier)
- `vehicles` - Cars, motorcycles (1.8x multiplier)
- `livestock` - Live animals (2.5x multiplier)

### Pricing Factors
1. Base price per kg (from route)
2. Cargo type multiplier
3. Volume surcharge (if low density)
4. Peak season surcharge (15% during Nov-Dec, Jun-Aug)

### Validation Rules
- Weight: 0.1 to 100 tonnes
- Volume: Up to 1000 cubic meters
- Date: Future dates within 1 year
- Routes: Must exist in database

## Database Schema

### Routes Table
- Available air cargo routes with base pricing
- Seeded with 22 international routes

### Bookings Table
- Soft delete via status field
- Statuses: pending, confirmed, cancelled, archived

### Audit Logs Table
- Request tracking with latency
- Full request/response logging

## Architecture

### LLM Responsibilities (Ollama)
- ✅ Extract user intent
- ✅ Extract slot values from natural language
- ✅ Identify missing information
- ✅ Generate clarification questions
- ❌ **NEVER** calculate prices
- ❌ **NEVER** access database
- ❌ **NEVER** make booking decisions

### Business Logic Responsibilities
- ✅ Deterministic price calculation
- ✅ Input validation
- ✅ Database operations
- ✅ Confirmation flows
- ✅ Audit logging

## Development

### Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI app with middleware
│   ├── database.py          # SQLAlchemy models
│   ├── schema.sql           # Database schema
│   ├── endpoints.py         # API endpoints
│   ├── llm_agent.py         # Ollama integration
│   ├── pricing.py           # Pricing engine
│   ├── validation.py        # Input validation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Main UI
│   ├── style.css            # Styling
│   └── app.js               # Voice + API integration
└── README.md
```

### Adding New Routes

Edit `backend/schema.sql` and add new routes:

```sql
INSERT INTO routes (origin, destination, base_price_per_kg, transit_days) 
VALUES ('ORD', 'NRT', 3.30, 2);
```

Then restart the backend or manually insert into database.

### Changing LLM Model

Edit `.env` or modify `backend/llm_agent.py`:

```python
OLLAMA_MODEL = "mistral"  # or llama2, codellama, etc.
```

## Troubleshooting

### "Ollama API error"
- Ensure Ollama is running: `ollama serve`
- Check model is pulled: `ollama list`
- Verify URL: http://localhost:11434

### "Microphone access denied"
- Enable microphone permissions in browser settings
- Use HTTPS or localhost (required for Web Speech API)

### "No route available"
- Check available routes in database
- Add custom routes via SQL or API

### "Connection failed"
- Ensure backend is running on port 8000
- Check CORS settings if using different domain


## Future Enhancements

- [ ] User authentication
- [ ] Email notifications
- [ ] Payment integration
- [ ] Real-time tracking updates
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Advanced analytics dashboard
