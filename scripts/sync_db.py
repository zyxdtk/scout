import sys
import json
import argparse
from pathlib import Path

# 将 src 目录添加到路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.tools.storage_tool import StorageTool

def main():
    parser = argparse.ArgumentParser(description="Synchronize Database with Disk Files")
    parser.add_argument("--check", action="store_true", help="Check for inconsistencies without applying changes")
    args = parser.parse_args()

    storage = StorageTool()
    
    if args.check:
        print("🔍 Checking for Database-File Inconsistencies...")
        
        # 1. 检查数据项 (Items)
        daily_dir = Path("data/daily")
        disk_ids = set()
        if daily_dir.exists():
            for json_file in daily_dir.rglob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "id" in data:
                            disk_ids.add(data["id"])
                except:
                    continue

        db_ids = set(storage.state_manager.get_all_item_ids())
        orphaned_items = db_ids - disk_ids
        missing_in_db = disk_ids - db_ids
        
        # 2. 检查报告 (Reports)
        reports_dir = Path("data/reports")
        report_inconsistent = False
        if reports_dir.exists():
            for report_file in reports_dir.rglob("summary.md"):
                try:
                    parts = report_file.parts
                    if len(parts) >= 3:
                        task_id = parts[-3]
                        date_str = parts[-2]
                        
                        disk_content = report_file.read_text(encoding='utf-8').strip()
                        db_report = storage.state_manager.get_execution_report(task_id, date_str)
                        db_content = (db_report.get("summary_report", "") if db_report else "").strip()
                        
                        if disk_content != db_content:
                            print(f"❌ Report mismatch: {task_id} on {date_str}")
                            report_inconsistent = True
                except:
                    continue

        if orphaned_items or report_inconsistent or missing_in_db:
            if orphaned_items:
                print(f"❌ Found {len(orphaned_items)} orphaned records in database.")
            if missing_in_db:
                print(f"❌ Found {len(missing_in_db)} disk items missing from database (Auto-repair available).")
            if report_inconsistent:
                print(f"❌ Found inconsistent reports on disk.")
            sys.exit(1)
        else:
            print("✅ Database and Disk are perfectly in sync.")
            sys.exit(0)
    
    # 执行全量同步
    print("🚀 Starting Database-File Synchronization...")
    valid_count = storage.run(action="sync_db")
    
    print(f"✅ Synchronization complete. Pruned orphans and updated reports.")
    print(f"✅ Current valid disk items: {valid_count}")

if __name__ == "__main__":
    main()
