import os
from fastapi import FastAPI , HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

app=FastAPI(title="Claude-powered Backend API")
client=AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class ChatRequest(BaseModel):
    prompt:str
    system_instruction:str ="You are a helpful assistant"
    max_tokens: int = 1024          
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response:str

@app.post("/api/chat",response_model=ChatResponse)
async def generate_chat_respose(payload:ChatRequest):
    try:
        message = await client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
            system=payload.system_instruction,
            messages=[
                {"role": "user", "content": payload.prompt}
            ]
        )

        ai_message= message.content.text
        return ChatResponse(response=ai_message)
    except Exception as e:
        raise HTTPException(status_code=500 , detail=str(e))