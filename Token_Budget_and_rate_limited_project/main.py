# Import datetime to track timestamps for rate limiting and window calculations
from datetime import datetime, timedelta
# Import typing utilities for structured layout definitions and optional attributes
from typing import List, Optional
# Import core FastAPI components for endpoints, security, dependencies, and exceptions
from fastapi import FastAPI, HTTPException, Depends, Security, status
# Import APIKeyHeader to capture custom authorization keys from HTTP headers
from fastapi.security import APIKeyHeader
# Import Pydantic models to enforce structural validation for inputs and outputs
from pydantic import BaseModel, Field
# Import SQLAlchemy core components to handle local DB infrastructure operations
from sqlalchemy import create_engine, Column, Integer, String, DateTime
# Import database mapping factories to build relational schemas
from sqlalchemy.ext.declarative import declarative_base
# Import transaction runner modules to control active records safely
from sqlalchemy.orm import sessionmaker, Session

# DataBase Setup
DATABASE_URL="sqlite:///memory:"

engine= create_engine(DATABASE_URL,connect_args={"check_same_thread":False})

SessionLocal= sessionmaker(autocommit= False,autoflush= False, bind=engine)

Base=declarative_base()

class UserModel(Base):
    __tablename__ = "ai_users"

    # Unique identity entry code tracking users
    id = Column(Integer, primary_key=True, index=True)
    # The developer's name or team name (e.g., "frontend_team")
    team_name = Column(String, index=True)
    # The secure internal API key passed in headers to unlock access privileges
    api_key = Column(String, unique=True, index=True)
    # Total max allowed tokens this user can consume overall per day
    daily_token_budget = Column(Integer, default=50000)
    # Running count tracking tokens consumed during the current cycle
    tokens_used_today = Column(Integer, default=0)
    # Timestamp tracking the last time this user made an API call (used for rate-limiting cooldowns)
    last_request_time = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db =SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pre-populate our virtual memory database with seed developer profiles on launch
def seed_initial_data():
    db = SessionLocal()
    # Check if data already exists to avoid redundant seed actions
    if db.query(UserModel).count() == 0:
        dev_team = UserModel(
            team_name="DevTeam_Alpha", 
            api_key="sk_alpha_123", 
            daily_token_budget=20000, 
            tokens_used_today=0
        )
        research_team = UserModel(
            team_name="Research_Beta", 
            api_key="sk_beta_456", 
            daily_token_budget=100000, 
            tokens_used_today=95000  # Seeded close to limit to test failure paths
        )
        db.add_all([dev_team, research_team])
        db.commit()
    db.close()

# Execute initial database population sequence
seed_initial_data()



# ==========================================
# 2. PYDANTIC SCHEMAS & SECURITY
# ==========================================

# Formulate standard API header checking for an "X-AI-API-KEY" validation target
API_KEY_NAME = "X-AI-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Schema handling input validation rules when registering new developer tokens
class UserCreate(BaseModel):
    team_name: str = Field(..., example="Data_Science_Squad")
    api_key: str = Field(..., example="sk_ds_789")
    daily_token_budget: int = Field(25000, description="Max allowed tokens per day")

# Data format structuring response payloads returned after registering profiles
class UserResponse(BaseModel):
    id: int
    team_name: str
    daily_token_budget: int
    tokens_used_today: int
    
    class Config:
        from_attributes = True

# Data payload submitted when requesting permission to execute an LLM call
class TokenCheckRequest(BaseModel):
    estimated_tokens: int = Field(..., example=1200, description="Calculated prompt + response tokens")

app =FastAPI(title="AI Token Budget and Rate Limiter Gateway", version="1.0.0")

def verify_api_key(header_key: str = Security(api_key_header), db: Session = Depends(get_db)) -> UserModel:
    if not header_key:
        raise HTTPException(status_code=401, detail="Missing X-AI-API-KEY header credential")
    
    # Query memory tables to verify if the key matches a registered developer profile
    user = db.query(UserModel).filter(UserModel.api_key == header_key).first()
    if not user:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API key entry")
    return user

# Endpoint for onboarding new developer teams into the platform system tracking
@app.post("/admin/users", response_model=UserResponse, status_code=201)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Admin route to register a new team and allocate their daily token budget."""
    existing = db.query(UserModel).filter(UserModel.api_key == user_in.api_key).first()
    if existing:
        raise HTTPException(status_code=400, detail="API key variant token identifier already registered")
        
    db_user = UserModel(
        team_name=user_in.team_name,
        api_key=user_in.api_key,
        daily_token_budget=user_in.daily_token_budget
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/gateway/check-budget")
def check_budget_and_rate_limit(
    request_data: TokenCheckRequest, 
    current_user: UserModel = Depends(verify_api_key), 
    db: Session = Depends(get_db)
):
    """
    Evaluates rate limits (cooldown rules) and updates daily budget thresholds.
    Rejects actions if bounds are crossed.
    """
    current_time = datetime.utcnow()

    # --- RULE 1: RATE LIMIT CHECK (Cooldown Window) ---
    # Enforce a strict 5-second cooldown gap limit between subsequent individual calls to prevent infinite scripting loops
    if current_user.last_request_time:
        time_since_last_call = current_time - current_user.last_request_time
        if time_since_last_call < timedelta(seconds=5):
            seconds_to_wait = 5 - time_since_last_call.seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit triggered. Please wait {seconds_to_wait} more seconds before querying."
            )

    # --- RULE 2: DAILY BUDGET VALUE EVALUATION ---
    # Project potential usage expansion calculations against assigned cap margins
    projected_use = current_user.tokens_used_today + request_data.estimated_tokens
    if projected_use > current_user.daily_token_budget:
        tokens_remaining = current_user.daily_token_budget - current_user.tokens_used_today
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, # 402 is an elegant semantic choice for quota empty scenarios
            detail=f"Quota exhausted! Request requires {request_data.estimated_tokens} tokens, but you only have {tokens_remaining} remaining today."
        )

    # --- UPDATE METRICS LAYER ---
    # If parameters pass validation safely, log execution increments onto memory states
    current_user.tokens_used_today += request_data.estimated_tokens
    current_user.last_request_time = current_time
    
    # Save the execution states to memory layout records
    db.commit()

    return {
        "status": "APPROVED",
        "team": current_user.team_name,
        "tokens_added": request_data.estimated_tokens,
        "total_consumed_today": current_user.tokens_used_today,
        "remaining_budget": current_user.daily_token_budget - current_user.tokens_used_today
    }

# Status endpoint enabling teams to inspect their balances actively
@app.get("/gateway/status", response_model=UserResponse)
def get_my_status(current_user: UserModel = Depends(verify_api_key)):
    """Fetch consumption summaries associated with the validated key."""
    return current_user
