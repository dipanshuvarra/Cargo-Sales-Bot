from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Route(Base):
    """Air cargo route with pricing information"""
    __tablename__ = 'routes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    base_price_per_kg = Column(Float, nullable=False)
    transit_days = Column(Integer, nullable=False)

class Booking(Base):
    """Cargo booking with soft delete support via status field"""
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String, unique=True, nullable=False)
    customer_name = Column(String)
    customer_email = Column(String)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    volume = Column(Float)
    cargo_type = Column(String, nullable=False)
    shipping_date = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String, nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    """Request audit log with latency tracking"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    latency_ms = Column(Float, nullable=False)
    request_data = Column(Text)
    response_status = Column(Integer)
    user_message = Column(Text)

# Database setup
DATABASE_URL = "sqlite:///./cargo_assistant.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database with schema and seed data"""
    from sqlalchemy import text
    
    Base.metadata.create_all(bind=engine)
    
    # Execute schema.sql for seed data
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            # Execute each statement separately
            with engine.connect() as conn:
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        conn.execute(text(statement))
                conn.commit()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
