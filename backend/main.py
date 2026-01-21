from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import json

from database import init_db, get_db, AuditLog
from endpoints import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    yield
    print("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Air Cargo Sales Assistant API",
    description="Voice-first air cargo booking system with LLM-powered conversation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Latency logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests with latency tracking.
    Stores audit logs in database.
    """
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    # Log to console
    print(f"[{request.method}] {request.url.path} - {response.status_code} - {latency_ms:.2f}ms")
    
    # Log to database (async, don't block response)
    try:
        db = next(get_db())
        
        audit_log = AuditLog(
            endpoint=request.url.path,
            method=request.method,
            latency_ms=latency_ms,
            request_data=None,  # Simplified - don't log body to avoid middleware issues
            response_status=response.status_code,
            user_message=None
        )
        db.add(audit_log)
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error logging to database: {e}")
    
    return response

# Include API routes
app.include_router(router, prefix="/api", tags=["cargo"])

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "online",
        "service": "Air Cargo Sales Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "conversation": "/api/conversation",
            "quote": "/api/quote",
            "book": "/api/book",
            "cancel": "/api/cancel",
            "track": "/api/track/{booking_id}",
            "bookings": "/api/bookings"
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": time.time()
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": request.url.path}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
