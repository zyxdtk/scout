import requests
import pdfplumber
import io
from typing import Any, Dict, Optional
from src.core.tools.base_tool import BaseTool

class PDFTool(BaseTool):
    """
    负责下载 PDF 并提取其文本内容的工具。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.timeout = self.config.get("timeout", 30)
        self.verify_ssl = self.config.get("verify_ssl", False)
        self.headers = self.config.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    @property
    def name(self) -> str:
        return "pdf_tool"

    @property
    def description(self) -> str:
        return "给定 PDF 的 URL，下载并提取其中的文本内容。"

    def run(self, url: str) -> str:
        """
        执行下载与提取逻辑。
        """
        import tempfile
        import os
        
        try:
            # 智能修正 Arxiv PDF 链接 (确保以 .pdf 结尾)
            if "arxiv.org/pdf/" in url and not url.endswith(".pdf"):
                url += ".pdf"
            
            print(f"[PDFTool] Fetching URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 1. 验证 magic bytes
            if not response.content.startswith(b"%PDF-"):
                snippet = response.content[:100].decode(errors='ignore')
                return f"Error: URL {url} did not return a valid PDF. Magic bytes: {snippet}"

            # 2. 写入临时文件以确保兼容性
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            try:
                text_content = ""
                # 1. 优先使用 pdfplumber (通常结构更好)
                with pdfplumber.open(tmp_path) as pdf:
                    pages_text = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            pages_text.append(text)
                    if pages_text:
                        text_content = "\n\n".join(pages_text)
                
                # 2. 如果 pdfplumber 失败 (0 页或无文本)，尝试 pypdf 兜底
                if not text_content:
                    from pypdf import PdfReader
                    reader = PdfReader(tmp_path)
                    pages_text = []
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            pages_text.append(text)
                    if pages_text:
                        text_content = "\n\n".join(pages_text)
                
                if not text_content:
                    return f"Warning: No text could be extracted from {url}. PDF might be scanned/encrypted or unsupported."
                
                return text_content
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            print(f"[PDFTool] Exception: {str(e)}")
            return f"Error processing PDF from {url}: {str(e)}"
