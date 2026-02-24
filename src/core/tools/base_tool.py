from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    原子能力基类 (Tool)。
    负责具体的执行逻辑 (How)。
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # 统一静默 SSL 警告（针对 verify=False 的场景）
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        执行工具的具体逻辑。
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述 (由 Agent 读取)"""
        pass
