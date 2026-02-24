import yaml
import importlib
from typing import Dict, Any, List
from pathlib import Path

from src.core.tools.base_tool import BaseTool
from src.core.skills.base_skill import BaseSkill

class SkillRegistry:
    """
    负责加载和管理所有的 Tools 和 Skills。
    从 config/tools.yaml 和 config/skills.yaml 读取定义。
    """
    def __init__(self, tools_config_path: str = "config/tools.yaml", skills_config_path: str = "config/skills.yaml"):
        self.tools_config_path = Path(tools_config_path)
        self.skills_config_path = Path(skills_config_path)
        self.tools: Dict[str, BaseTool] = {}
        self.skills: Dict[str, BaseSkill] = {}
        self._load_all()

    def _load_all(self):
        # 1. 加载 Tools
        if self.tools_config_path.exists():
            with open(self.tools_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                for tool_def in config.get("tools", []):
                    if tool_def.get("enabled"):
                        self.tools[tool_def["name"]] = self._instantiate_tool(tool_def)

        # 2. 加载 Skills
        if self.skills_config_path.exists():
            with open(self.skills_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                for skill_def in config.get("skills", []):
                    if skill_def.get("enabled"):
                        self.skills[skill_def["name"]] = self._instantiate_skill(skill_def)

    def _instantiate_tool(self, tool_def: Dict[str, Any]) -> BaseTool:
        class_name = tool_def["class"]
        snake_name = self._to_snake_case(class_name)
        module_path = f"src.core.tools.{snake_name}"
        try:
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            return tool_class(config=tool_def.get("config", {}))
        except Exception as e:
            print(f"[SkillRegistry] Error loading tool {class_name} from {module_path}: {e}")
            raise

    def _instantiate_skill(self, skill_def: Dict[str, Any]) -> BaseSkill:
        class_name = skill_def["class"]
        snake_name = self._to_snake_case(class_name)
        module_path = f"src.core.skills.{snake_name}"
        try:
            module = importlib.import_module(module_path)
            skill_class = getattr(module, class_name)
            # 关联工具
            skill_tools = {name: self.tools[name] for name in skill_def.get("tools", []) if name in self.tools}
            return skill_class(tools=skill_tools, config=skill_def.get("config", {}))
        except Exception as e:
            print(f"[SkillRegistry] Error loading skill {class_name} from {module_path}: {e}")
            raise

    def _to_snake_case(self, name: str) -> str:
        import re
        # Handle cases like ArxivArticleTool -> arxiv_article_tool
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-0])([A-Z])', r'\1_\2', s1).lower()

    def get_skill(self, name: str) -> BaseSkill:
        return self.skills.get(name)

    def get_tool(self, name: str) -> BaseTool:
        return self.tools.get(name)
