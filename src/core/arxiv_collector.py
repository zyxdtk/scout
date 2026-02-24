import urllib.request
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import List

from pydantic import HttpUrl

from src.core.base_collector import BaseCollector, ScrapedItem

class ArxivCollector(BaseCollector):
    """
    搜集 ArXiv 上指定关键词的最新论文
    """

    def __init__(self, query: str, max_results: int = 10):
        self.query = query
        self.max_results = max_results
        self.base_url = 'http://export.arxiv.org/api/query?'

    def fetch(self) -> List[ScrapedItem]:
        query_params = {
            'search_query': self.query,
            'start': 0,
            'max_results': self.max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        url = self.base_url + urllib.parse.urlencode(query_params)
        
        try:
            with urllib.request.urlopen(url) as response:
                xml_data = response.read()
        except Exception as e:
            print(f"Error fetching from Arxiv: {e}")
            return []

        root = ET.fromstring(xml_data)
        
        items = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            id_url = entry.find('atom:id', ns).text
            title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
            published_str = entry.find('atom:published', ns).text
            # Arxiv 格式: 2024-03-15T18:00:00Z
            published = datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")
            
            authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
            categories = [cat.get('term') for cat in entry.findall('atom:category', ns)]
            
            # 找到 pdf 链接
            pdf_url = ""
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    pdf_url = link.get('href')
                    break
            
            item = ScrapedItem(
                id=id_url,
                source="arxiv",
                title=title,
                content=summary,
                url=id_url, # type: ignore
                publish_time=published,
                author=", ".join(authors),
                tags=categories,
                raw_data={"pdf_url": pdf_url}
            )
            items.append(item)

        return items

# Usage Demo
if __name__ == '__main__':
    # 搜集 LLM Agent 相关的论文
    collector = ArxivCollector(query='all:"LLM Agent"', max_results=3)
    papers = collector.fetch()
    for paper in papers:
        print(f"[{paper.publish_time}] {paper.title}\n{paper.url}\n")
