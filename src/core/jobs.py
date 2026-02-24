import os
from pathlib import Path

def run_collection_job(task_name: str):
    """
    代理驱动的任务执行入口。
    现在直接调用 AgentExecutor 来处理从任务解构到执行反馈的全流程。
    """
    print(f"[Job] Starting agentic execution for task='{task_name}'...")
    from src.core.agent_executor import AgentExecutor
    
    executor = AgentExecutor()
    try:
        # 这种方式将原本散落在 jobs.py 里的 XML 解析、Collector 调用等逻辑统统交给 AgentExecutor
        result = executor.execute_task(task_name)
        
        if "error" in result:
            print(f"[Job Error] {result['error']}")
            return

        print(f"[Job] Agentic execution completed for {task_name}.")
        
    except Exception as e:
        print(f"[Job Error] Critical failure in agent executor: {e}")
