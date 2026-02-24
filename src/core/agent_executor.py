import re
import json
import requests
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.skills.skill_registry import SkillRegistry
from src.core.state_manager import StateManager

class AgentExecutor:
    """
    Scout 代理执行引擎。
    负责根据 task.md 和 agents.md 编排 Skills 的执行。
    支持原生工具调用 (Tool Calling) 和基于标签的手动解析模式。
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.registry = SkillRegistry()
        self.state_manager = StateManager()
        
        # 加载配置
        with open(self.base_dir / config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        self.llm_cfg = cfg.get("llm", {})
        
        self.api_key = self.llm_cfg.get("api_key")
        self.base_url = self.llm_cfg.get("base_url", "https://api.openai.com/v1")
        self.model_name = self.llm_cfg.get("model_name", "gpt-4o")
        self.use_auto_tools = self.llm_cfg.get("use_auto_tools", True)
        self.timeout = self.llm_cfg.get("timeout", 60)

    def execute_task(self, task_name: str) -> Dict[str, Any]:
        """
        执行特定任务。
        1. 加载 task.md。
        2. 组装系统提示词。
        3. 进入 ReAct 循环或执行计划。
        """
        task_file = self.base_dir / "data" / "tasks" / f"{task_name}.md"
        if not task_file.exists():
            return {"error": f"Task file {task_name}.md not found"}
        
        task_instruction = task_file.read_text(encoding='utf-8')
        
        # 加载系统提示词模板并注入技能列表
        system_prompt_tmpl = (self.base_dir / "config" / "agents.md").read_text(encoding='utf-8')
        skills_desc = self._get_skills_description()
        system_prompt = system_prompt_tmpl.replace("{{SKILLS_LIST}}", skills_desc)
        
        print(f"[AgentExecutor] Starting task: {task_name}")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"任务指示：\n{task_instruction}\n\n当前日期：{datetime.now().strftime('%Y-%m-%d')}"}
        ]
        
        # 执行循环 (限定最大步数防止死循环)
        max_steps = 10
        execution_trace = []
        
        for i in range(max_steps):
            print(f"[AgentExecutor] Step {i+1} calling LLM...")
            llm_response = self._call_llm(messages)
            
            # 保存 LLM 的思考/回复
            messages.append({"role": "assistant", "content": llm_response})
            execution_trace.append({"step": i+1, "assistant": llm_response})
            
            # 解析工具调用
            tool_calls = self._parse_tool_calls(llm_response)
            
            if not tool_calls:
                # 如果没有工具调用，说明 Agent 认为任务已完成或在输出最终结论
                print(f"[AgentExecutor] No tool calls detected. Task might be finished.")
                break
            
            # 执行工具调用并收集结果
            for call in tool_calls:
                skill_name = call['name']
                params = call['params']
                try:
                    skill = self.registry.get_skill(skill_name)
                    if skill:
                        # 注入 task_id (Phase 15.1)
                        params['task_id'] = task_name
                        result = skill.execute(**params)
                        result_str = json.dumps(result, ensure_ascii=False)
                    else:
                        result_str = f"Error: Skill '{skill_name}' not found."
                except Exception as e:
                    result_str = f"Error executing {skill_name}: {str(e)}"
                
                # 截断超大结果，防止 context window 溢出 (例如 1MB 的 PDF 文本)
                if len(result_str) > 10000:
                    print(f"[AgentExecutor] Result too large ({len(result_str)}), truncating...")
                    result_str = result_str[:10000] + "\n\n(结果过长，已截断...)"

                print(f"[AgentExecutor] Result size: {len(result_str)}")
                messages.append({"role": "user", "content": f"技能 {skill_name} 返回结果：\n{result_str}"})
                execution_trace.append({"step": i+1, "tool": skill_name, "result": result_str})

        # 最终总结
        final_report = self._generate_final_report(messages)
        
        # 存入数据库
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.state_manager.save_execution_report(
            task_id=task_name,
            date_str=today_str,
            metadata={"trace": execution_trace, "task": task_name},
            report_text=final_report
        )
        
        return {"task": task_name, "report": final_report, "trace": execution_trace}

    def _get_skills_description(self) -> str:
        import inspect
        desc = ""
        for name, skill in self.registry.skills.items():
            # 获取 execute 方法的签名
            sig = inspect.signature(skill.execute)
            params = []
            for p_name, p in sig.parameters.items():
                if p_name in ['self', 'task_id']: continue
                default = f" (default: {p.default})" if p.default != inspect.Parameter.empty else " (required)"
                params.append(f"{p_name}{default}")
            
            p_desc = ", ".join(params)
            desc += f"- `{name}`: {skill.description}\n  参数: {p_desc}\n"
        return desc

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2
        }
        
        # 如果是 OpenAI 或支持 tools 的模型，且 use_auto_tools=True，可以注入 tools 字段
        # ... (此处待扩展)

        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        解析内容中的工具调用。目前支持 <call name="..." params='...' /> 格式。
        """
        calls = []
        # 正则匹配示例: <call name="x_collection_skill" params='{"user_id": "elonmusk"}' />
        pattern = r'<call\s+name=["\']([^"\']+)["\']\s+params=([\'"])(.*?)\2\s*/>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            skill_name = match[0]
            params_str = match[2]
            try:
                params = json.loads(params_str)
                calls.append({"name": skill_name, "params": params})
            except Exception as e:
                print(f"[AgentExecutor] Failed to parse params for {skill_name}: {params_str}. Error: {e}")
        
        return calls

    def _generate_final_report(self, messages: List[Dict[str, str]]) -> str:
        """
        让模型根据整个执行过程生成一份总结报告。
        """
        summary_prompt = """请根据以上的执行过程和采集到的数据，生成一份最终的任务报告。
报告必须严格遵守以下三部分结构：
1. **运行状态**：简要概括本次任务的执行元数据（如采集时间、总计发现、新内容数等）。
2. **原文列表**：仅列出本次采集到的所有高价值内容的标题和原始链接，保持简洁。
3. **内容总结**：针对上述内容进行深度的中文汇总分析，点出核心价值或趋势。

请直接输出 Markdown 格式的报告内容，不要包含额外的解释。"""
        messages.append({"role": "user", "content": summary_prompt})
        return self._call_llm(messages)
