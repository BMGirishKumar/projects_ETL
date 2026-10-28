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