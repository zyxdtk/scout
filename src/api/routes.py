import os
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path

from src.core.state_manager import StateManager
from src.core.task_manager import TaskManager
from src.core.jobs import run_collection_job

# Setup Jinja2 templates location
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

router = APIRouter()
state_manager = StateManager(db_path=os.path.join(BASE_DIR.parent, "data", "scout_state.db"))
task_manager = TaskManager(base_dir=str(BASE_DIR.parent))

class FeedbackRequest(BaseModel):
    item_id: str
    action: str  # "like" or "dislike"

class TaskRequest(BaseModel):
    name: str
    instruction: str
    cron: str = None

class TaskChatRequest(BaseModel):
    user_input: str

@router.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """渲染仪表盘首页"""
    tasks = task_manager.get_tasks()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "tasks": tasks}
    )

@router.get("/reports", response_class=HTMLResponse)
async def read_reports(request: Request):
    """渲染执行报告页面"""
    tasks = task_manager.get_tasks()
    return templates.TemplateResponse(
        "reports.html",
        {"request": request, "tasks": tasks}
    )

@router.get("/api/items")
async def get_items(
    task_id: str = None,
    date: str = None,
    limit: int = 20,
    offset: int = 0
):
    try:
        # 获取当前活跃的任务列表，用于过滤已删除任务的数据
        tasks = task_manager.get_tasks()
        active_task_ids = [t['id'] for t in tasks]
        
        items = state_manager.get_items_by_task_and_date(
            task_id, 
            date, 
            limit, 
            offset, 
            active_task_ids=active_task_ids
        )
        return JSONResponse(content={
            "status": "success", 
            "items": items
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.get("/api/reports")
async def get_report(task_id: str = None, date: str = None, limit: int = 10, offset: int = 0):
    """获取指定任务和日期的执行简报（支持全局分页）"""
    try:
        from datetime import datetime
        # 如果 task_id 是空字符串，视作 None，触发 StateManager 的全局分页查询逻辑
        if not task_id:
            task_id = None
            
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        result = state_manager.get_execution_report(task_id, date, limit=limit, offset=offset)
        
        if task_id:
            # 精确查询：返回单条 report
            if result:
                return JSONResponse(content={"status": "success", "report": result})
            else:
                return JSONResponse(status_code=404, content={"status": "error", "message": "Report not found"})
        else:
            # 全局查询：返回 reports 列表（空列表也 200 OK）
            return JSONResponse(content={"status": "success", "reports": result, "total": len(result)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.post("/api/feedback")
async def receive_feedback(feedback: FeedbackRequest):
    """接收异步赞/踩反馈"""
    is_liked = True if feedback.action == "like" else False
    
    try:
        state_manager.record_feedback(feedback.item_id, is_liked)
        return JSONResponse(content={"status": "success", "message": f"Recorded {feedback.action} for {feedback.item_id}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.get("/config", response_class=HTMLResponse)
async def read_config(request: Request):
    """渲染任务配置页面"""
    tasks = task_manager.get_tasks()
    return templates.TemplateResponse(
        "config.html",
        {"request": request, "tasks": tasks}
    )

@router.post("/api/tasks")
async def create_task(task: TaskRequest):
    try:
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", task.name):
            return JSONResponse(status_code=400, content={"status": "error", "message": "任务名称只能包含字母、数字和下划线"})
            
        task_manager.save_task(task.name, task.instruction, task.cron)
        
        # 触发 APScheduler 同步
        from src.main_web import sync_scheduler_jobs
        sync_scheduler_jobs(task_manager)
        
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task: TaskRequest):
    try:
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", task.name):
            return JSONResponse(status_code=400, content={"status": "error", "message": "任务名称只能包含字母、数字和下划线"})
            
        if task_id != task.name:
            task_manager.delete_task(task_id)
            
        task_manager.save_task(task.name, task.instruction, task.cron)
        
        # 触发 APScheduler 同步
        from src.main_web import sync_scheduler_jobs
        sync_scheduler_jobs(task_manager)
        
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    try:
        task_manager.delete_task(task_id)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.post("/api/tasks/{task_id}/run")
async def manual_run_task(task_id: str, background_tasks: BackgroundTasks):
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Task not found"})
            
        background_tasks.add_task(run_collection_job, task['name'])
        return JSONResponse(content={"status": "success", "message": "Job dispatched to background"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.post("/api/tasks/chat")
async def chat_to_config(request: TaskChatRequest):
    """大模型对话生成配置"""
    try:
        from src.core.llm_summarizer import LLMSummarizer
        summarizer = LLMSummarizer()
        config_dict = summarizer.generate_task_markdown_from_chat(request.user_input)
        return JSONResponse(content={"status": "success", "data": config_dict})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
