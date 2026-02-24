# Scout 🔭

> **自动化 AI 情报官** — 专为技术人打造的智能信息聚合与深度精读系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 项目简介

Scout 是一个**完全自动化**的信息搜集与处理系统，专为算法工程师等技术人员设计。它以 **Agentic 模式**驱动，能够自动从多个异构数据源（Arxiv、X/Twitter 等）获取最新资讯，使用 LLM 进行智能筛选与总结，并通过精致的 Web UI 将结果呈现给你。

```
📥 数据源 (Arxiv / X / Web)
      ↓
🤖 Agent 执行层 (Skills & Tools)
      ↓
🧠 LLM 智能筛选与摘要
      ↓
💾 结构化存储 (SQLite + Markdown)
      ↓
🌐 Web UI 可视化阅读
```

---

## ✨ 核心特性

| 特性 | 描述 |
|---|---|
| 🤖 **Agentic 驱动** | Agent 接收任务指令，自主决策并编排 Skills，无需硬编码流程 |
| 📚 **多源采集** | 支持 Arxiv、X (Twitter)、通用网页爬取、RSS 等异构数据源 |
| 🧠 **LLM 智能处理** | 兼容 OpenAI 标准接口，自动过滤噪音、生成 Markdown 结构化摘要 |
| 🗓️ **定时调度** | 基于 Cron 自动执行，也可以 Web 手动触发任务 |
| 🌐 **精致 Web UI** | 每日简报、执行报告双页面，点赞/踩反馈训练个人偏好 |
| 🔄 **数据一致性** | 启动时自动检查 DB 与磁盘文件一致性，支持一键修复 |

---

## 🏗️ 系统架构

```
scout/
├── config/
│   ├── config.yaml          # 主配置（LLM API Key 等，不入库）
│   ├── config.yaml.example  # 配置模板
│   ├── agents.md            # Agent 行为指令与报告格式定义
│   ├── skills.yaml          # Skills 注册表（采集 SOP 定义）
│   └── tools.yaml           # Tools 注册表（原子能力定义）
├── src/
│   ├── core/
│   │   ├── agent_executor.py    # Agentic 执行引擎
│   │   ├── llm_summarizer.py   # LLM 摘要与相关度评分
│   │   ├── state_manager.py    # SQLite 状态管理与去重
│   │   ├── task_manager.py     # 任务加载与调度管理
│   │   ├── skills/             # 高层技能 (SOP: X 采集、论文追踪等)
│   │   └── tools/              # 原子工具 (搜索、爬取、存储等)
│   ├── api/
│   │   └── routes.py           # FastAPI 路由层
│   └── web/
│       └── templates/          # Jinja2 前端模板
├── data/
│   ├── tasks/       # 任务定义 Markdown 文件
│   ├── daily/       # 每日筛选后的 JSON 数据项
│   └── reports/     # Agent 执行后的 Markdown 汇总报告
├── tests/           # 单元测试
├── scripts/         # 维护脚本 (DB 同步等)
└── start.sh         # 服务管理脚本
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/zyxdtk/scout.git
cd scout
```

### 2. 安装依赖

> 项目使用 [uv](https://github.com/astral-sh/uv) 管理环境，请先安装 uv。

```bash
uv venv
uv sync
```

### 3. 配置 API Key

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，填写你的 LLM API 信息：

```yaml
llm:
  api_key: "sk-your-api-key-here"       # 你的 OpenAI 或兼容接口的 Key
  base_url: "https://api.openai.com/v1" # API 地址
  model_name: "gpt-4o"                  # 使用的模型
  timeout: 30
```

### 4. 启动服务

```bash
./start.sh
```

服务启动后访问：**http://127.0.0.1:8000**

---

## 📋 服务管理

```bash
./start.sh          # 启动（若已在运行则提示重启/停止）
./start.sh stop     # 停止服务
./start.sh restart  # 重启服务
./start.sh status   # 查看运行状态

tail -f logs/scout.log   # 实时查看日志
```

---

## 🛠️ 内置 Skills（采集技能）

| Skill | 描述 | 状态 |
|---|---|---|
| `x_collection_skill` | 采集指定 X (Twitter) 博主的最新推文 | ✅ 已启用 |
| `paper_research_skill` | 追踪 Arxiv 等学术平台的最新论文 | ✅ 已启用 |
| `market_news_skill` | 监控市场新闻与舆情 | 🚧 开发中 |

---

## 📱 Web 功能

### 每日简报 (/)
- 展示 LLM 过滤后认为与用户高度相关的资讯
- 支持按任务和日期筛选
- 支持无限滚动加载
- 支持点赞 👍 / 点踩 👎 反馈

### 执行报告 (/reports)
- 展示 Agent 每次执行后生成的深度汇总报告
- 支持多报告滚动查看（无限滚动）
- 显示统计数据：总抓取量、新发现、优质内容占比、耗时

---

## ⚙️ 添加自定义任务

在 `data/tasks/` 目录下创建一个 Markdown 文件，即可定义新任务：

```markdown
# 追踪 LLM Agent 最新进展

## 调度配置
- cron: "0 9 * * *"   # 每天早 9 点执行

## 任务描述
请追踪 Arxiv 和 X 上关于 LLM Agent 领域的最新进展。
重点关注：多模态、Tool-use、长上下文等方向。
```

---

## 🧪 运行测试

```bash
uv run pytest tests/ -v
```

---

## 📄 License

MIT License © 2026 Scout Contributors
