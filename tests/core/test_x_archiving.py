import datetime
from src.core.skills.skill_registry import SkillRegistry
from src.core.tools.storage_tool import StorageTool

def test_x_archiving():
    registry = SkillRegistry()
    skill = registry.get_skill("x_collection_skill")
    
    # Run for a real user
    user_id = "elonmusk"
    print(f"Testing X archiving for {user_id}...")
    result = skill.execute(user_id=user_id, limit=2)
    
    print(f"Stats: {result.get('stats')}")
    
    # Check if files exist in data/daily/x_elonmusk/
    import os
    from pathlib import Path
    today = datetime.date.today().isoformat()
    daily_dir = Path(f"data/daily/x_{user_id}/{today}")
    
    if daily_dir.exists():
        files = list(daily_dir.glob("*.json"))
        print(f"Found {len(files)} archived items for {user_id}")
        for f in files[:2]:
            print(f" - {f.name}")
    else:
        print(f"Error: daily_dir {daily_dir} not found!")

if __name__ == "__main__":
    test_x_archiving()
