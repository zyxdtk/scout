from abc import ABC, abstractmethod
from typing import Any, Dict, List
from src.core.tools.base_tool import BaseTool

class BaseSkill(ABC):
    """
    操作流程基ate (Skill/SOP)。
    负责编排工具完成特定任务流程 (What/Process)。
    """
    def __init__(self, tools: Dict[str, BaseTool], config: Dict[str, Any] = None):
        self.tools = tools
        self.config = config or {}

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        执行 SOP 流程。
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述 (由 Agent 读取)"""
        pass
