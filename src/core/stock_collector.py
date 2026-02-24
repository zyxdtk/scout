from datetime import datetime
from typing import List
import time
import feedparser
from email.utils import parsedate_tz, mktime_tz

from src.core.base_collector import BaseCollector, ScrapedItem

class StockCollector(BaseCollector):
    """
    搜集关注的股票相关的最新新闻 (通过 Yahoo Finance RSS)
    """

    def __init__(self, tickers: List[str], max_news_per_ticker: int = 5):
        self.tickers = tickers
        self.max_news_per_ticker = max_news_per_ticker

    def fetch(self) -> List[ScrapedItem]:
        items = []
        for ticker in self.tickers:
            try:
                # Yahoo Finance RSS url
                rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
                feed = feedparser.parse(rss_url)
                
                if not feed.entries:
                    print(f"No news found for ticker {ticker} in RSS feed.")
                    continue
                    
                for idx, entry in enumerate(feed.entries):
                    if idx >= self.max_news_per_ticker:
                        break
                        
                    # Parse RSS timestamp
                    publish_time = datetime.now()
                    if hasattr(entry, 'published'):
                        parsed_time = parsedate_tz(entry.published)
                        if parsed_time:
                            timestamp = mktime_tz(parsed_time)
                            publish_time = datetime.fromtimestamp(timestamp)
                            
                    news_url = entry.link if hasattr(entry, 'link') else ""
                    if not news_url:
                        continue
                        
                    title = f"[{ticker}] " + (entry.title if hasattr(entry, 'title') else "No Title")
                    summary = entry.summary if hasattr(entry, 'summary') else title
                    
                    item = ScrapedItem(
                        id=news_url,
                        source="stock_news",
                        title=title,
                        content=summary, 
                        url=news_url, # type: ignore
                        publish_time=publish_time,
                        author="Yahoo Finance",
                        tags=[ticker, "finance"],
                        raw_data={"ticker": ticker}
                    )
                    items.append(item)
                    
            except Exception as e:
                print(f"Error fetching RSS for ticker {ticker}: {e}")
                
            # Be nice to Yahoo servers
            time.sleep(1)
                
        return items

# Usage Demo
if __name__ == '__main__':
    collector = StockCollector(tickers=["NVDA", "AAPL"], max_news_per_ticker=2)
    news_items = collector.fetch()
    for item in news_items:
        print(f"[{item.publish_time}] {item.title}\n{item.url}\n")
