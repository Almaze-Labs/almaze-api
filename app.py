# api_server.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import uuid
from typing import Dict, Optional
import gc
import psutil

from agents.compass import compass

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def check_memory_usage(request, call_next):
    # Force garbage collection before processing request
    gc.collect()
    
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # Memory in MB
    
    # If memory usage is too high, refuse new requests
    if mem_before > 900:  # 900MB threshold
        raise HTTPException(
            status_code=503,
            detail="Server is currently overloaded. Please try again later."
        )
    
    response = await call_next(request)
    return response

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# Store active sessions
active_sessions: Dict[str, dict] = {}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize session if it doesn't exist
        if session_id not in active_sessions:
            active_sessions[session_id] = {
            }
        
        # Process message through Compass agent
        response = compass(session_id, request.message)
        # print(response)
        
        # Update session history
        active_sessions[session_id]["history"].append({
            "role": "user",
            "content": request.message
        })
        active_sessions[session_id]["history"].append({
            "role": "assistant",
            "content": response
        })
        
        return ChatResponse(
            response=response,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, port=8000)