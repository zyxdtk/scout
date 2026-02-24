import os
import subprocess
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.core.base_collector import ScrapedItem
from src.core.llm_summarizer import LLMResult

class Publisher:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = Path(docs_dir)
        self.posts_dir = self.docs_dir / "posts"
        self.template_dir = Path("src") / "templates"
        
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_template()
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def _init_template(self):
        """如果模板不存在，创建一个默认的 Markdown 模板"""
        template_path = self.template_dir / "daily_report.md.j2"
        if not template_path.exists():
            default_template = """# {{ date }} - Scout 每日简报

{% if items %}
{% for item, result in items %}
## {{ loop.index }}. [{{ item.title }}]({{ item.url }})
- **来源**: `{{ item.source }}`
- **发布时间**: {{ item.publish_time.strftime('%Y-%m-%d %H:%M') }}
- **相关性得分**: {{ result.score }} / 100

### 核心摘要
> {{ result.summary }}

---
**为什么推荐这篇？**  
*{{ result.reason }}*

[👍 赞](#) | [👎 踩](#)
{% if not loop.last %}

<br>

{% endif %}
{% endfor %}
{% else %}
今天没有发现符合你兴趣的新鲜事。
{% endif %}
"""
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(default_template)

    def publish_daily_report(self, items_with_results: List[tuple[ScrapedItem, LLMResult]]):
        """
        根据当天的分析结果生成当天的 Markdown 简报，并落盘到 docs/posts/ 下。
        """
        if not items_with_results:
            print("No relevant items to publish today.")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 将来源不同的混合在一起排序，或者按照分数排序
        # 这里默认按照分数从高到低排序一下
        sorted_items = sorted(items_with_results, key=lambda x: x[1].score, reverse=True)

        template = self.env.get_template("daily_report.md.j2")
        rendered_md = template.render(
            date=today_str,
            items=sorted_items
        )

        filename = f"{today_str}-Daily-Scout.md"
        filepath = self.posts_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(rendered_md)
            
        print(f"Generated daily report: {filepath}")
        return filepath

    def publish_to_github(self):
        """
        自动执行 git add, commit 和 push，将改变推送到远程 Github 仓库中。
        """
        try:
            print("Committing and pushing generated docs to Git repository...")
            project_dir = self.docs_dir.parent
            
            subprocess.run(["git", "add", "docs/"], cwd=project_dir, check=True)
            
            commit_msg = f"docs: auto-generated daily scout report for {datetime.now().strftime('%Y-%m-%d')}"
            
            # 允许 git commit 空跑（防报错）如果有变更才 commit
            result = subprocess.run(
                ["git", "diff", "--staged", "--quiet"], 
                cwd=project_dir, 
                capture_output=True
            )
            
            if result.returncode == 1: # 1 means there are differences
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_dir, check=True)
                subprocess.run(["git", "push"], cwd=project_dir, check=True)
                print("Successfully pushed to GitHub.")
            else:
                print("No new changes to commit.")
                
        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
