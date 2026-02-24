import json
import yaml
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from src.core.base_collector import ScrapedItem

class LLMResult(BaseModel):
    is_relevant: bool = Field(description="这篇文章是否符合用户的兴趣和要求")
    score: int = Field(description="文章与用户兴趣的相关度打分 (1-100)")
    reason: str = Field(description="简要解释为什么给出这个相关度判定")
    summary: str = Field(description="生成一两句话的核心中文摘要，支持并建议使用 Markdown 格式（如加粗、列表）以增强可读性，必须用中文")

class LLMSummarizer:
    def __init__(self, config_path: str = "config/config.yaml"):
        # Load user configurations
        path = Path(config_path)
        if not path.exists():
            # Fallback to example if user hasn't created one
            path = Path("config/config.yaml.example")
            
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            
        self.llm_cfg = cfg.get("llm", {})
        self.user_cfg = cfg.get("user_profile", {})
        
        self.api_key = self.llm_cfg.get("api_key", "")
        self.base_url = self.llm_cfg.get("base_url", "https://api.openai.com/v1")
        self.model_name = self.llm_cfg.get("model_name", "gpt-4o")
        self.timeout = self.llm_cfg.get("timeout", 30)

    def _build_prompt(self, item: ScrapedItem, custom_summary_prompt: str = None) -> str:
        role = self.user_cfg.get("role", "工程师")
        interests = ", ".join(self.user_cfg.get("interests", []))
        rules = self.user_cfg.get("filter_rules", {}).get(item.source, "")
        
        user_focus = f"\\n【专属任务要求】：{custom_summary_prompt}" if custom_summary_prompt else ""
        
        prompt = f"""你是一个智能技术咨询助手。你需要帮助一位 {role} 筛选并总结信息。
用户的全局核心兴趣：{interests}
用户的全局过滤要求：{rules}{user_focus}

请分析以下搜集到的文章信息：
标题：{item.title}
来源：{item.source}
作者：{item.author}
时间：{item.publish_time}
原始摘要/内容：{item.content}

请根据用户兴趣和过滤要求，评估这篇文章的相关性。
请用 JSON 格式输出评估结果，包含以下字段：
{{
  "is_relevant": true/false, (布尔值，是否值得推荐给用户)
  "score": (整数 1-100，相关度打分),
  "reason": "(字符串，简短的中文理由说明判断依据)",
  "summary": "(字符串，文章的核心亮点总结，控制在2-3句话，必须用中文。**支持 Markdown 格式**，如使用 **加粗** 强调关键词)"
}}
只输出合法的 JSON 即可，不要输出 Markdown 标记。
"""
        return prompt

    def evaluate_and_summarize(self, item: ScrapedItem, custom_summary_prompt: str = None) -> Optional[LLMResult]:
        """
        调用 LLM API 评价和总结信息
        """
        if not self.api_key or self.api_key.startswith("sk-your-api-key"):
            print("Warning: LLM API key not configured properly. Skipping LLM processing.")
            return None

        prompt = self._build_prompt(item, custom_summary_prompt)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that strictly outputs valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"].strip()
            
            # Remove Markdown fences if the model still returns them
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            parsed = json.loads(content)
            return LLMResult(**parsed)
            
        except Exception as e:
            print(f"Error calling LLM or parsing result for item {item.id}: {e}")
            if response is not None and getattr(response, 'text', None):
                print(f"LLM Response: {response.text}")
            return None

    def generate_daily_summary(self, items_with_scores: list) -> Optional[str]:
        """
        根据当天的优质精选内容生成一段连贯的中文每日大总结
        items_with_scores: [(ScrapedItem, LLMResult), ...]
        """
        if not self.api_key or self.api_key.startswith("sk-your-api-key") or not items_with_scores:
            return None
            
        content_lines = []
        for i, (item, res) in enumerate(items_with_scores, 1):
            content_lines.append(f"{i}. 标题：{item.title}\\n得分：{res.score}\\n摘要：{res.summary}\\n")
            
        prompt = f"""你是一个高级科技和财经分析师。请根据以下今天采集到的高分精选资讯，写一篇中文的「每日大总结报告」。
要求：
1. 语言连贯、富有洞察力，不要仅仅是罗列，要找出这些资讯之间的潜在联系（如果有的话）。
2. 如果资讯跨度很大，可以分点/分板块总结，带上适当的 Emoji 增加趣味性。
3. 长度控制在 300-500 字左右，直接输出 Markdown 格式的报告正文，无需开头问候。

以下是今日精选资讯：
{"".join(content_lines)}
"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a senior analyst that strictly outputs markdown summaries."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"].strip()
            return content
        except Exception as e:
            print(f"Error generating daily summary: {e}")
            return None

    def generate_comprehensive_report(self, meta: dict, items_with_results: list) -> Optional[str]:
        """
        生成包含执行过程和内容精粹的综合日报。
        """
        if not self.api_key or self.api_key.startswith("sk-your-api-key"):
            return "Execution completed. (LLM API not configured for summary)"
            
        # 构建执行过程的可读描述
        sources_desc = []
        for s in meta.get("sources", []):
            sources_desc.append(f"- {s['type']} (Query: {s['query']}): 抓取 {s['fetched']} 条, 其中 {s['new']} 条为新内容")
            
        process_summary = f"""本次任务执行汇总：
- 启动时间：{meta.get('start_time')}
- 结束时间：{meta.get('end_time')}
- 总计抓取：{meta.get('total_fetched')} 条
- 新发现：{meta.get('total_new')} 条
- 高价值内容：{meta.get('total_high_quality')} 条
数据源明细：
{"\n".join(sources_desc)}
"""

        if not items_with_results:
            return process_summary + "\n今日未发现符合评分标准的高价值内容。"

        # 构建内容摘要
        items_content = []
        for it, res in items_with_results:
            items_content.append(f"【{it.title}】(Score: {res.score})\n摘要：{res.summary}")

        system_prompt = "你是一个专业的信息分析官。你需要将今天的任务执行过程和搜集到的高质量信息，整理成一段优美、连贯、且具有洞察力的中文日报报告。"
        prompt = f"""请根据以下素材，写一份当天的任务综述。
要求：
1. 第一部分简单概括工作量（使用了哪些源，发现了多少好东西）。
2. 第二部分是对今日资讯的深度点评（分类总结，点出关键趋势或重要发现）。
3. 语气要客观、专业但亲切。

素材：
{process_summary}

今日高产内容：
{"\n---\n".join(items_content)}
"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"].strip()
            return content
        except Exception as e:
            print(f"Error generating comprehensive report: {e}")
            return process_summary + "\n(内容总结生成失败)"

    def summarize_long_content(self, title: str, content: str, custom_prompt: str = None) -> str:
        """
        专门处理长文本的总结与翻译逻辑。
        """
        if not self.api_key:
            return content[:1000] + "..."

        system_prompt = "你是一个专业的技术翻译与总结助手。你的任务是将长篇幅的技术内容提炼成精华，并统一使用中文输出。"
        
        user_focus = f"\n任务背景：{custom_prompt}" if custom_prompt else ""
        
        prompt = f"""请阅读以下内容并进行深度总结。
标题：{title}
内容详情：
{content[:15000]}  # 限制输入长度，防止 token 溢出

要求：
1. 如果原文是英文，请务必翻译成地道的中文进行总结。
2. 提炼核心观点、技术细节或新闻要点。
3. 如果内容非常长，请按逻辑分点列出（如：核心结论、背景原因、影响意义）。
4. 语言要精炼，总长度控制在 300-600 字以内。
{user_focus}

直接输出中文总结内容，Markdown 格式。不要输出markdown标记
"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error in summarize_long_content: {e}")
            return content[:1000] + "\n\n(总结失败，已截断原始文本)"

    def generate_task_markdown_from_chat(self, user_input: str) -> dict:
# ... (keeping existing methods)
        """
        NLP to Task Config. Converts user's natural language input into a Markdown Task Config.
        """
        if not self.api_key or self.api_key.startswith("sk-your-api-key"):
            raise ValueError("LLM API key not configured properly.")
            
        system_prompt = '''你是一个智能的任务生成助手。
根据用户的自然语言需求，生成任务配置信息。

格式要求：
1. 提炼出一个合法且简短的英文字母任务名称 (name)，类似函数名。
2. 提炼出符合用户需求的 Cron 定时表达式 (cron)。
3. 生成详细的 Markdown 需求分档 (instruction)。注意：instruction 中不要包含 `cron: ...` 行，因为调度信息已经独立出来了。

请严格以 JSON 格式返回：
{
  "name": "fetch_apple_news",
  "cron": "0 8 * * *",
  "instruction": "# 任务目标\n每天早上八点抓取苹果公司的新闻...\n\n## 采集源\n使用 stock_news 采集 AAPL 相关的资讯...\n\n## 过滤要求\n只看财报..."
}
只输出合法 JSON，不包含首尾 markdown codeblock 的反引号修饰。'''
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.2
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"].strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
        except Exception as e:
            print(f"Error in chat-to-markdown: {e}")
            raise e
