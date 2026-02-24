import requests
from bs4 import BeautifulSoup
from typing import Any, Dict, Optional
from src.core.tools.base_tool import BaseTool

class WebCrawlerTool(BaseTool):
    """
    通过 URL 爬取网页正文内容的工具。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.timeout = self.config.get("timeout", 10)
        self.headers = self.config.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    @property
    def name(self) -> str:
        return "web_crawler_tool"

    @property
    def description(self) -> str:
        return "给定一个网页 URL，爬取并提取网页的正文文本内容。"

    def run(self, url: str, arxiv_smart: bool = False) -> str:
        """
        执行爬取逻辑。
        :param url: 目标 URL
        :param arxiv_smart: 是否开启 Arxiv 智能模式（自动转换 HTML/PDF）
        """
        # 1. 如果开启了 arxiv_smart，且是 Arxiv Abs URL，尝试转换并爬取全文
        if arxiv_smart and "arxiv.org/abs/" in url:
            html_url = url.replace("/abs/", "/html/")
            content = self._fetch_html(html_url)
            
            # 如果 HTML 爬取失败或内容过短，尝试 PDF Fallback
            if not content or "Error crawling" in content or len(content) < 500:
                pdf_url = url.replace("/abs/", "/pdf/") + ".pdf"
                content = self._fetch_pdf(pdf_url)
            return content

        # 2. 普通爬取逻辑
        return self._fetch_html(url)

    def _fetch_html(self, url: str) -> str:
        try:
            verify_ssl = self.config.get("verify_ssl", True)
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=verify_ssl)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)
        except Exception as e:
            return f"Error crawling {url}: {str(e)}"

    def _fetch_pdf(self, url: str) -> str:
        # 为了避免循环依赖，我们在方法内部导入 PDFTool
        from src.core.tools.pdf_tool import PDFTool
        pdf_tool = PDFTool(config=self.config)
        return pdf_tool.run(url)
