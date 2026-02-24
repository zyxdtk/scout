import os
import re
from pathlib import Path
from typing import List, Dict, Optional

class TaskManager:
    """
    基于 Markdown 文件的任务管理器。
    真正通过 Web 界面新建和管理的编排任务落在 data/tasks/ 目录下。
    文件名即任务名 (*.md)。
    """
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.tasks_dir = self.base_dir / "data" / "tasks"
        self.schedules_path = self.base_dir / "data" / "schedules.json"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._init_schedules()
        
    def _init_schedules(self):
        if not self.schedules_path.exists():
            import json
            self.schedules_path.write_text("{}", encoding='utf-8')

    def _get_all_schedules(self) -> Dict[str, str]:
        import json
        try:
            return json.loads(self.schedules_path.read_text(encoding='utf-8'))
        except:
            return {}

    def _save_schedule(self, name: str, cron: str):
        import json
        schedules = self._get_all_schedules()
        schedules[name] = cron
        self.schedules_path.write_text(json.dumps(schedules, indent=2), encoding='utf-8')

    def get_tasks(self) -> List[Dict]:
        tasks = []
        schedules = self._get_all_schedules()
        for file in self.tasks_dir.glob("*.md"):
            task_name = file.stem
            content = file.read_text(encoding='utf-8')
            
            # 优先从 schedules.json 获取，如果不存在则尝试从内容提取 (后向兼容一次)
            cron = schedules.get(task_name)
            if not cron:
                cron = self._extract_cron(content)
                if cron:
                    self._save_schedule(task_name, cron)
            
            # extract basic task metadata
            tasks.append({
                "id": task_name, # Use name as string identifier for frontend
                "name": task_name,
                "cron": cron if cron else "0 8 * * *",
                "is_active": True,
                "instruction": content
            })
        
        # Sort by name alphabetically
        tasks.sort(key=lambda x: x["name"])
        return tasks

    def _extract_cron(self, content: str) -> Optional[str]:
        # match `cron: "0 8 * * *"` or `cron: 0 8 * * *`
        match = re.search(r'^cron:\s*[\'"]?([^\'\"\n]+)[\'"]?', content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def get_task(self, name: str) -> Optional[Dict]:
        for t in self.get_tasks():
            if t['name'] == name:
                return t
        return None

    def save_task(self, name: str, instruction: str, cron: str = None):
        file_path = self.tasks_dir / f"{name}.md"
        # 移除 instruction 中可能存在的 cron: 行，防止冗余和混淆
        cleaned_instruction = re.sub(r'^cron:\s*.*$', '', instruction, flags=re.MULTILINE).strip()
        file_path.write_text(cleaned_instruction, encoding='utf-8')
        
        if cron:
            self._save_schedule(name, cron)

    def delete_task(self, name: str):
        file_path = self.tasks_dir / f"{name}.md"
        if file_path.exists():
            file_path.unlink()
            
        xml_path = self.tasks_dir / f"{name}_plan.xml"
        if xml_path.exists():
            xml_path.unlink()
            
        # 同时删除调度信息
        import json
        schedules = self._get_all_schedules()
        if name in schedules:
            del schedules[name]
            self.schedules_path.write_text(json.dumps(schedules, indent=2), encoding='utf-8')
