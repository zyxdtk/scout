import pytest
from src.core.tools.web_crawler_tool import WebCrawlerTool
from src.core.tools.search_tool import SearchTool
from src.core.tools.rss_tool import RSSTool
from src.core.tools.storage_tool import StorageTool
from src.core.tools.pdf_tool import PDFTool
import os

@pytest.fixture
def storage():
    # 使用临时数据库进行测试
    db_path = "data/test_scout.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    tool = StorageTool(config={"db_path": db_path})
    yield tool
    if os.path.exists(db_path):
         os.remove(db_path)

def test_web_crawler_tool():
    tool = WebCrawlerTool(config={"verify_ssl": False})
    # 测试爬取一个简单的已知网页 (例如 example.com)
    result = tool.run("https://example.com")
    assert "Example Domain" in result
    assert isinstance(result, str)

def test_arxiv_html_crawl():
    """测试具体的 Arxiv HTML 页面爬取"""
    tool = WebCrawlerTool(config={"verify_ssl": False, "timeout": 30})
    url = "https://arxiv.org/html/2602.19128v1"
    result = tool.run(url)
    
    # 基本检查
    assert isinstance(result, str)
    if "Error crawling" in result:
        pytest.skip(f"External Arxiv crawl failed: {result}")
    
    # 检查是否抓取到了内容（通常 HTML 版 Arxiv 会包含 Abstract 或文章标题关键字）
    # 由于是未来日期或特定版本，我们放宽检查，只要不是空且字符数够多
    assert len(result) > 500
    print(f"\n[Arxiv Crawl Success] Length: {len(result)} characters.")

def test_arxiv_abs_to_html_crawl():
    """测试 WebCrawlerTool 的 arxiv_smart 模式"""
    tool = WebCrawlerTool(config={"verify_ssl": False, "timeout": 30})
    # abs_url = "https://arxiv.org/abs/2602.19128v1"
    abs_url = "https://arxiv.org/abs/1804.01653"
    
    # 直接传入 Abstract URL，开启 smart 模式
    result = tool.run(abs_url, arxiv_smart=True)
    
    assert isinstance(result, str)
    if "Error crawling" in result or "Error processing PDF" in result:
        pytest.skip(f"Arxiv smart crawl failed: {result}")
    
    assert len(result) > 500
    # 检查一些通用的 Arxiv/学术关键字 (英文或中文)
    assert "arxiv" in result.lower() or "abstract" in result.lower() or "摘要" in result or "引用" in result
    print(f"\n[Arxiv Smart Success] URL: {abs_url}, Length: {len(result)}")
    # print(result)

def test_pdf_tool():
    """测试 PDFTool 的下载与文本提取功能"""
    tool = PDFTool(config={"verify_ssl": False, "timeout": 30})
    # 使用一个较小的 Arxiv PDF 进行测试
    # pdf_url = "https://arxiv.org/pdf/2602.19128v1.pdf"
    pdf_url = "https://arxiv.org/pdf/1804.01653"
    result = tool.run(pdf_url)
    
    assert isinstance(result, str)
    if "Error processing PDF" in result:
        pytest.skip(f"External PDF processing failed: {result}")
    
    assert len(result) > 1000
    # 检查通用学术关键字
    assert "arxiv" in result.lower() or "摘要" in result or "Abstract" in result
    print(f"\n[PDF Tool Success] Length: {len(result)} characters.")

def test_search_tool():
    tool = SearchTool(config={"verify_ssl": False, "timeout": 30})
    # 在 Arxiv 上搜索 'Agent'
    results = tool.run("Agent", limit=2)
    # 检查是否返回了错误消息而非正常结果
    if isinstance(results, list) and len(results) > 0 and "error" in results[0]:
        pytest.skip(f"Search tool external dependency failed: {results[0]['error']}")
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert "url" in results[0]
    assert "title" in results[0]

def test_rss_tool():
    tool = RSSTool()
    # 采集 Arxiv 的 LLM 论文
    results = tool.run(source="arxiv", query="all:LLM", limit=2)
    if isinstance(results, list) and len(results) > 0 and "error" in results[0]:
        pytest.skip(f"RSS tool external dependency failed: {results[0]['error']}")
        
    assert isinstance(results, list)
    assert len(results) > 0
    assert results[0]["source"] == "arxiv"

def test_storage_tool_deduplication(storage):
    item_id = "test_item_123"
    assert storage.run(action="is_seen", item_id=item_id) is False
    
    # 模拟一个 ScrapedItem 对象（这里简化为具有 id 属性的对象或 Dict，取决于 Tool 的容忍度）
    class MockItem:
        def __init__(self, id, source, title, url, publish_time):
            self.id = id
            self.source = source
            self.title = title
            self.url = url
            self.publish_time = publish_time

    from datetime import datetime
    mock_item = MockItem(id=item_id, source="test", title="Test", url="http://test.com", publish_time=datetime.now())
    
    storage.run(action="save_item", items=[mock_item], task_id="test_task")
    assert storage.run(action="is_seen", item_id=item_id) is True
