import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import yaml

class ConfigAgent:
    """
    负责将大段的 task.md 自然语言转换为结构化的 plan.xml 执行计划
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.tasks_dir = base_dir / "data" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        cfg_path = base_dir / config_path
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            self.llm_cfg = cfg.get("llm", {})
        else:
            self.llm_cfg = {}
            
        self.api_key = self.llm_cfg.get("api_key")
        self.base_url = self.llm_cfg.get("base_url", "https://api.openai.com/v1")
        self.model_name = self.llm_cfg.get("model_name", "gpt-4o")
        self.timeout = self.llm_cfg.get("timeout", 30)

    def generate_plan(self, task_name: str, force: bool = False, output_path: Optional[str] = None) -> Optional[str]:
        """
        读取 data/tasks/{task_name}.md，调用 LLM 生成对应的执行计划。
        如果指定了 output_path，则无视缓存，直接生成到该路径。
        否则默认生成到 data/tasks/{task_name}_plan.xml (带缓存逻辑)。
        """
        md_file = self.tasks_dir / f"{task_name}.md"
        xml_file = Path(output_path) if output_path else self.tasks_dir / f"{task_name}_plan.xml"
        
        if not md_file.exists():
            print(f"[ConfigAgent] Task markdown not found: {md_file}")
            return None
            
        if not output_path and not force and xml_file.exists():
            if xml_file.stat().st_mtime > md_file.stat().st_mtime:
                print(f"[ConfigAgent] Using cached plan.xml for {task_name}")
                return str(xml_file)
                
        # 需要重新生成
        from datetime import datetime
        now = datetime.now()
        current_date_str = now.strftime("%Y-%m-%d")
        
        print(f"[ConfigAgent] Compiling {task_name}.md into plan.xml using LLM (Today is {current_date_str})...")
        content = md_file.read_text(encoding='utf-8')
        
        system_prompt = f'''你是一个顶级的 AI 任务编排配置智能体 (ConfigAgent)。
你有能力将用户的自然语言任务意图，编译成一份结构化的 XML 采集执行计划 (plan.xml)。

当前日期是：{current_date_str}

当前我们支持的底层数据源 (source type) 只有：
    - Arxiv 查询支持日期范围，格式为 `submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]`。
    - 如果用户要求“最近”、“最新”，请根据当前日期计算出起始日期，结束日期使用今天的日期（例如，如果今天是 2024-03-15，则范围为 `[202401010000 TO 202403152359]`）。
2. `stock_news`: 监控相关美股，query 填写以逗号分隔的 Ticker 代码 (如 AAPL,NVDA)。

用户会输入一段完整的 Markdown 格式的需求文档。你需要提取：
1. 需要并排跑多少个数据源？分别是什么？每个数据源所需的 query 关键字和单次抓取的最大数量 (limit) 定为多少？
2. 最后的文章过滤与提纯指令 (summary_prompt) 是什么？你需要用专业、清晰的语言归纳用户的总结要求。

请直接以严格的 XML 格式返回你的计划，不能输出多余字符，务必保证可以用 XML Parser 直接解析。
XML 的 Root 节点为 `<plan>`。

格式示例：
```xml
<plan>
    <sources>
        <source type="arxiv">
            <query>all:"LLM Agent" AND submittedDate:[20240101 TO *]</query>
            <limit>10</limit>
        </source>
        <source type="stock_news">
            <query>TSLA,MSFT</query>
            <limit>5</limit>
        </source>
    </sources>
    <summary_prompt>只提取文章里和 Agent 架构、大模型训练细节直接相关的段落，不相关的段落忽略并打低分。</summary_prompt>
</plan>
```
'''
        if not self.api_key or self.api_key.startswith("sk-your-api-key"):
            print("[ConfigAgent] Error: No valid API key to compile task.")
            raise ValueError("LLM API key not configured properly for ConfigAgent.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"今天是 {current_date_str}。请根据以下完整的任务需求文档 (task.md) 编写执行计划：\n\n{content}"}
            ],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result_json = response.json()
            xml_content = result_json["choices"][0]["message"]["content"].strip()
            
            # Clean up markdown code blocks if any
            if xml_content.startswith("```xml"):
                xml_content = xml_content[6:]
            if xml_content.endswith("```"):
                xml_content = xml_content[:-3]
                
            xml_content = xml_content.strip()
            
            # Simple validation to ensure it's valid XML
            try:
                ET.fromstring(xml_content)
            except ET.ParseError as e:
                print(f"[ConfigAgent] LLM returned invalid XML: {xml_content}\nError: {e}")
                return None
                
            xml_file.write_text(xml_content, encoding='utf-8')
            print(f"[ConfigAgent] Successfully compiled plan for {task_name}.")
            return str(xml_file)
            
        except Exception as e:
            print(f"[ConfigAgent] Error compiling plan: {e}")
            return None
