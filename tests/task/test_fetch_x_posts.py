import pytest
from src.core.agent_executor import AgentExecutor
import datetime
from pathlib import Path
import sqlite3

@pytest.fixture(autouse=True)
def cleanup_db():
    """每个测试前清空数据库，确保它是全新的环境"""
    db_path = Path("data/scout_state.db")
    if db_path.exists():
        db_path.unlink()
    yield

def test_fetch_x_posts_task():
    """
    测试 AgentExecutor 执行 'fetch_x_posts' 任务。
    验证：
    1. 任务能正常执行完毕。
    2. 生成了最终执行报告。
    3. 产生了结构化的日常存档文件 (JSON)。
    4. 摘要为中文。
    """
    executor = AgentExecutor()
    task_name = "fetch_x_posts"
    
    result = executor.execute_task(task_name)
    
    # 基本断言
    assert "error" not in result
    assert "report" in result
    assert len(result["trace"]) > 0
    
    # 检查产生的日常存档文件
    today = datetime.date.today().isoformat()
    daily_dir = Path(f"data/daily/{task_name}/{today}")
    
    assert daily_dir.exists(), f"Daily archiving directory {daily_dir} does not exist."
    
    files = list(daily_dir.glob("*.json"))
    assert len(files) > 0, "No JSON item cards were generated."
    
    # 验证第一个文件的内容（检查摘要是否为中文）
    import json
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        summary = data.get("summary", "")
        # 简单校验：摘要应包含中文字符
        import re
        assert re.search(r'[\u4e00-\u9fa5]', summary), f"Summary seems not to be in Chinese: {summary}"

if __name__ == "__main__":
    # 允许手动执行
    pytest.main([__file__])
