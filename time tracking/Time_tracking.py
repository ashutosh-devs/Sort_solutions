from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime
import uuid

app = FastAPI()

class TimeLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Unique ID
    task: str
    start_time: datetime
    end_time: datetime

    # Validate that end_time is after start_time
    @classmethod
    def validate(cls, values):
        if values["end_time"] <= values["start_time"]:
            raise ValueError("end_time must be after start_time")
        return values

# Use a dictionary for fast lookups
time_logs: Dict[str, TimeLog] = {}

@app.post("/logs/", response_model=TimeLog)
def create_time_log(log: TimeLog):
    """Add a new time log with a unique ID."""
    time_logs[log.id] = log
    return log

@app.get("/logs/", response_model=list[TimeLog])
def get_time_logs():
    """Retrieve all time logs."""
    return list(time_logs.values())

@app.get("/logs/{log_id}", response_model=TimeLog)
def get_time_log(log_id: str):
    """Retrieve a single time log by ID."""
    if log_id not in time_logs:
        raise HTTPException(status_code=404, detail="Log not found")
    return time_logs[log_id]

@app.delete("/logs/{log_id}", response_model=TimeLog)
def delete_time_log(log_id: str):
    """Delete a time log by ID."""
    if log_id not in time_logs:
        raise HTTPException(status_code=404, detail="Log not found")
    return time_logs.pop(log_id)

@app.put("/logs/{log_id}", response_model=TimeLog)
def update_time_log(log_id: str, updated_log: TimeLog):
    """Update an existing time log."""
    if log_id not in time_logs:
        raise HTTPException(status_code=404, detail="Log not found")
    
    updated_log.id = log_id  # Keep the same ID
    time_logs[log_id] = updated_log
    return updated_log
