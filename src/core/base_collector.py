import abc
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field

class ScrapedItem(BaseModel):
    """
    统一的采集信息结构体
    所有采集器输出的数据必须包装成这个类型，方便下游做去重和 LLM 处理
    """
    id: str = Field(description="全局唯一ID，用于去重，如 url 或 arxiv_id")
    source: str = Field(description="来源渠道，如 'arxiv', 'x.com', 'stock_news'")
    title: str = Field(description="标题")
    content: str = Field(description="内容主体（摘要或正文）")
    url: HttpUrl = Field(description="原文链接")
    publish_time: datetime = Field(description="发布时间")
    author: str = Field(default="", description="作者/发布者")
    tags: List[str] = Field(default_factory=list, description="原始标签集")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="采集到的其他原始信息，备用")

class BaseCollector(abc.ABC):
    """
    搜集器抽象基类
    """
    @abc.abstractmethod
    def fetch(self) -> List[ScrapedItem]:
        """
        执行采集逻辑
        返回 ScrapedItem 列表
        """
        pass
