from typing import Any, Dict, List
from src.core.skills.base_skill import BaseSkill
from src.core.tools.base_tool import BaseTool
import datetime

class PaperResearchSkill(BaseSkill):
    """
    追踪学术论文最新进展的 SOP 技能。
    流程：
    1. 使用 RSSTool (Arxiv) 获取最新论文。
    2. 使用 StorageTool 过滤已读项。
    3. (可选) 使用 WebCrawlerTool 抓取深度内容。
    4. 汇总结果并存入 StorageTool。
    """
    
    @property
    def name(self) -> str:
        return "paper_research_skill"

    @property
    def description(self) -> str:
        return "学术论文追踪 SOP：通过 Arxiv 采集、自动去重、内容提取并生成研究简报。"

    def execute(self, query: str, limit: int = 10, task_id: str = "paper_research") -> Dict[str, Any]:
        """
        执行 SOP。
        """
        results = {
            "task": "paper_research",
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "new_items": [],
            "stats": {"total_fetched": 0, "new_count": 0}
        }

        # 1. 采集
        rss_tool = self.tools.get("rss_tool")
        storage_tool = self.tools.get("storage_tool")
        
        if not rss_tool or not storage_tool:
            return {"error": "Missing required tools: rss_tool or storage_tool"}

        raw_items = rss_tool.run(source="arxiv", query=query, limit=limit)
        
        # 检查工具执行是否出错
        if raw_items and isinstance(raw_items, list) and "error" in raw_items[0]:
            return {"error": f"Tool execution failed: {raw_items[0]['error']}"}

        results["stats"]["total_fetched"] = len(raw_items)

        # 2. 过滤
        # 注意：BaseCollector 的 ScrapedItem 和这里的 Dict 格式需要转换或统一下
        # 这里为了演示，我们假设 StorageTool 能处理这些 Dict 格式（后续需要严谨类型化）
        new_items = []
        for item in raw_items:
            if not storage_tool.run(action="is_seen", item_id=item.get("id")):
                new_items.append(item)
        
        results["stats"]["new_count"] = len(new_items)
        results["new_items"] = new_items

        # 3. 深入提取内容 (Delegate to Smart Tool)
        crawl_tool = self.tools.get("crawl_tool")
        summary_tool = self.tools.get("summary_tool")
        
        if crawl_tool:
            for item in new_items:
                url = item.get("url", "")
                # 使用工具内置的 arxiv_smart 模式
                content = crawl_tool.run(url, arxiv_smart=True)
                
                # 4. 落地单篇“信息卡片” (Phase 16: 全量中文化)
                summary = ""
                if summary_tool:
                    print(f"[PaperResearchSkill] Generating Chinese summary for paper: {item.get('id')}")
                    # 无论长短都通过 SummaryTool 确保翻译/总结
                    summary = summary_tool.run(title=item['title'], content=content or item.get('snippet', ''))
                    item["full_content"] = summary
                else:
                    item["full_content"] = content
                    summary = item.get("snippet", "")

                # 5. 落地单篇“信息卡片” (Phase 15.1)
                storage_tool.run(
                    action="save_daily_item", 
                    task_id=task_id, 
                    item=item, 
                    summary=summary
                )
                
                # 6. 同时同步到 DB (带上摘要)
                storage_tool.run(
                    action="save_item",
                    task_id=task_id,
                    items=[item],
                    summary=summary
                )

        # 7. 汇总报告
        if new_items:
            # 这里简化处理，直接调用 save_report
            report_content = f"# Paper Research Report: {query}\n\n"
            report_content += f"Date: {datetime.date.today()}\n\n"
            for item in new_items:
                report_content += f"### {item['title']}\n- URL: {item['url']}\n"
                if item.get("full_content"):
                     report_content += f"- Content Summary (Chinese): \n\n{item['full_content']}\n\n"
                else:
                     report_content += f"- Summary: {item['snippet']}\n\n"
            
            storage_tool.run(action="save_report", task_id=task_id, content=report_content)
        
        # 8. 保存 Session
        storage_tool.run(action="save_session", task_id=task_id, session_data=results)

        return results
