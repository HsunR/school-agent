# School Agent - Chat MVP

## TL;DR

> **Quick Summary**: 构建一个规范的 School Agent 智能对话系统（v1），采用 pnpm workspace monorepo 架构，Next.js + Tailwind 前端通过 SSE 流式调用 FastAPI + LangChain + LangGraph 后端，严格 TDD 开发。
> 
> **Deliverables**:
> - 完整 monorepo 项目结构（前后端分离）
> - FastAPI 后端：SSE 流式聊天 API + LangGraph 简单 Graph
> - Next.js 前端：聊天界面 + Markdown 渲染
> - 100% TDD 覆盖（RED → GREEN → REFACTOR）
> 
> **Estimated Effort**: Medium (~12-15 tasks)
> **Parallel Execution**: YES - 6 waves
> **Critical Path**: Root scaffolding → Backend core → API endpoint → Frontend integration → Final verification

---

## Context

### Original Request
开发一个 school agent 智能 Agent，前端使用 Next.js + TypeScript + Tailwind，后端使用 FastAPI + LangChain + LangGraph，使用 pnpm monorepo 管理。第一期只实现单纯的 API 对话功能，AI 回答使用 Markdown 渲染。严格 TDD 开发，项目结构规范。

### Interview Summary
**Key Discussions**:
- **后端结构**: 按模块分层 (api/ core/ services/ schemas/)
- **LLM**: 兼容 OpenAI API 格式（默认 DeepSeek: deepseek-chat）
- **API 设计**: SSE 流式响应 (POST 请求)
- **测试**: 严格 TDD (Vitest + pytest)
- **Monorepo**: pnpm workspace（frontend/ + backend/）
- **多轮对话**: 前端发送完整 messages 数组
- **输入限制**: 1000 字符截断
- **中断处理**: 排队（等待当前流完成）
- **SSE 方式**: fetch + ReadableStream
- **Windows 兼容**: asyncio.ProactorEventLoopPolicy

**Research Findings**:
- 环境已确认: Node.js v24.10.0, pnpm 10.23.0, Python 3.12.7
- 全局已安装 fastapi 0.110.0, uvicorn 0.29.0, httpx 0.28.1
- 全局已安装 langchain 1.2.17, langgraph 1.1.10, openai 2.37.0

### Metis Review
**Identified Gaps** (addressed):
- **SSE 在 Windows 上的兼容性**: 使用 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())` 解决
- **Python 包管理策略**: 使用 pyproject.toml + requirements.txt，独立于 pnpm
- **PNPM workspace 问题**: 只包含 frontend/，backend/ 作为独立 Python 项目
- **多轮对话未定义**: 确认前端传递完整 messages 数组
- **中断行为未定义**: 确认排队处理
- **Markdown 渲染膨胀**: 锁定 react-markdown + remark-gfm 仅此而已
- **错误处理不足**: 添加超时处理、错误状态显示、空消息验证

---

## Work Objectives

### Core Objective
构建一个基于 SSE 流式传输的智能对话系统，实现"用户输入 → AI 流式回复（Markdown 渲染）"的单轮/多轮对话闭环。

### Concrete Deliverables
- 根目录: pnpm-workspace.yaml, .gitignore, README.md
- `backend/`: FastAPI 应用（app/api/, app/core/, app/services/, app/schemas/, app/graph/）
- `backend/tests/`: pytest 测试套件
- `frontend/`: Next.js App Router 应用（components/, hooks/, app/）
- `frontend/__tests__/`: Vitest 测试套件

### Definition of Done
- [ ] `curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}"` 返回 SSE 流式内容
- [ ] 前端输入消息 → 实时看到 AI 流式回复 → Markdown 正确渲染
- [ ] `pytest backend/tests/ -v` 全部通过
- [ ] `cd frontend && npx vitest run` 全部通过

### Must Have
- SSE 流式响应（非一次性 JSON 返回）
- Markdown 渲染（粗体、列表、代码块、链接）
- 多轮对话（历史消息传递）
- 1000 字符输入限制
- 排队机制（流传输中禁止发送新消息）
- TDD 测试覆盖（services + components）
- 空消息/错误状态处理

### Must NOT Have (Guardrails)
- 禁止数据库/SQLite/文件持久化
- 禁止用户认证/登录/会话
- 禁止 Docker 容器化
- 禁止语法高亮 (rehype-highlight)、数学公式 (remark-math) 等 Markdown 增强
- 禁止打字机动画/打字指示器
- 禁止 RAG/向量存储/知识库
- 禁止快照测试/视觉回归测试/E2E 测试
- 禁止 v1 范围内的中断/取消功能
- 禁止使用 EventSource（必须用 fetch + ReadableStream）

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.
> No exceptions. No manual testing required.

### Test Decision
- **Infrastructure**: New project - needs setup
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Frontend framework**: Vitest + @testing-library/react + @testing-library/jest-dom
- **Backend framework**: pytest + pytest-asyncio + httpx.AsyncClient

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario}.{ext}`.

- **Backend**: Bash(curl) + pytest for SSE endpoint testing
- **Frontend**: Playwright for browser interaction + vitest for unit tests
- **API**: curl for manual verification + pytest for automated

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - 4 parallel tasks):
├── Task 1: Root monorepo scaffolding [quick]
├── Task 2: Backend project scaffolding [quick]
├── Task 3: Frontend project scaffolding (create-next-app) [quick]
└── Task 4: API contract & message type definition [quick]

Wave 2 (Backend core - 3 parallel tasks after Wave 1):
├── Task 5: Backend config + Pydantic schemas [quick] (depends: 2, 4)
├── Task 6: Backend LLM service + LangGraph graph [deep] (depends: 5)
└── Task 7: Backend SSE streaming API endpoint [unspecified-high] (depends: 6)

Wave 3 (Frontend core - 3 parallel tasks after Wave 1):
├── Task 8: Frontend chat API hook + SSE client [unspecified-high] (depends: 3, 4)
├── Task 9: Frontend ChatInput + ChatMessage components [visual-engineering] (depends: 3)
└── Task 10: Frontend MarkdownRenderer component [visual-engineering] (depends: 3)

Wave 4 (Integration - 2 parallel tasks):
├── Task 11: Frontend main page integration [visual-engineering] (depends: 8, 9, 10)
└── Task 12: Backend tests + coverage [unspecified-high] (depends: 5, 6, 7)

Wave 5 (Frontend test & polish - 2 parallel tasks):
├── Task 13: Frontend vitest test suite [unspecified-high] (depends: 8, 9, 10, 11)
└── Task 14: Next.js proxy config + integration wiring [quick] (depends: 7, 11)

Wave FINAL (4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high + playwright)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1    | -         | -      |
| 2    | -         | 5, 6, 7 |
| 3    | -         | 8, 9, 10, 11, 13 |
| 4    | -         | 5, 8   |
| 5    | 2, 4      | 6      |
| 6    | 5         | 7, 12  |
| 7    | 6         | 12, 14 |
| 8    | 3, 4      | 11, 13 |
| 9    | 3         | 11, 13 |
| 10   | 3         | 11, 13 |
| 11   | 8, 9, 10  | 13, 14 |
| 12   | 5, 6, 7   | -      |
| 13   | 8, 9, 10, 11 | -   |
| 14   | 7, 11     | -      |
| F1-F4| All above | -      |

### Agent Dispatch Summary

- **Wave 1**: 4 × `quick`
- **Wave 2**: 1 × `quick`, 1 × `deep`, 1 × `unspecified-high`
- **Wave 3**: 1 × `unspecified-high`, 2 × `visual-engineering`
- **Wave 4**: 1 × `visual-engineering`, 1 × `unspecified-high`
- **Wave 5**: 1 × `unspecified-high`, 1 × `quick`
- **FINAL**: 4 × review agents

---

## TODOs

- [x] 1. Root Monorepo 基础结构搭建

  **What to do**:
  - 在根目录创建 `pnpm-workspace.yaml`，只包含 `packages: ['frontend/*']`（backend 是独立 Python 项目）
  - 创建根 `package.json`，配置 workspace 脚本和基础信息
  - 创建 `.gitignore`（Node、Python、IDE 通用规则）
  - 创建 `.env.example` 模板文件（DEEPSEEK_API_KEY、LLM_MODEL、LLM_BASE_URL）
  - 创建 `README.md` 项目说明（项目结构、启动方式、技术栈）

  **Must NOT do**:
  - 不要在 pnpm-workspace.yaml 中包含 backend/
  - 不要提交真实 API Key

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - pnpm workspace docs: `https://pnpm.io/pnpm-workspace_yaml`

  **QA Scenarios**:
  ```
  Scenario: Verify project structure exists
    Tool: Bash
    Steps:
      1. Check pnpm-workspace.yaml exists: Test-Path "pnpm-workspace.yaml"
      2. Check .gitignore exists: Test-Path ".gitignore"
      3. Check .env.example exists: Test-Path ".env.example"
      4. Check package.json exists: Test-Path "package.json"
    Expected Result: All files exist with correct content
    Evidence: .sisyphus/evidence/task-1-structure.txt

  Scenario: Verify pnpm-workspace only includes frontend
    Tool: Bash
    Steps:
      1. Read pnpm-workspace.yaml
      2. Verify backend/ is NOT listed as a package
    Expected Result: Only 'frontend/*' in packages array
    Evidence: .sisyphus/evidence/task-1-workspace.txt
  ```

  **Commit**: YES (groups with 2, 3, 4)
  - Message: `chore(project): initialize monorepo structure with backend and frontend scaffolding`
  - Files: `pnpm-workspace.yaml`, `package.json`, `.gitignore`, `.env.example`, `README.md`

---

- [x] 2. 后端项目骨架搭建

  **What to do**:
  - 创建 `backend/` 目录结构：
    ```
    backend/
    ├── app/
    │   ├── __init__.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── chat.py          # SSE 聊天端点（stub）
    │   ├── core/
    │   │   ├── __init__.py
    │   │   └── settings.py      # 配置管理（stub）
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   └── chat.py          # Pydantic 模型（stub）
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── chat_service.py  # LLM 服务（stub）
    │   └── graph/
    │       ├── __init__.py
    │       └── graph.py         # LangGraph 图定义（stub）
    ├── tests/
    │   ├── __init__.py
    │   ├── test_chat_api.py     # API 测试（stub）
    │   └── test_chat_service.py # 服务测试（stub）
    ├── pyproject.toml           # Python 项目元数据
    └── requirements.txt         # 依赖列表
    ```
  - 创建 `pyproject.toml` 基本配置
  - 创建 `requirements.txt`：fastapi, uvicorn, langchain-core, langchain-openai, langgraph, httpx, pydantic, python-dotenv
  - 所有模块文件写基本 import + docstring stub
  - `app/main.py`: FastAPI app 入口（含 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`）

  **Must NOT do**:
  - 不要写任何业务逻辑（stub 只包含 import 和 docstring）
  - 不要添加数据库依赖

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - FastAPI project structure: `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
  - pyproject.toml spec: `https://packaging.python.org/en/latest/tutorials/packaging-projects/`

  **QA Scenarios**:
  ```
  Scenario: Backend structure is correct
    Tool: Bash
    Steps:
      1. Check all directories exist: Test-Path "backend/app/api", Test-Path "backend/app/core", etc.
      2. Check all __init__.py exist
      3. Check main.py exists
      4. Check pyproject.toml and requirements.txt exist
    Expected Result: Complete directory structure with stub files
    Evidence: .sisyphus/evidence/task-2-structure.txt

  Scenario: FastAPI app can be imported
    Tool: Bash
    Steps:
      1. cd backend
      2. python -c "from app.main import app; print('OK:', type(app).__name__)"
    Expected Result: "OK: FastAPI" printed without errors
    Evidence: .sisyphus/evidence/task-2-import.txt
  ```

  **Commit**: YES (groups with 1, 3, 4)

---

- [x] 3. 前端项目骨架搭建（create-next-app）

  **What to do**:
  - 在 `frontend/` 目录下使用 `npx create-next-app@latest` 初始化：
    - TypeScript: Yes
    - ESLint: Yes
    - Tailwind CSS: Yes
    - `src/` directory: Yes (使用 src/)
    - App Router: Yes
    - Import alias: `@/*`
  - 安装前端开发依赖：
    - `pnpm add react-markdown remark-gfm`（Markdown 渲染）
    - `pnpm add -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom`（测试）
  - 配置 `vitest.config.ts`
  - 在 `frontend/package.json` 中添加 test script: `"test": "vitest run", "test:watch": "vitest"`
  - 清理 create-next-app 的默认页面内容，保留干净骨架
  - 启动验证：`pnpm dev` 可正常启动

  **Must NOT do**:
  - 不要添加 UI 库（如 shadcn/ui, radix）
  - 不要添加状态管理库（如 zustand, redux）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Tasks 8, 9, 10, 11, 13
  - **Blocked By**: None

  **References**:
  - create-next-app: `https://nextjs.org/docs/getting-started/installation`
  - Vitest with Next.js: `https://nextjs.org/docs/app/building-your-application/testing/vitest`
  - react-markdown: `https://github.com/remarkjs/react-markdown`

  **QA Scenarios**:
  ```
  Scenario: Next.js app starts
    Tool: Bash
    Steps:
      1. cd frontend
      2. pnpm dev &
      3. curl http://localhost:3000 (expect HTML response)
      4. kill %1
    Expected Result: Server starts, returns HTML
    Evidence: .sisyphus/evidence/task-3-startup.txt

  Scenario: Vitest is configured
    Tool: Bash
    Steps:
      1. cd frontend
      2. npx vitest run --help (verify command exists)
      3. Check vitest.config.ts exists
    Expected Result: vitest is configured
    Evidence: .sisyphus/evidence/task-3-vitest.txt
  ```

  **Commit**: YES (groups with 1, 2, 4)

---

- [x] 4. API 契约与消息类型定义

  **What to do**:
  - 在根目录创建 `docs/api.md` 记录 API 契约：
    - 端点: `POST /api/chat`
    - 请求体格式 (JSON):
      ```json
      {
        "messages": [
          {"role": "user" | "assistant" | "system", "content": "string"}
        ],
        "stream": true
      }
      ```
    - 响应格式: SSE (Server-Sent Events)
      - 每行格式: `data: {"token": "Hello", "done": false}\n\n`
      - 结束标志: `data: {"token": "", "done": true}\n\n`
      - 错误格式: `data: {"error": "message", "done": true}\n\n`
    - 错误状态码: 400 (验证错误), 422 (模型错误), 500 (服务器错误)
  - 输入限制：max 1000 字符

  **Must NOT do**:
  - 不要写入任何代码文件（只写文档）
  - 不要在 docs/api.md 中包含具体实现细节

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Tasks 5, 8
  - **Blocked By**: None

  **QA Scenarios**:
  ```
  Scenario: API document exists
    Tool: Bash
    Steps:
      1. Test-Path "docs/api.md"
      2. Read file content - verify it defines endpoint, request, response format
    Expected Result: Complete API contract document
    Evidence: .sisyphus/evidence/task-4-docs.txt
  ```

  **Commit**: YES (groups with 1, 2, 3)

---

- [x] 5. 后端配置 + Pydantic 数据模型（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `tests/test_settings.py`：验证 settings 加载正确的环境变量
    - `tests/test_schemas.py`：验证 ChatRequest、ChatMessage 模型验证
  - **GREEN**:
    - `app/core/settings.py`:
      - `class Settings(BaseSettings)`:
        - `deepseek_api_key: str` (env: DEEPSEEK_API_KEY)
        - `llm_model: str = "deepseek-chat"` (env: LLM_MODEL)
        - `llm_base_url: str = "https://api.deepseek.com/v1"` (env: LLM_BASE_URL)
        - `max_input_length: int = 1000` (env: MAX_INPUT_LENGTH)
        - `llm_timeout: int = 30` (env: LLM_TIMEOUT)
        - `app_name: str = "school-agent"`
      - 使用 `lazy load` 模式（`@lru_cache`）
    - `app/schemas/chat.py`:
      - `class ChatMessage(BaseModel)`:
        - `role: Literal["user", "assistant", "system"]`
        - `content: str` (validated: max_length=max_input_length)
      - `class ChatRequest(BaseModel)`:
        - `messages: list[ChatMessage]` (validated: min_length=1)
        - `stream: bool = True`
      - `class ChatResponse(BaseModel)`:
        - `token: str`
        - `done: bool = False`
        - `error: Optional[str] = None`
  - **REFACTOR**: 清理验证逻辑

  **Must NOT do**:
  - 不要添加与 AI 模型交互的逻辑
  - 不要添加 API 路由

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential within Wave 2)
  - **Parallel Group**: Wave 2 (Task 5 → Task 6 → Task 7)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 2, 4

  **References**:
  - Pydantic v2 Settings: `https://docs.pydantic.dev/latest/concepts/pydantic_settings/`
  - Pydantic field validation: `https://docs.pydantic.dev/latest/concepts/validators/`

  **QA Scenarios**:
  ```
  Scenario: Settings loads from env
    Tool: Bash
    Steps:
      1. cd backend
      2. $env:DEEPSEEK_API_KEY="test-key-123"; python -c "from app.core.settings import get_settings; s = get_settings(); print(s.deepseek_api_key)"
    Expected Result: Prints "test-key-123"
    Evidence: .sisyphus/evidence/task-5-settings.txt

  Scenario: Schema validation rejects oversize input
    Tool: Bash
    Steps:
      1. cd backend
      2. python -c "from app.schemas.chat import ChatRequest, ChatMessage; import traceback; msgs=[ChatMessage(role='user',content='x'*1001)]; r=ChatRequest(messages=msgs); print('FAIL: should have raised ValueError')"
      3. python -c "from app.schemas.chat import ChatRequest, ChatMessage; msgs=[ChatMessage(role='user',content='x'*500)]; r=ChatRequest(messages=msgs); print('OK:', len(r.messages[0].content))"
    Expected Result: First command raises validation error, second prints "OK: 500"
    Evidence: .sisyphus/evidence/task-5-schema.txt

  Scenario: Tests pass
    Tool: Bash
    Steps:
      1. cd backend
      2. pytest tests/test_settings.py tests/test_schemas.py -v
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-5-pytest.txt
  ```

  **Commit**: NO (groups with 6, 7)

---

- [x] 6. 后端 LLM 服务 + LangGraph Graph（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `tests/test_chat_service.py`：mock LangChain ChatOpenAI，测试服务的流式调用
    - `tests/test_graph.py`：mock service，测试 Graph 编译和调用
  - **GREEN**:
    - `app/graph/graph.py`:
      - 定义一个简单的 LangGraph `StateGraph`，状态类型为 `list[ChatMessage]`
      - 只有一个节点 `call_model`，调用 ChatOpenAI 生成回复
      - 边: `START -> call_model -> END`
      - 导出 `compile_graph()` 函数返回编译后的 graph
    - `app/services/chat_service.py`:
      - `class ChatService`:
        - `__init__(self, settings: Settings)`: 初始化 ChatOpenAI（streaming=True）
        - `async def stream_chat(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]`:
          - 使用 LangGraph graph 调用 LLM
          - 通过 `astream_events` 或 `astream` 逐 token 产出
    - 使用 `langchain_openai.ChatOpenAI`（兼容 DeepSeek / 任何 OpenAI 兼容 API）
    - 配置 base_url = settings.llm_base_url
    - 配置 api_key = settings.deepseek_api_key
    - 配置 model = settings.llm_model
    - 配置 timeout = settings.llm_timeout
    - 配置 streaming = True
  - **REFACTOR**: 分离关注点，确保可测试性

  **Must NOT do**:
  - 不要添加 API 路由（Task 7 做）
  - 不要添加复杂条件边或多节点 graph
  - 不要添加 RAG/向量存储

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Reason**: LangGraph + LangChain 集成需要深度理解异步流式处理

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential: 5 → 6 → 7)
  - **Blocks**: Tasks 7, 12
  - **Blocked By**: Task 5

  **References**:
  - LangGraph quickstart: `https://langchain-ai.github.io/langgraph/tutorials/introduction/`
  - LangChain ChatOpenAI streaming: `https://python.langchain.com/docs/how_to/streaming/`
  - LangChain OpenAI integration: `https://python.langchain.com/docs/integrations/chat/openai/`

  **QA Scenarios**:
  ```
  Scenario: Service can stream tokens (with mocked LLM)
    Tool: Bash
    Steps:
      1. cd backend
      2. python -c "
import asyncio
from app.core.settings import get_settings
from app.services.chat_service import ChatService
from app.schemas.chat import ChatMessage

async def test():
    s = get_settings()
    svc = ChatService(s)
    msgs = [ChatMessage(role='user', content='Say hello')]
    tokens = []
    async for token in svc.stream_chat(msgs):
        tokens.append(token)
    print(f'Got {len(tokens)} tokens')
    # NOTE: This actually calls the API - requires valid DEEPSEEK_API_KEY
asyncio.run(test())
"
    Expected Result: Prints token count (requires valid API key)
    Evidence: .sisyphus/evidence/task-6-stream.txt

  Scenario: Graph compiles without errors
    Tool: Bash
    Steps:
      1. cd backend
      2. python -c "
from app.graph.graph import compile_graph
graph = compile_graph()
print('Graph compiled:', type(graph).__name__)
"
    Expected Result: "Graph compiled: CompiledStateGraph" (no errors)
    Evidence: .sisyphus/evidence/task-6-graph.txt

  Scenario: Tests pass
    Tool: Bash
    Steps:
      1. cd backend
      2. pytest tests/test_chat_service.py tests/test_graph.py -v
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-6-pytest.txt
  ```

  **Commit**: NO (groups with 5, 7)

---

- [x] 7. 后端 SSE 流式 API 端点（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `tests/test_chat_api.py`：
      - 使用 `httpx.AsyncClient` 测试 SSE 端点
      - mock ChatService 返回模拟 tokens
      - 验证响应是 text/event-stream 格式
      - 验证格式: `data: {"token": "...", "done": false}\n\n`
      - 验证最后收到: `data: {"token": "", "done": true}\n\n`
      - 测试空消息返回 422
      - 测试超长消息返回 400
  - **GREEN**:
    - `app/api/chat.py`:
      - `POST /api/chat`
      - 接收 `ChatRequest` JSON body
      - 验证 `messages` 不为空
      - 验证每条 message 的 content 不超过 max_input_length
      - 使用 `StreamingResponse`（media_type="text/event-stream"）
      - 异步生成 SSE 格式数据：
        ```python
        async def event_generator():
            async for token in chat_service.stream_chat(messages):
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        ```
      - 错误处理：try/except 块捕获并返回 SSE 格式错误
      - 导入并挂载到 main app
  - **REFACTOR**: 优化错误处理和流管理

  **Must NOT do**:
  - 不要添加非 SSE 的响应方式
  - 不要添加数据库操作

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential: 5 → 6 → 7)
  - **Blocks**: Tasks 12, 14
  - **Blocked By**: Task 6

  **References**:
  - FastAPI StreamingResponse: `https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse`
  - SSE spec: `https://html.spec.whatwg.org/multipage/server-sent-events.html`

  **QA Scenarios**:
  ```
  Scenario: SSE endpoint returns valid event stream
    Tool: Bash
    Steps:
      1. cd backend
      2. Start server: Start-Process -NoNewWindow powershell -ArgumentList "uvicorn app.main:app --host 0.0.0.0 --port 8000"
      3. Start-Sleep -Seconds 3
      4. curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"count 1 to 3"}]}' -NoEscape
      5. Stop process
    Expected Result: Receives SSE data events ending with {"token":"","done":true}
    Evidence: .sisyphus/evidence/task-7-sse.txt

  Scenario: Empty message returns 422
    Tool: Bash
    Steps:
      1. Start server (same as above)
      2. curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":""}]}'
    Expected Result: Response status 422 with validation error
    Evidence: .sisyphus/evidence/task-7-validation.txt

  Scenario: Tests pass
    Tool: Bash
    Steps:
      1. cd backend
      2. pytest tests/test_chat_api.py -v
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-7-pytest.txt
  ```

  **Commit**: YES (groups with 5, 6)
  - Message: `feat(backend): implement SSE chat API with LangChain + LangGraph`
  - Files: `backend/app/`, `backend/tests/`

---

- [ ] 8. 前端 Chat API Hook + SSE 客户端（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `frontend/src/__tests__/hooks/useChat.test.ts`:
      - mock fetch 返回 ReadableStream
      - 测试 sendMessage 正确调用 POST /api/chat
      - 测试流式 token 正确累积到 message 中
      - 测试 done=true 后标记消息完成
      - 测试空消息不发送
      - 测试超长消息被截断或阻止
      - 测试 API 错误显示在错误状态中
  - **GREEN**:
    - `frontend/src/types/chat.ts`:
      ```typescript
      export interface ChatMessage {
        id: string;
        role: 'user' | 'assistant' | 'system';
        content: string;
        timestamp: number;
        isStreaming?: boolean;
      }
      
      export interface SSEPayload {
        token: string;
        done: boolean;
        error?: string;
      }
      ```
    - `frontend/src/hooks/useChat.ts`:
      - `function useChat()`
      - 状态: `messages: ChatMessage[]`, `isLoading: boolean`, `error: string | null`
      - `sendMessage(content: string)`:
        - 验证输入不为空且长度 ≤ 1000
        - 添加 user message 到列表
        - 创建空的 assistant message（isStreaming=true）
        - POST `/api/chat` 发送完整 messages 数组
        - 使用 `response.body.getReader()` 读取 SSE 流
        - 解析 `data: {...}\n\n` 格式，逐 token 追加到 assistant message
        - 收到 `done: true` 后标记 isStreaming=false
        - 错误处理：catch 异常并设置 error
        - 排队机制：isLoading 时禁用发送
      - `clearMessages()`: 清空消息列表
      - `clearError()`: 清除错误
  - **REFACTOR**: 提取 SSE 解析逻辑到独立 utility

  **Must NOT do**:
  - 不要使用 EventSource API（必须用 fetch + ReadableStream）
  - 不要添加 Zustand/Redux 等状态管理
  - 不要添加持久化存储

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10)
  - **Blocks**: Tasks 11, 13
  - **Blocked By**: Tasks 3, 4

  **References**:
  - Fetch API ReadableStream: `https://developer.mozilla.org/en-US/docs/Web/API/ReadableStream`
  - Next.js App Router fetching: `https://nextjs.org/docs/app/building-your-application/data-fetching/patterns`

  **QA Scenarios**:
  ```
  Scenario: Hook sends messages to correct endpoint
    Tool: Bash (vitest)
    Steps:
      1. cd frontend
      2. npx vitest run src/__tests__/hooks/useChat.test.ts
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-8-hook.txt

  Scenario: Hook validates empty messages
    Tool: Bash (node REPL - check types)
    Steps:
      1. cd frontend
      2. npx tsx -e "
import { ChatMessage } from '@/types/chat';
const msg: ChatMessage = { id: '1', role: 'user', content: 'hello', timestamp: Date.now() };
console.log('Type check passed:', msg.content);
"
    Expected Result: Types compile correctly
    Evidence: .sisyphus/evidence/task-8-types.txt
  ```

  **Commit**: NO (groups with 9, 10, 11)

---

- [ ] 9. 前端 ChatInput + ChatMessage 组件（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `frontend/src/__tests__/components/ChatInput.test.tsx`:
      - 测试输入框渲染
      - 测试输入文本后发送按钮启用
      - 测试空输入时发送按钮禁用
      - 测试超过 1000 字符显示警告
      - 测试 loading 状态时输入框/按钮禁用
      - 测试 onSend 回调正确触发
    - `frontend/src/__tests__/components/ChatMessage.test.tsx`:
      - 测试 user message 渲染（右对齐）
      - 测试 assistant message 渲染（左对齐）
      - 测试 `isStreaming` 时显示加载指示器
  - **GREEN**:
    - `frontend/src/components/ChatInput.tsx`:
      - Props: `onSend(content: string): void`, `isLoading: boolean`
      - textarea 输入框（自动调整高度）
      - 发送按钮（isLoading 时禁用）
      - 字符计数器（xxx/1000）
      - 空/仅空白消息阻止发送
      - Enter 发送（Shift+Enter 换行）
    - `frontend/src/components/ChatMessage.tsx`:
      - Props: `message: ChatMessage`
      - user 消息右对齐，assistant 消息左对齐
      - AI 消息使用 `<MarkdownRenderer>` 渲染
      - 显示消息时间戳
      - isStreaming 时显示光标动画
  - **REFACTOR**: 提取公共样式，确保可访问性

  **Must NOT do**:
  - 不要添加打字机动画
  - 不要添加打字指示器（TypingIndicator）
  - 不要使用第三方 UI 库

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 10)
  - **Blocks**: Tasks 11, 13
  - **Blocked By**: Task 3

  **References**:
  - Tailwind CSS docs: `https://tailwindcss.com/docs/`
  - Next.js components: `https://nextjs.org/docs/app/building-your-application/rendering/client-components`

  **QA Scenarios**:
  ```
  Scenario: Components render correctly
    Tool: Bash (vitest)
    Steps:
      1. cd frontend
      2. npx vitest run src/__tests__/components/ChatInput.test.tsx src/__tests__/components/ChatMessage.test.tsx
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-9-components.txt
  ```

  **Commit**: NO (groups with 8, 10, 11)

---

- [ ] 10. 前端 MarkdownRenderer 组件（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `frontend/src/__tests__/components/MarkdownRenderer.test.tsx`:
      - 测试普通文本渲染为 `<p>`
      - 测试 `**bold**` 渲染为 `<strong>bold</strong>`
      - 测试 `*italic*` 渲染为 `<em>italic</em>`
      - 测试 `` `code` `` 渲染为 `<code>code</code>`
      - 测试 ``` ```code block``` ``` 渲染为 `<pre><code>`
      - 测试 `- list item` 渲染为 `<ul><li>`
      - 测试 `[link](url)` 渲染为 `<a href="url">link</a>`
      - 测试 XSS 防护（`<script>` 被转义而非执行）
  - **GREEN**:
    - `frontend/src/components/MarkdownRenderer.tsx`:
      - Props: `content: string`
      - 使用 `react-markdown` 渲染
      - 配置 `remarkPlugins={[remarkGfm]}` 启用 GFM（表格、任务列表等）
      - 自定义组件映射（可选定制样式）
      - Tailwind 样式美化（代码块背景、标题样式等）
  - **REFACTOR**: 提取代码块样式到全局 CSS

  **Must NOT do**:
  - 不要添加 rehype-highlight（语法高亮）
  - 不要添加 remark-math（数学公式）
  - 不要添加自定义 rehype/remark 插件

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9)
  - **Blocks**: Tasks 11, 13
  - **Blocked By**: Task 3

  **References**:
  - react-markdown: `https://github.com/remarkjs/react-markdown`
  - remark-gfm: `https://github.com/remarkjs/remark-gfm`
  - Custom components: `https://github.com/remarkjs/react-markdown?tab=readme-ov-file#appendix-b-components`

  **QA Scenarios**:
  ```
  Scenario: Markdown renders correctly
    Tool: Bash (vitest)
    Steps:
      1. cd frontend
      2. npx vitest run src/__tests__/components/MarkdownRenderer.test.tsx
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-10-markdown.txt
  ```

  **Commit**: NO (groups with 8, 9, 11)

---

- [ ] 11. 前端主页面集成（TDD）

  **What to do**:
  - **RED**: 先写测试：
    - `frontend/src/__tests__/app/page.test.tsx`:
      - 测试页面渲染 ChatInput + 消息列表 + 空状态
      - 测试发送消息后 user message 出现在列表中
      - 测试错误状态显示错误信息
      - 测试 loading 状态
      - 测试清空消息功能
  - **GREEN**:
    - `frontend/src/app/page.tsx`:
      - 导入 `useChat` hook
      - 消息列表渲染（`<ChatMessage>` 组件循环）
      - 空状态提示（"开始对话吧！"）
      - `<ChatInput>` 绑定 `sendMessage`
      - 错误提示区域（可关闭）
      - 清空按钮
      - loading 时底部消息显示跳过动画
    - `frontend/src/app/globals.css`:
      - Tailwind 基础样式
      - 自定义滚动条样式
      - Markdown 内容样式
      - 加载动画（闪烁光标）
    - `frontend/src/app/layout.tsx`:
      - HTML meta 标签
      - 字体设置
      - 基本布局
  - **REFACTOR**: 优化样式和布局

  **Must NOT do**:
  - 不要添加导航栏/侧边栏
  - 不要添加多页面路由
  - 不要添加主题切换

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (sequential with 13)
  - **Blocks**: Tasks 13, 14
  - **Blocked By**: Tasks 8, 9, 10

  **References**:
  - Next.js App Router: `https://nextjs.org/docs/app`
  - Tailwind CSS: `https://tailwindcss.com/docs/`

  **QA Scenarios**:
  ```
  Scenario: Frontend page renders with chat components
    Tool: Bash (vitest)
    Steps:
      1. cd frontend
      2. npx vitest run src/__tests__/app/page.test.tsx
    Expected Result: All tests passed
    Evidence: .sisyphus/evidence/task-11-page.txt

  Scenario: Full UI renders in browser (Playwright)
    Tool: Bash + Playwright
    Steps:
      1. cd frontend
      2. npx playwright open http://localhost:3000 (or use Playwright skill)
      3. Verify chat input exists
      4. Verify send button exists
    Expected Result: Chat UI renders properly
    Evidence: .sisyphus/evidence/task-11-ui.txt
  ```

  **Commit**: YES (groups with 8, 9, 10)
  - Message: `feat(frontend): implement chat UI with SSE streaming and Markdown rendering`
  - Files: `frontend/src/`

---

- [ ] 12. 后端完整测试套件（pytest）

  **What to do**:
  - 完善 `tests/test_chat_api.py`：
    - 集成测试：使用 httpx.AsyncClient + TestClient
    - mock ChatService 测试 SSE 响应格式
    - 测试 400 错误（空消息、超长消息）
    - 测试 500 错误（service 抛出异常）
  - 完善 `tests/test_chat_service.py`：
    - mock ChatOpenAI 测试流式输出
    - 测试超时处理
  - 完善 `tests/test_graph.py`：
    - 测试 Graph 编译
    - 测试 Graph 调用
  - 添加 `tests/conftest.py`：
    - pytest fixtures（settings, mock_service, test_client）
  - 验证: `pytest tests/ -v` 全部通过

  **Must NOT do**:
  - 不要添加需要真实 API Key 的测试
  - 不要添加性能测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 11)
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 6, 7

  **References**:
  - FastAPI TestClient: `https://fastapi.tiangolo.com/tutorial/testing/`
  - pytest-asyncio: `https://pytest-asyncio.readthedocs.io/`

  **QA Scenarios**:
  ```
  Scenario: All backend tests pass
    Tool: Bash
    Steps:
      1. cd backend
      2. pytest tests/ -v --tb=short
    Expected Result: All tests pass, test names clearly describe what they test
    Evidence: .sisyphus/evidence/task-12-alltests.txt
  ```

  **Commit**: NO (groups with 13)

---

- [ ] 13. 前端完整测试套件（Vitest）

  **What to do**:
  - 完善 `frontend/src/__tests__/hooks/useChat.test.ts`：
    - mock fetch SSE 流
    - 测试完整消息发送-接收流程
    - 测试错误恢复
  - 完善 `frontend/src/__tests__/components/ChatInput.test.tsx`：
    - 测试所有交互场景
    - 测试键盘快捷键（Enter 发送，Shift+Enter 换行）
  - 完善 `frontend/src/__tests__/components/ChatMessage.test.tsx`：
    - 测试不同角色样式
    - 测试流式状态
  - 完善 `frontend/src/__tests__/components/MarkdownRenderer.test.tsx`：
    - 测试所有 Markdown 语法
    - 测试安全边界（XSS）
  - 完善 `frontend/src/__tests__/app/page.test.tsx`：
    - 测试完整页面渲染
    - 测试消息流
  - 验证: `npx vitest run` 全部通过

  **Must NOT do**:
  - 不要添加快照测试
  - 不要添加 E2E 测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 14)
  - **Blocks**: None
  - **Blocked By**: Tasks 8, 9, 10, 11

  **References**:
  - Vitest: `https://vitest.dev/guide/`
  - Testing Library: `https://testing-library.com/docs/react-testing-library/intro`

  **QA Scenarios**:
  ```
  Scenario: All frontend tests pass
    Tool: Bash
    Steps:
      1. cd frontend
      2. npx vitest run --reporter=verbose
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-13-alltests.txt
  ```

  **Commit**: YES (groups with 12)
  - Message: `test: add backend and frontend test suites`
  - Files: `backend/tests/`, `frontend/src/__tests__/`

---

- [ ] 14. Next.js 代理配置 + 集成联调

  **What to do**:
  - `frontend/next.config.ts`：
    ```typescript
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ];
    }
    ```
  - 确保前端开发时 `/api/chat` 被代理到后端
  - 验证端到端：启动前后端 → 发送消息 → 接收 SSE 流 → Markdown 渲染
  - 文档更新：README.md 添加启动步骤
  - 创建 `README.md` 或更新已有内容：
    ```markdown
    # School Agent
    
    ## Quick Start
    # Backend
    cd backend
    pip install -r requirements.txt
    cp .env.example .env  # 设置 DEEPSEEK_API_KEY
    uvicorn app.main:app --reload --port 8000
    
    # Frontend
    cd frontend
    pnpm install
    pnpm dev  # 访问 http://localhost:3000
    ```

  **Must NOT do**:
  - 不要修改后端端口
  - 不要添加 HTTPS 配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 13)
  - **Blocks**: None
  - **Blocked By**: Tasks 7, 11

  **References**:
  - Next.js rewrites: `https://nextjs.org/docs/app/api-reference/next-config-js/rewrites`

  **QA Scenarios**:
  ```
  Scenario: Proxy routes correctly
    Tool: Bash
    Steps:
      1. cd frontend
      2. Check next.config.ts contains rewrite rule for /api/:path*
      3. Start backend: cd backend; Start-Process powershell "uvicorn app.main:app --port 8000"
      4. Start frontend: Start-Process powershell "pnpm dev"
      5. Start-Sleep 5
      6. curl -X POST http://localhost:3000/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"hi"}]}'
    Expected Result: SSE stream received through Next.js proxy
    Evidence: .sisyphus/evidence/task-14-proxy.txt

  Scenario: README has correct startup instructions
    Tool: Bash
    Steps:
      1. Read README.md
      2. Verify it contains backend and frontend startup commands
    Expected Result: Complete, accurate startup guide
    Evidence: .sisyphus/evidence/task-14-readme.txt
  ```

  **Commit**: YES (groups alone)
  - Message: `chore: configure Next.js proxy and finalize integration`
  - Files: `frontend/next.config.ts`, `README.md`

---

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `cd backend && python -m pytest` + `cd frontend && npx vitest run`. Review all changed files for: type safety, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Backend Tests [PASS/FAIL] | Frontend Tests [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration. Test edge cases: empty message, error states, streaming cancellation.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1-4**: `chore(project): initialize monorepo structure with backend and frontend scaffolding`
- **5-7**: `feat(backend): implement SSE chat API with LangChain + LangGraph`
- **8-11**: `feat(frontend): implement chat UI with SSE streaming and Markdown rendering`
- **12-13**: `test: add backend and frontend test suites`
- **14**: `chore: configure Next.js proxy and finalize integration`

---

## Success Criteria

### Verification Commands
```bash
# Backend
cd backend && pytest tests/ -v
# Expected: All tests passed

# Frontend
cd frontend && npx vitest run
# Expected: All tests passed

# Integration
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello, say something in **bold**"}]}'
# Expected: SSE stream with Markdown content (bold text between ** **)

# Full stack
cd frontend && npx next dev
# Open http://localhost:3000, type message, see AI reply with Markdown rendering
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] SSE streaming works end-to-end
- [ ] Markdown renders correctly in frontend
