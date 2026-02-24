import urllib.request
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from src.core.tools.base_tool import BaseTool

class RSSTool(BaseTool):
    """
    通用 RSS/Atom 采集工具，支持 Arxiv 等源。
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "rss_tool"

    @property
    def description(self) -> str:
        return "从指定的 RSS 或 Atom 源（如 Arxiv）中，根据关键词获取最新的内容列表。"

    def run(self, source: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        执行采集。
        """
        source_lower = source.lower()
        if source_lower == "arxiv":
            return self._fetch_arxiv(query, limit)
        elif source_lower in ["x", "twitter"]:
            # 对于 X，query 通常是博主 ID
            return self._fetch_x(query, limit)
        else:
            return [{"error": f"Source '{source}' is not supported yet."}]

    def _fetch_x(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """
        通过 Nitter RSS 采集 X.com 内容。
        这是一个非常稳健的低频采集方案，避开了 SPA 和 JS 渲染。
        """
        # 公共 Nitter 实例列表 (可以增加更多以实现轮询)
        instances = [
            "https://nitter.net",
            "https://nitter.it",
            "https://nitter.privacydev.net"
        ]
        
        last_error = ""
        for base_url in instances:
            rss_url = f"{base_url}/{user_id}/rss"
            try:
                import ssl
                context = ssl._create_unverified_context()
                # 增加请求头模拟
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                req = urllib.request.Request(rss_url, headers=headers)
                
                with urllib.request.urlopen(req, context=context, timeout=15) as response:
                    xml_data = response.read()
                
                root = ET.fromstring(xml_data)
                items = []
                channel = root.find('channel')
                if channel is None:
                    continue
                
                for entry in channel.findall('item')[:limit]:
                    title = entry.find('title').text if entry.find('title') is not None else ""
                    link = entry.find('link').text if entry.find('link') is not None else ""
                    description = entry.find('description').text if entry.find('description') is not None else ""
                    pub_date_str = entry.find('pubDate').text if entry.find('pubDate') is not None else ""
                    
                    # Nitter RSS 格式: Sat, 16 Mar 2024 12:00:00 GMT
                    try:
                        dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S GMT")
                        published = dt.isoformat()
                    except:
                        published = pub_date_str

                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(description, 'html.parser')
                    
                    # 提取图片
                    images = []
                    for img in soup.find_all('img'):
                        img_url = img.get('src')
                        if img_url:
                            # 转换相对路径为绝对路径 (如果需要)
                            if img_url.startswith('/'):
                                img_url = base_url + img_url
                            images.append(img_url)
                    
                    # 提取外部链接 (排除 nitter 内部链接)
                    external_links = []
                    for a in soup.find_all('a'):
                        href = a.get('href')
                        if href and not href.startswith('/') and base_url not in href:
                            external_links.append(href)

                    items.append({
                        "id": link,
                        "title": title[:100] + "..." if len(title) > 100 else title,
                        "url": link,
                        "snippet": soup.get_text()[:300] + "..." if len(soup.get_text()) > 300 else soup.get_text(),
                        "images": images,
                        "external_links": external_links,
                        "publish_time": published,
                        "source": "x"
                    })
                
                if items:
                    return items
            except Exception as e:
                last_error = str(e)
                continue # 尝试下一个实例
        
        return [{"error": f"Failed to fetch X content for {user_id} from all Nitter instances. Last error: {last_error}"}]

    def _fetch_arxiv(self, query: str, limit: int) -> List[Dict[str, Any]]:
        base_url = 'http://export.arxiv.org/api/query?'
        query_params = {
            'search_query': query,
            'start': 0,
            'max_results': limit,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        url = base_url + urllib.parse.urlencode(query_params)
        
        try:
            # Arxiv 有时需要忽略 SSL 证书校验 (特别是在某些 Mac 环境下)
            import ssl
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context, timeout=20) as response:
                xml_data = response.read()
            
            root = ET.fromstring(xml_data)
            items = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                id_url = entry.find('atom:id', ns).text
                title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
                summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
                published_str = entry.find('atom:published', ns).text
                # Arxiv 格式: 2024-03-15T18:00:00Z
                published = datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ").isoformat()
                
                results = {
                    "id": id_url,
                    "title": title,
                    "url": id_url,
                    "snippet": summary,
                    "publish_time": published,
                    "source": "arxiv"
                }
                items.append(results)
            return items
        except Exception as e:
            return [{"error": f"Arxiv fetch failed: {str(e)}"}]
