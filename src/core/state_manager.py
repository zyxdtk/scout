import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional, List, Any

from src.core.base_collector import ScrapedItem

class StateManager:
    """
    状态管理模块，负责已处理信息的去重和持久化。
    使用 SQLite 存储。
    """
    def __init__(self, db_path: str = "data/scout_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_items (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    publish_time TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_liked BOOLEAN DEFAULT NULL,
                    score INTEGER,
                    summary TEXT,
                    reason TEXT
                )
            ''')
            
            # Create execution_reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    summary_report TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(task_id, date)
                )
            ''')
            
            conn.commit()

    def is_seen(self, item_id: str) -> bool:
        """检查某个 ID 是否已经被处理过"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM scraped_items WHERE id = ?', (item_id,))
            return cursor.fetchone() is not None

    def mark_as_seen(self, item: Any, task_id: str = None, score: int = None, summary: str = None, reason: str = None):
        """将物品标记为已处理存入库中，并一并保存大模型的处理结果（如果有）"""
        
        # 兼容 dict 和 object
        is_dict = isinstance(item, dict)
        item_id = item.get("id") if is_dict else getattr(item, "id", None)
        source = item.get("source") if is_dict else getattr(item, "source", "unknown")
        title = item.get("title") if is_dict else getattr(item, "title", "No Title")
        url = item.get("url") if is_dict else getattr(item, "url", "")
        publish_time = item.get("publish_time") if is_dict else getattr(item, "publish_time", None)

        # 格式化时间
        if isinstance(publish_time, (datetime.datetime, datetime.date)):
            publish_time_str = publish_time.isoformat()
        else:
            publish_time_str = str(publish_time) if publish_time else ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO scraped_items 
                (id, task_id, source, title, url, publish_time, score, summary, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                task_id,
                source,
                title,
                str(url),
                publish_time_str,
                score,
                summary,
                reason
            ))
            conn.commit()
            
    def filter_new_items(self, items: List[ScrapedItem]) -> List[ScrapedItem]:
        """批量过滤，返回所有库中没见过的新 Item"""
        return [item for item in items if not self.is_seen(item.id)]

    def record_feedback(self, item_id: str, is_liked: bool):
        """记录用户的赞/踩反馈"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scraped_items SET is_liked = ? WHERE id = ?
            ''', (is_liked, item_id))
            conn.commit()
            
            conn.commit()
            
    def save_execution_report(self, task_id: str, date_str: str, metadata: dict, report_text: str):
        """保存任务执行过程报告（含元数据和总结）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO execution_reports (task_id, date, metadata_json, summary_report)
                VALUES (?, ?, ?, ?)
            ''', (task_id, date_str, json.dumps(metadata), report_text))
            conn.commit()

    def get_execution_report(self, task_id: Optional[str], date_str: str, limit: int = 10, offset: int = 0):
        """获取任务执行详细报告。
        - 若 task_id 有值：精确查找，返回 dict 或 None。
        - 若 task_id 为空：全局分页查询，返回 List[dict]。
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if task_id and len(task_id) > 0:
                # 精确查找：返回单条记录
                cursor.execute('SELECT * FROM execution_reports WHERE task_id = ? AND date = ?', (task_id, date_str))
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    data['metadata'] = json.loads(data.get('metadata_json', '{}'))
                    return data
                return None
            else:
                # 全局查询：分页返回该日期下的所有报告
                cursor.execute(
                    'SELECT * FROM execution_reports WHERE date = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                    (date_str, limit, offset)
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    data = dict(row)
                    data['metadata'] = json.loads(data.get('metadata_json', '{}'))
                    results.append(data)
                return results

    def update_execution_report_text(self, task_id: str, date_str: str, new_text: str):
        """仅更新报告文本内容（当磁盘文件发生变化时同步使用）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 更新 execution_reports
            cursor.execute('''
                UPDATE execution_reports 
                SET summary_report = ? 
                WHERE task_id = ? AND date = ?
            ''', (new_text, task_id, date_str))
            
            # 如果不存在，可能是之前没存入 DB，这里可以选择 INSERT
            if conn.total_changes == 0:
                cursor.execute('''
                    INSERT INTO execution_reports (task_id, date, metadata_json, summary_report)
                    VALUES (?, ?, ?, ?)
                ''', (task_id, date_str, json.dumps({"task": task_id, "source": "disk_sync"}), new_text))

            conn.commit()

    def get_recent_items(self, limit: int = 50, require_summary: bool = True) -> List[dict]:
        """获取最近处理过的前N条记录供界面展示 (Fallback/Legacy)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM scraped_items'
            if require_summary:
                query += ' WHERE summary IS NOT NULL AND score IS NOT NULL AND score >= 60'
                
            query += ' ORDER BY processed_at DESC LIMIT ?'
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def upsert_scraped_item(self, item_data: dict, task_id: str):
        """插入或更新已爬取的项（供从磁盘重导入使用）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO scraped_items 
                (id, task_id, source, title, url, publish_time, score, summary, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_data.get("id"),
                task_id,
                item_data.get("source", "unknown"),
                item_data.get("title", "No Title"),
                item_data.get("url", ""),
                item_data.get("publish_time", ""),
                item_data.get("score"),
                item_data.get("summary", ""),
                item_data.get("reason", "")
            ))
            conn.commit()

    def get_items_by_task_and_date(self, task_id: Optional[str] = None, date_str: Optional[str] = None, limit: int = 20, offset: int = 0, active_task_ids: Optional[List[str]] = None) -> List[dict]:
        """获取按任务和日期筛选的数据集"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM scraped_items WHERE summary IS NOT NULL'
            params = []
            
            if task_id:
                query += ' AND task_id = ?'
                params.append(task_id)
            elif active_task_ids is not None:
                # 如果没有指定特定 task_id，但提供了活跃列表，则仅展示活跃任务的数据
                if not active_task_ids:
                    return [], None # 无活跃任务，直接返回空
                placeholders = ', '.join(['?'] * len(active_task_ids))
                query += f' AND task_id IN ({placeholders})'
                params.extend(active_task_ids)
                
            if date_str:
                query += ' AND date(processed_at) = ?'
                params.append(date_str)
            
            # 这里的过滤条件放宽：只要有摘要且评分 >= 60 或者 评分是 NULL 的都显示
            # 或者直接移除评分硬限制，让用户决定
            # 为了兼容 X 博主内容（通常没评分），允许 NULL
            query += ' AND (score IS NULL OR score >= 60)'
                
            query += ' ORDER BY processed_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_item_ids(self) -> List[str]:
        """获取库中所有的 item ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM scraped_items')
            return [row[0] for row in cursor.fetchall()]

    def sync_with_disk_ids(self, valid_ids: List[str]):
        """
        同步数据库：删除那些不在 valid_ids 列表中的记录。
        用于确保数据库状态与物理文件一致。
        """
        if not valid_ids:
            # 如果没有有效 ID，慎重起见不直接清空，或者根据业务逻辑决定
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 使用占位符批量删除
            placeholders = ', '.join(['?'] * len(valid_ids))
            cursor.execute(f'''
                DELETE FROM scraped_items 
                WHERE id NOT IN ({placeholders})
            ''', tuple(valid_ids))
            
            deleted_count = conn.total_changes
            conn.commit()
            print(f"[StateManager] Pruned {deleted_count} orphaned records from database.")
