from typing import Any, Dict, List
from src.core.tools.base_tool import BaseTool
import requests
import xml.etree.ElementTree as ET

class SearchTool(BaseTool):
    """
    通用搜索工具。
    初始版本：优先通过 Arxiv API 进行学术搜索，后续可扩展 Google/Bing。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.arxiv_url = "http://export.arxiv.org/api/query"

    @property
    def name(self) -> str:
        return "search_tool"

    @property
    def description(self) -> str:
        return "给定关键词，在互联网或特定平台（如 Arxiv）搜索相关网页及信息列表。"

    def run(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        执行搜索。目前默认使用 Arxiv 作为学术搜索源。
        """
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit
            }
            # Arxiv API 有时响应较慢，增加超时时间并支持关闭 SSL (若有需要)
            verify_ssl = self.config.get("verify_ssl", True)
            timeout = self.config.get("timeout", 20)
            response = requests.get(self.arxiv_url, params=params, timeout=timeout, verify=verify_ssl)
            response.raise_for_status()
            
            # 解析 Arxiv XML 到通用格式
            root = ET.fromstring(response.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            results = []
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": summary[:200] + "..."
                })
            
            return results
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]
