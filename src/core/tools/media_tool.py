import requests
import os
from typing import Any, Dict, Optional
from src.core.tools.base_tool import BaseTool
from pathlib import Path

class MediaTool(BaseTool):
    """
    媒体文件（图片、视频等）下载工具。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_dir = Path(self.config.get("media_dir", "data/media"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = self.config.get("timeout", 20)
        self.headers = self.config.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    @property
    def name(self) -> str:
        return "media_tool"

    @property
    def description(self) -> str:
        return "下载远程媒体文件（如推文图片、外部链接缩略图）并保存到本地。"

    def run(self, url: str, sub_dir: str = "general") -> Dict[str, str]:
        """
        下载并保存媒体文件。
        :param url: 文件远程 URL
        :param sub_dir: 子目录名称（通常是 taskId 或 userId）
        :return: 包含 local_path 和原始 url 的字典，失败时包含 error
        """
        try:
            target_dir = self.base_dir / sub_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            # 获取文件名并进行解码
            import urllib.parse
            import hashlib
            raw_filename = url.split("/")[-1].split("?")[0]
            unquoted_name = urllib.parse.unquote(raw_filename)
            
            # 如果文件名包含路径分隔符（如 Nitter 的 %2F），取最后一段
            filename = unquoted_name.split("/")[-1]
            
            if not filename or "." not in filename:
                filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
            
            # 限制长度
            if len(filename) > 100:
                ext = filename.split(".")[-1]
                filename = filename[:90] + "..." + ext

            local_path = target_dir / filename
            
            # 执行下载
            verify_ssl = self.config.get("verify_ssl", True)
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=verify_ssl, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {
                "url": url,
                "local_path": str(local_path),
                "filename": filename
            }
        except Exception as e:
            return {"url": url, "error": f"Download failed: {str(e)}"}
