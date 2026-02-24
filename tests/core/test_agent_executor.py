import pytest
from src.core.agent_executor import AgentExecutor
import os

def test_agent_executor_world_model():
    """
    测试 AgentExecutor 执行 'fetch_world_model_content' 任务。
    注意：这会产生真实的 LLM 调用。
    """
    executor = AgentExecutor()
    task_name = "fetch_world_model_content"
    
    # 运行任务
    # 为了测试，我们可能需要 mock LLM 调用，但这里先尝试真实调用一次看效果
    result = executor.execute_task(task_name)
    
    print("\n--- Final Report ---")
    print(result.get("report", "No report generated"))
    
    assert "error" not in result
    assert "report" in result
    assert len(result["trace"]) > 0

if __name__ == "__main__":
    test_agent_executor_world_model()
