import argparse
import os

from src.core.arxiv_collector import ArxivCollector
from src.core.stock_collector import StockCollector
from src.core.state_manager import StateManager
from src.core.llm_summarizer import LLMSummarizer, LLMResult
from src.core.publisher import Publisher

def main():
    parser = argparse.ArgumentParser(description="Scout: Automated Information Collector")
    parser.add_argument("--source", type=str, choices=["arxiv", "stock_news"], required=True, help="Data source to collect from")
    parser.add_argument("--query", type=str, help="Query string for arxiv, or comma-separated tickers for stock_news")
    parser.add_argument("--max", type=int, default=10, help="Max results to fetch per query/ticker")
    parser.add_argument("--push", action="store_true", help="Push the generated markdown to GitHub")
    args = parser.parse_args()

    state_manager = StateManager(db_path=os.path.join(os.path.dirname(__file__), "..", "data", "scout_state.db"))
    
    collector = None
    if args.source == "arxiv":
        if not args.query:
            print("Error: --query is required for arxiv source")
            return
        collector = ArxivCollector(query=args.query, max_results=args.max)
    elif args.source == "stock_news":
        if not args.query:
             print("Error: --query is required for stock_news (e.g. NVDA,AAPL)")
             return
        tickers = [t.strip() for t in args.query.split(",") if t.strip()]
        collector = StockCollector(tickers=tickers, max_news_per_ticker=args.max)
        
    if not collector:
        print(f"Collector for {args.source} not implemented.")
        return

    print(f"Fetching from {args.source}...")
    items = collector.fetch()
    print(f"Fetched {len(items)} items.")

    new_items = state_manager.filter_new_items(items)
    print(f"Found {len(new_items)} new items after deduplication.")

    summarizer = LLMSummarizer()
    publisher = Publisher()
    
    published_items = []
    
    for item in new_items:
        print(f"\n[NEW] {item.title}\n      {item.url}")
        
        # Call LLM logic
        llm_result = summarizer.evaluate_and_summarize(item)
        if llm_result:
            print(f"      => Relevant: {llm_result.is_relevant} | Score: {llm_result.score}")
            print(f"      => Summary: {llm_result.summary}")
            
            # Only generate markdown if strongly relevant
            if llm_result.is_relevant and llm_result.score > 60:
                published_items.append((item, llm_result))
            elif llm_result.score > 75: # in case is_relevant is unexpectedly false but score is high
                 published_items.append((item, llm_result))
        else:
            print("      => Skipping LLM summarization (No API Key or Error)")
            
        state_manager.mark_as_seen(item)
        
    if published_items:
        publisher.publish_daily_report(published_items)
        print("Daily report successfully built.")
        
        if args.push:
            publisher.publish_to_github()

if __name__ == "__main__":
    main()
