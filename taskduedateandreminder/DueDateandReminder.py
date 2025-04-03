from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta
import smtplib

app = FastAPI()

tasks = {}

class Task(BaseModel):
    title: str
    due_date: datetime
    user_email: str


def send_reminder(email: str, task_title: str):
    print(f"Reminder sent to {email} for task: {task_title}")

@app.post("/create-task/")
def create_task(task: Task, background_tasks: BackgroundTasks):
    task_id = len(tasks) + 1
    tasks[task_id] = task

    
    reminder_time = task.due_date - timedelta(days=1)
    background_tasks.add_task(send_reminder, task.user_email, task.title)

    return {"message": "Task created and reminder scheduled!", "task_id": task_id}

@app.get("/tasks/")
def get_tasks():
    return tasks

@app.post("/complete-task/{task_id}")
def complete_task(task_id: int):
    if task_id in tasks:
        del tasks[task_id]
        return {"message": "Task marked as completed"}
    return {"error": "Task not found"}
