from typing import Any, Dict, List, Optional
from src.core.tools.base_tool import BaseTool
from src.core.state_manager import StateManager
from pathlib import Path
import json
import datetime

class StorageTool(BaseTool):
    """
    负责数据持久化、去重与 Session/Report 存档的工具。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.state_manager = StateManager(db_path=self.config.get("db_path", "data/scout_state.db"))
        self.reports_dir = Path("data/reports")
        self.sessions_dir = Path("data/sessions")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "storage_tool"

    @property
    def description(self) -> str:
        return "负责状态去重、数据持久化（SQLite）以及 Session 和 Report 的文件存档。"

    def _safe_filename(self, text: str) -> str:
        # 简单转换 url/id 为安全的文件名
        if not text: return "unknown"
        valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        filename = ''.join(c for c in text if c in valid_chars)
        return filename[:100] or "unknown_item"

    def run(self, action: str, **kwargs) -> Any:
        """
        支持的 action:
        - is_seen: 检查 ID 是否存在
        - filter_new: 批量过滤新项
        - save_item: 保存单条或多条数据到 DB
        - save_session: 保存执行会话到文件
        - save_report: 保存最终报告到文件
        - save_daily_item: 保存单条数据到 data/daily (供前端/简报展示)
        """
        if action == "is_seen":
            return self.state_manager.is_seen(kwargs.get("item_id"))
        
        elif action == "filter_new":
            return self.state_manager.filter_new_items(kwargs.get("items", []))
        
        elif action == "save_item":
            items = kwargs.get("items", [])
            task_id = kwargs.get("task_id")
            for item in items:
                # kwargs 中可能带有 score, summary, reason
                self.state_manager.mark_as_seen(
                    item, 
                    task_id=task_id,
                    score=kwargs.get("score"),
                    summary=kwargs.get("summary"),
                    reason=kwargs.get("reason")
                )
            return True

        elif action == "save_daily_item":
            task_id = kwargs.get("task_id", "default")
            item = kwargs.get("item", {})
            date_str = kwargs.get("date", datetime.date.today().isoformat())
            
            # 兼容 ScrapedItem 模型或普通 dict
            item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            if not item_id:
                return False
                
            safe_id = self._safe_filename(item_id)
            target_dir = Path("data/daily") / task_id / date_str
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出为 JSON
            json_path = target_dir / f"{safe_id}.json"
            
            # 准备元数据，确保包含用户关心的字段
            export_data = {
                "id": item_id,
                "title": item.get("title") if isinstance(item, dict) else getattr(item, "title", "No Title"),
                "url": item.get("url") if isinstance(item, dict) else getattr(item, "url", ""),
                "source": item.get("source") if isinstance(item, dict) else getattr(item, "source", "unknown"),
                "publish_time": item.get("publish_time") if isinstance(item, dict) else getattr(item, "publish_time", ""),
                "summary": kwargs.get("summary", ""),
                "score": kwargs.get("score", 0),
                "reason": kwargs.get("reason", ""),
                "media": item.get("images", []) if isinstance(item, dict) else getattr(item, "images", [])
            }
            
            # 转换为字符串以便序列化（处理 datetime 等）
            if isinstance(export_data["publish_time"], (datetime.datetime, datetime.date)):
                export_data["publish_time"] = export_data["publish_time"].isoformat()

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return str(json_path)

        elif action == "sync_db":
            """同步数据库与磁盘文件：删除磁盘上不存在的记录，并同步最新的报告内容"""
            daily_dir = Path("data/daily")
            sync_count = 0
            
            # --- 1. 同步数据项 (scraped_items) ---
            valid_ids = []
            reimport_count = 0
            if daily_dir.exists():
                for json_file in daily_dir.rglob("*.json"):
                    try:
                        # 提取路径中的 task_id
                        # json_file.parts: (..., 'data', 'daily', 'task_id', 'date', 'id.json')
                        parts = json_file.parts
                        task_id_from_path = parts[-3] if len(parts) >= 3 else "default"
                        
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            item_id = data.get("id")
                            if item_id:
                                valid_ids.append(item_id)
                                
                                # 检查 DB 是否已存在此 ID
                                if not self.state_manager.is_seen(item_id):
                                    print(f"[StorageTool] Re-importing item {item_id} from disk...")
                                    self.state_manager.upsert_scraped_item(data, task_id=task_id_from_path)
                                    reimport_count += 1
                                    
                    except Exception as e:
                        print(f"[StorageTool] Error reading {json_file}: {e}")
            
            if valid_ids:
                self.state_manager.sync_with_disk_ids(valid_ids)
                sync_count = len(valid_ids)
            
            if reimport_count > 0:
                print(f"[StorageTool] Total re-imported: {reimport_count}")

            # --- 2. 同步报告 (execution_reports) ---
            reports_dir = Path("data/reports")
            if reports_dir.exists():
                # 目录结构: data/reports/{task_id}/{date}/summary.md
                for report_file in reports_dir.rglob("summary.md"):
                    try:
                        # 提取 task_id 和 date
                        # report_file.parts: (..., 'data', 'reports', 'task_id', 'date', 'summary.md')
                        parts = report_file.parts
                        if len(parts) >= 3:
                            task_id = parts[-3]
                            date_str = parts[-2]
                            
                            with open(report_file, "r", encoding="utf-8") as f:
                                disk_content = f.read()
                            
                            # 检查 DB 内容
                            db_report = self.state_manager.get_execution_report(task_id, date_str)
                            db_content = db_report.get("summary_report", "") if db_report else ""
                            
                            if disk_content.strip() != db_content.strip():
                                print(f"[StorageTool] Syncing report for {task_id} on {date_str} from disk...")
                                self.state_manager.update_execution_report_text(task_id, date_str, disk_content)
                    except Exception as e:
                        print(f"[StorageTool] Error syncing report {report_file}: {e}")

            return sync_count

        elif action == "save_session":
            task_id = kwargs.get("task_id", "default")
            session_data = kwargs.get("session_data", {})
            date_str = kwargs.get("date", datetime.date.today().isoformat())
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 路径对齐：data/sessions/{task_id}/{date}/session_{timestamp}.json
            session_path = self.sessions_dir / task_id / date_str / f"session_{timestamp}.json"
            session_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return str(session_path)

        elif action == "save_report":
            task_id = kwargs.get("task_id", "default")
            date_str = kwargs.get("date", datetime.date.today().isoformat())
            content = kwargs.get("content", "")
            report_path = self.reports_dir / task_id / date_str / "summary.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(content)
            return str(report_path)

        else:
            raise ValueError(f"Unsupported action: {action}")
