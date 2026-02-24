# Scout 项目重建指南 (AI Reconstruction Cookbook)

如果你是另一个 AI 助手，请按照此指南逐步还原本项目。

## 第一阶段：环境与框架搭建
1. **依赖管理**：使用 `uv` 初始化项目，包含 `fastapi`, `uvicorn`, `jinja2`, `apscheduler`, `requests`, `pyyaml`, `pydantic`。
2. **目录结构**：
   - `src/` (core, api, web/templates, web/static)
   - `data/` (tasks, daily)
   - `config/` (tasks)

## 第二阶段：核心组件实现 (顺序推荐)
1. **`src/core/base_collector.py`**: 定义 `ScrapedItem` 模型和 `BaseCollector` 基类。
2. **`src/core/state_manager.py`**: 实现基于 SQLite 的去重逻辑，确保 `task_id` 为 TEXT 类型以兼容文件名作为 ID。
3. **`src/core/task_manager.py`**: 实现从 `data/tasks/*.md` 读取 content 和解析 `cron` 的逻辑。
4. **`src/core/config_agent.py`**: 核心！编写能生成 `<plan><sources><source type="..."><query>...` 格式 XML 的 Prompt。
5. **`src/core/jobs.py`**: 编写 `run_collection_job(task_name)` 逻辑，它是有序调用 ConfigAgent、Collector、Summarizer、Exporter 的中控。

## 第三阶段：智能总结层
1. **`src/core/llm_summarizer.py`**:
   - `evaluate_and_summarize`: 负责给单条 Item 打分和总结。
   - `generate_task_markdown_from_chat`: 负责处理 Web UI 的 NLP 输入，输出带 `name` 和 `instruction` (Markdown) 的 JSON。

## 第四阶段：Web UI 与 Web API
1. **`src/api/routes.py`**: 对接核心组件。
   - `GET /api/items`: 分页查询。
   - `POST /api/tasks`: 保存 Markdown。
   - `POST /api/tasks/chat`: NLP 生成 Markdown。
2. **前端页面**:
   - `index.html`: 无限滚动展示资讯，支持 Like/Dislike 反馈。
   - `config.html`: Markdown 编辑器 + AI 沟通台。

## 第五阶段：服务挂载
1. **`src/main_web.py`**:
   - 初始化 `TaskManager` 和 `StateManager`。
   - 挂载 `APScheduler` 定时拉取任务。
   - 启动 Uvicorn。

---

## 避坑说明 (Important Tips)
- **ID 转换**：任务 ID 统一使用文件名（String），不要使用数据库递增自增 ID。
- **Prompt 隔离**：每个任务可以有自己的总结 Prompt，在 XML 的 `<summary_prompt>` 中体现。
- **文件路径**：所有涉及 `data` 或 `config` 的操作，务必基于 `base_dir` 的绝对路径动态拼接。
