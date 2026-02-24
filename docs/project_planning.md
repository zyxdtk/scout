# Scout 项目规划文档

## 1. 项目概述 (Project Overview)
**Scout** 是一个自动化的信息搜集与处理系统，专为算法工程师等技术人员设计。旨在自动化地从多个异构数据源获取最新资讯，进行智能筛选和总结，并以 Agent 友好的方式输出结果。

## 2. 核心目标 (Core Objectives)
1. **自动化信息搜集**：定时或按需从指定平台获取最新内容。
2. **智能筛选与总结**：基于大语言模型（LLM）识别与用户（算法工程师）相关性高的内容，并提供结构化总结。
3. **Agent 友好**：系统架构设计和接口输出必须高度结构化（如 JSON 格式、标准 API），方便其他 AI Agent 直接调用或集成。

## 3. 核心驱动：能力抽象化 (Skills & Tools)
Scout 不再预设死板的数据源需求，而是将其抽象为可动态编排的能力集。

- **Tools (底层工具/原子能力)**：
  - 代表“**如何执行 (How)**”。
  - 例如：`SearchTool` (搜索)、`CrawlTool` (爬取)、`StorageTool` (负责状态去重与 Session/Report 的物理落盘记录)。
  - 具备极强的通用性和原子性。
- **Skills (高层技能/操作 SOP)**：
  - 代表“**业务流程 (SOP/What)**”。
  - 编排一个或多个 Tools 来完成复杂的任务。
  - 例如：`ResearchSOP` (研究技能)、`StockAlertSOP` (股票预警技能)。
  - 内置领域知识，如去重策略、特定网站的解析逻辑、用户的偏好权重。

## 4. 架构设计与核心基石 (Architecture & Pillars)
本项目的核心架构全面转向 **以 Task 为中心 (Task-centric)** 的 **Agentic 模式**。

### 4.1 Task (任务层)
- **定义**：包含任务名称、执行要求（Markdown Instruction）及调度配置（Cron）。
- **配置**：支持通过 `Chat-to-Config` 自然语言对话生成。
- **调度**：支持 Web 手动触发与 Cron 自动触发双模式。

### 4.2 Agentic Execution (执行层)
- **Agent 逻辑**：从死板的 Workflow 转向 **Agentic 驱动**。模型接收 Task 指令，自主决策并编排 Skills。
- **Skills & Tools (技能与工具)**：
  - 将原有的 Collector 重构为独立的 Skill。
  - **有状态性 (Stateful)**：如 Arxiv 采集、网页提取需内置去重逻辑。
  - **质量保障**：所有 Skill 和 Tool 必须配备单元测试 (`tests/skills/`)。
- **Context & Memory (记忆系统)**：
  - **Session**：任务的每一次执行被称为一个 Session。
  - **持久化**：Session 执行详情落地存储于 `data/sessions/`。
  - **闭环**：上一轮 Session 的产物可作为下一轮的 Context，指导 Agent 进行过滤和排序倾向的微调。

### 4.3 Channel (分发层)
- **定义**：负责将 Agent 的执行结果交付。
- **当前实现**：调用 `StorageTool` 落地为 `data/reports/` 目录下的结构化文件。
- **消费与展示**：Web UI 负责读取 Channel 产出的数据并进行前端可视化渲染。

## 5. 项目结构规范 (Project Structure)
严格遵循以下目录结构：
- `src/core/skills`: 存放独立的原子化技能（Arxiv, WebSearch 等）。
- `data/sessions`: 存放任务执行的中间过程与 Session 上下文存档。
- `data/reports`: 存放最终对用户可见的精简结果。
- `tests/skills`: 存放技能层级的单元测试。
- `config`: 存放全局配置、任务调度 (`schedules.json`) 以及 **Skills & Tools 的定义和元数据** (`skills.yaml`, `tools.yaml`)。
- `docs`: 存储 [详细技术设计](file:///Users/liyong.1024/Workspace/scout/docs/technical_design.md) 和 [重建指南](file:///Users/liyong.1024/Workspace/scout/docs/reconstruction_guide.md)。

## 6. 验收与评估标准 (Evaluation & Assessment)
Scout 的初步成功将由以下具体能力作为评估标准（Baseline）：

### 6.1 工具层验收 (Tool-level Verification)
- **CrawlTool**：给定任意标准网页 URL，能够准确抓取并解析出网页主体文本内容。
- **SearchTool**：给定 Query 关键词，能够通过搜索引擎返回包含标题、链接及摘要的网页列表。
- **RSSTool**：给定 Arxiv 等标准源及关键词，能够采集到最新的内容列表。

### 6.2 技能层验收 (Skill-level Verification)
- **X (Twitter) Collection Skill**：给定博主（Blogger/User ID），Skill 能够自动化编排爬取过程，完整采集该博主近期的推文内容。

### 6.3 整体 Agentic 评估 (End-to-End Agentic Assessment)
- **端到端闭环**：要求 Agent 执行“追踪 X 与 Arxiv 上关于 'Agent' 领域最新进展”的任务。
- **预期结果**：
  1. 系统成功从两个异构平台采集到内容。
  2. 采集到的资讯必须具备**强相关性**（非杂讯）。
  3. 能够识别并去重，最终输出一份结构清晰、相关性极高的综述报告。

---
*本文档为 Scout 的核心知识库，可作为 AI 智能体重新理解并构建本项目的元数据依据。*