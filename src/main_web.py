import os
import argparse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path

from src. api. routes import router as api_router
from src. core. task_manager import TaskManager
from src. core. jobs import run_collection_job

# Background scheduler setup
scheduler = BackgroundScheduler()

def sync_scheduler_jobs(task_manager: TaskManager):
    """同步文件系统中的 Markdown 任务到 APScheduler 中"""
    scheduler.remove_all_jobs()
    tasks = task_manager.get_tasks()
    for task in tasks:
        if task['is_active']:
            print(f"Syncing Cron Job: Task {task['id']} - {task['name']} -> {task['cron']}")
            # 解析非常简单的 cron, 例如 "0 8 * * *" (分 时 日 月 星期)
            parts = task['cron'].split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                scheduler.add_job(
                    run_collection_job, 
                    'cron', 
                    minute=minute, 
                    hour=hour, 
                    day=day, 
                    month=month, 
                    day_of_week=day_of_week, 
                    id=f'task_{task["id"]}',
                    args=[task['name']]
                )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Starting background scheduler...")
    base_dir = Path(__file__).resolve().parent
    tm = TaskManager(base_dir=str(base_dir.parent))
    
    sync_scheduler_jobs(tm)
    scheduler.start()
    
    yield
    
    # Shutdown actions
    scheduler.shutdown()

# Initialize FastAPI App
app = FastAPI(title="Scout Web Dashboard", lifespan=lifespan)

# Mount static files
base_dir = Path(__file__).resolve().parent
static_dir = base_dir / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include Routers
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main_web:app", host="0.0.0.0", port=8000, reload=True)
