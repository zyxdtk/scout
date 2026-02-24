from typing import Any, Dict
from src.core.tools.base_tool import BaseTool
from src.core.llm_summarizer import LLMSummarizer

class SummaryTool(BaseTool):
    """
    内容总结与翻译工具。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.summarizer = LLMSummarizer()

    @property
    def name(self) -> str:
        return "summary_tool"

    @property
    def description(self) -> str:
        return "如果你觉得获取到的内容太长，或者原文是英文需要翻译成中文，请调用此工具对内容进行深度总结与翻译。"

    def run(self, title: str, content: str, custom_prompt: str = None) -> str:
        """
        执行总结。
        :param title: 文章标题
        :param content: 原始长文本
        :param custom_prompt: 额外的背景或总结要求
        :return: 中文摘要
        """
        if not content:
            return "Error: No content to summarize."
        
        # 简单判断是否已经是简短摘要
        if len(content) < 300 and not any(ord(c) > 127 for c in content):
            # 虽然短但是全英文，可能也需要翻译
            pass

        return self.summarizer.summarize_long_content(title, content, custom_prompt)
