# Agent 工作台实现计划

> **给 agentic workers：** 必须使用子技能 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。所有步骤都使用 checkbox（`- [ ]`）语法，方便追踪进度。

**目标：** 把现有结果页从“原始 JSON + SSE 调试面板”升级成一个可用的 PrismLens Agent 分析工作台，具备真实节点进度、稳定结构化报告和更完整的分析展示。

**架构：** 保留当前 FastAPI + ARQ + Python LangGraph 的后端执行架构。新增一个小型 progress event 模块，让 worker 统一发布 Redis/SSE 事件；前端继续作为轻量 Next.js 客户端，负责拉取任务状态、订阅进度、渲染 timeline 和结构化报告。

**技术栈：** Python 3.11、FastAPI、ARQ、Redis pub/sub、LangGraph、unittest、Next.js 16 App Router、React 19、TypeScript、Tailwind v4、shadcn UI。

---

## 文件结构

- 新建 `backend/app/worker/progress.py`：统一维护进度事件格式、Redis channel 名称和发布函数。
- 修改 `backend/app/worker/tasks.py`：worker 跑图时发布 `started`、`step`、`complete`、`error` 事件。
- 修改 `backend/app/pipeline/state.py`：新增 `PrismReport` 类型，作为稳定最终报告契约。
- 修改 `backend/app/pipeline/nodes.py`：新增 `synthesize_node`，先基于当前模拟搜索结果生成结构化报告。
- 修改 `backend/app/pipeline/graph.py`：把 `synthesize` 节点接到图的终点前。
- 新建 `backend/tests/test_progress.py`：测试 channel 命名和 Redis publish payload。
- 修改 `backend/tests/test_worker_tasks.py`：测试 worker 进度事件和最终报告结构。
- 修改 `backend/tests/test_routes.py`：补一个 SSE 终止事件转发的 smoke test。
- 新建 `frontend/lib/types.ts`：集中定义任务状态、进度事件和报告类型。
- 修改 `frontend/lib/api.ts`：使用共享类型，并让 SSE callback 变成 typed callback。
- 新建 `frontend/components/TaskTimeline.tsx`：把节点进度渲染成紧凑 timeline。
- 新建 `frontend/components/ReportView.tsx`：渲染结构化分析报告，不再把原始 JSON 当主界面。
- 修改 `frontend/components/ProgressPanel.tsx`：负责任务 fetch、SSE 订阅、timeline 和 report view 的编排。
- 修改 `frontend/app/result/[id]/page.tsx`：扩大布局，让结果页更像分析工作台。
- 修改 `frontend/app/page.tsx`：轻微调整首页文案和布局语气，让它和工作台一致。

---

### Task 1：后端进度事件工具

**文件：**
- 新建：`backend/app/worker/progress.py`
- 测试：`backend/tests/test_progress.py`

- [ ] **Step 1：先写失败测试**

新增 `backend/tests/test_progress.py`：

```python
import json
import unittest
from unittest.mock import AsyncMock

from app.worker.progress import progress_channel, publish_progress


class ProgressEventsTest(unittest.IsolatedAsyncioTestCase):
    def test_progress_channel_uses_task_id(self) -> None:
        self.assertEqual(
            progress_channel("abc-123"),
            "multiprism:progress:abc-123",
        )

    async def test_publish_progress_serializes_event_payload(self) -> None:
        redis = AsyncMock()

        await publish_progress(
            redis,
            "task-1",
            event="step",
            node="plan",
            message="规划搜索关键词",
        )

        redis.publish.assert_awaited_once()
        channel, payload = redis.publish.await_args.args
        self.assertEqual(channel, "multiprism:progress:task-1")
        self.assertEqual(
            json.loads(payload),
            {
                "event": "step",
                "node": "plan",
                "message": "规划搜索关键词",
            },
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2：运行测试，确认它失败**

运行：

```bash
cd backend
uv run python -m unittest tests.test_progress -v
```

预期：失败，错误包含 `ModuleNotFoundError: No module named 'app.worker.progress'`。

- [ ] **Step 3：实现进度事件工具**

新建 `backend/app/worker/progress.py`：

```python
import json
from typing import Any, Literal


ProgressEventName = Literal["started", "step", "complete", "error"]


def progress_channel(task_id: str) -> str:
    return f"multiprism:progress:{task_id}"


async def publish_progress(
    redis: Any,
    task_id: str,
    *,
    event: ProgressEventName,
    node: str | None = None,
    message: str | None = None,
    report: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"event": event}
    if node is not None:
        payload["node"] = node
    if message is not None:
        payload["message"] = message
    if report is not None:
        payload["report"] = report

    await redis.publish(progress_channel(task_id), json.dumps(payload, ensure_ascii=False))
```

- [ ] **Step 4：再次运行测试**

运行：

```bash
cd backend
uv run python -m unittest tests.test_progress -v
```

预期：通过。

- [ ] **Step 5：提交**

```bash
git add backend/app/worker/progress.py backend/tests/test_progress.py
git commit -m "feat: add worker progress event helper"
```

---

### Task 2：结构化报告节点

**文件：**
- 修改：`backend/app/pipeline/state.py`
- 修改：`backend/app/pipeline/nodes.py`
- 修改：`backend/app/pipeline/graph.py`
- 测试：`backend/tests/test_worker_tasks.py`

- [ ] **Step 1：先修改 worker 测试的期望报告结构**

在 `backend/tests/test_worker_tasks.py` 中，把 `_FakeCompiledGraph.ainvoke` 改成：

```python
class _FakeCompiledGraph:
    async def ainvoke(self, state, config):
        return {
            "final_report": {
                "summary": "政策影响分析的初步分析完成。",
                "stance_groups": [
                    {
                        "label": "支持",
                        "position": "强调政策收益",
                        "evidence": ["第1轮搜索结果0：政策影响分析 支持"],
                    },
                    {
                        "label": "反对",
                        "position": "强调执行风险",
                        "evidence": ["第1轮搜索结果1：政策影响分析 反对"],
                    },
                ],
                "tensions": ["不同来源对事件影响的叙述存在差异。"],
                "sources": [
                    {
                        "title": "第1轮搜索结果0：政策影响分析 支持",
                        "url": None,
                        "publisher": "模拟来源",
                        "stance": "支持",
                    }
                ],
            }
        }
```

把最终断言改成：

```python
self.assertEqual(
    update_task_status.await_args_list[1].kwargs["final_report"]["summary"],
    "政策影响分析的初步分析完成。",
)
self.assertEqual(
    update_task_status.await_args_list[1].kwargs["final_report"]["stance_groups"][0]["label"],
    "支持",
)
```

- [ ] **Step 2：运行测试，确认失败**

运行：

```bash
cd backend
uv run python -m unittest tests.test_worker_tasks -v
```

预期：失败，因为 `run_research_graph` 还在写入 `{"raw_results": ...}`。

- [ ] **Step 3：给 pipeline state 增加报告类型**

用下面内容替换 `backend/app/pipeline/state.py`：

```python
from typing import TypedDict


class PrismSource(TypedDict):
    title: str
    url: str | None
    publisher: str
    stance: str


class PrismStanceGroup(TypedDict):
    label: str
    position: str
    evidence: list[str]


class PrismReport(TypedDict):
    summary: str
    stance_groups: list[PrismStanceGroup]
    tensions: list[str]
    sources: list[PrismSource]


class PrismState(TypedDict):
    event_query: str
    search_queries: list[str]
    raw_results: list[str]
    retry_count: int
    final_report: PrismReport | None
```

- [ ] **Step 4：新增 synthesize 节点**

在 `backend/app/pipeline/nodes.py` 的 `reflect_node` 后面增加：

```python
def synthesize_node(state: PrismState) -> dict:
    event_query = state["event_query"]
    raw_results = state["raw_results"]
    support_evidence = [item for item in raw_results if "支持" in item]
    oppose_evidence = [item for item in raw_results if "反对" in item]

    return {
        "final_report": {
            "summary": f"{event_query}的初步分析完成。",
            "stance_groups": [
                {
                    "label": "支持",
                    "position": "强调事件带来的收益、必要性或正面影响。",
                    "evidence": support_evidence[:3],
                },
                {
                    "label": "反对",
                    "position": "强调事件带来的风险、代价或执行问题。",
                    "evidence": oppose_evidence[:3],
                },
            ],
            "tensions": ["不同来源对事件影响的叙述存在差异。"],
            "sources": [
                {
                    "title": item,
                    "url": None,
                    "publisher": "模拟来源",
                    "stance": "支持" if "支持" in item else "反对" if "反对" in item else "未知",
                }
                for item in raw_results
            ],
        }
    }
```

- [ ] **Step 5：把 synthesize 接进图里**

修改 `backend/app/pipeline/graph.py` 的 import：

```python
from app.pipeline.nodes import plan_node, search_node, reflect_node, should_continue, synthesize_node
```

添加节点：

```python
graph_builder.add_node("synthesize", synthesize_node)
```

修改 conditional edges：

```python
graph_builder.add_conditional_edges(
    "reflect",
    should_continue,
    {
        "continue": "search",
        "stop": "synthesize",
    },
)
graph_builder.add_edge("synthesize", END)
```

- [ ] **Step 6：worker 写入 `final_report`**

在 `backend/app/worker/tasks.py` 中，把成功更新数据库的部分改成：

```python
final_report = result.get("final_report")
if final_report is None:
    final_report = {
        "summary": f"{event_query}的分析完成，但没有生成结构化报告。",
        "stance_groups": [],
        "tensions": [],
        "sources": [],
    }

async with AsyncSessionLocal() as db:
    await update_task_status(
        db,
        task_uuid,
        TaskStatus.COMPLETED,
        final_report=final_report,
    )
```

- [ ] **Step 7：运行 worker 测试**

运行：

```bash
cd backend
uv run python -m unittest tests.test_worker_tasks -v
```

预期：通过。

- [ ] **Step 8：提交**

```bash
git add backend/app/pipeline/state.py backend/app/pipeline/nodes.py backend/app/pipeline/graph.py backend/app/worker/tasks.py backend/tests/test_worker_tasks.py
git commit -m "feat: add structured prism report"
```

---

### Task 3：发布真实 worker 进度

**文件：**
- 修改：`backend/app/worker/tasks.py`
- 修改：`backend/tests/test_worker_tasks.py`

- [ ] **Step 1：扩展 worker 测试，断言进度事件**

在 `backend/tests/test_worker_tasks.py` 增加：

```python
class _FakeRedis:
    def __init__(self):
        self.messages = []

    async def publish(self, channel, payload):
        self.messages.append((channel, payload))

    async def close(self):
        return None
```

在 `test_run_research_graph_uses_task_id_argument_from_arq_job` 中创建：

```python
redis = _FakeRedis()
```

并加入 patch：

```python
patch.object(tasks.aioredis, "from_url", return_value=redis),
```

在已有断言后增加：

```python
published_payloads = [payload for _, payload in redis.messages]
self.assertTrue(any('"event": "started"' in payload for payload in published_payloads))
self.assertTrue(any('"event": "complete"' in payload for payload in published_payloads))
self.assertTrue(any('"report"' in payload for payload in published_payloads))
```

- [ ] **Step 2：运行测试，确认失败**

运行：

```bash
cd backend
uv run python -m unittest tests.test_worker_tasks -v
```

预期：失败，因为 `tasks.aioredis` 还未导入，worker 也还没有发布进度事件。

- [ ] **Step 3：worker 引入 Redis 和 progress helper**

在 `backend/app/worker/tasks.py` 顶部添加：

```python
import redis.asyncio as aioredis

from app.worker.progress import publish_progress
```

- [ ] **Step 4：发布 started、step、complete、error 事件**

在 `run_research_graph` 中，`task_uuid = uuid.UUID(str(task_id))` 后添加：

```python
redis = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
```

状态更新为 running 后添加：

```python
await publish_progress(
    redis,
    str(task_uuid),
    event="started",
    message=f"开始分析：{event_query}",
)
```

`graph.ainvoke(...)` 返回后，数据库完成更新前添加：

```python
for node_name, message in [
    ("plan", "规划搜索关键词完成"),
    ("search", "相关报道搜索完成"),
    ("reflect", "覆盖度判断完成"),
    ("synthesize", "结构化报告生成完成"),
]:
    await publish_progress(redis, str(task_uuid), event="step", node=node_name, message=message)
```

数据库完成更新后添加：

```python
await publish_progress(
    redis,
    str(task_uuid),
    event="complete",
    message="任务完成",
    report=final_report,
)
```

在 `except Exception as exc` 分支里，失败状态写库后添加：

```python
await publish_progress(
    redis,
    str(task_uuid),
    event="error",
    message=str(exc),
)
```

在 `except` 同级添加：

```python
finally:
    await redis.close()
```

- [ ] **Step 5：运行 worker 测试**

运行：

```bash
cd backend
uv run python -m unittest tests.test_worker_tasks -v
```

预期：通过。

- [ ] **Step 6：提交**

```bash
git add backend/app/worker/tasks.py backend/tests/test_worker_tasks.py
git commit -m "feat: publish worker progress events"
```

---

### Task 4：前端共享类型和 API 契约

**文件：**
- 新建：`frontend/lib/types.ts`
- 修改：`frontend/lib/api.ts`

- [ ] **Step 1：新增共享类型**

创建 `frontend/lib/types.ts`：

```typescript
export type TaskStatus = "pending" | "running" | "completed" | "failed";

export interface PrismSource {
  title: string;
  url: string | null;
  publisher: string;
  stance: string;
}

export interface PrismStanceGroup {
  label: string;
  position: string;
  evidence: string[];
}

export interface PrismReport {
  summary: string;
  stance_groups: PrismStanceGroup[];
  tensions: string[];
  sources: PrismSource[];
}

export type ProgressEvent =
  | {
      event: "started";
      message?: string;
    }
  | {
      event: "step";
      node: "plan" | "search" | "reflect" | "synthesize" | string;
      message?: string;
    }
  | {
      event: "complete";
      message?: string;
      report?: PrismReport;
    }
  | {
      event: "error";
      message?: string;
    };

export interface TaskSnapshot {
  task_id: string;
  task_status: TaskStatus;
  event_query: string;
  final_report: PrismReport | null;
  error_message: string | null;
  created_at: string;
}
```

- [ ] **Step 2：API client 使用共享类型**

修改 `frontend/lib/api.ts` 的 imports：

```typescript
import type { ProgressEvent, TaskSnapshot } from "@/lib/types";
```

修改 `getTask`：

```typescript
export async function getTask(taskId: string) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  return readApiData<TaskSnapshot>(res);
}
```

修改 `subscribeToProgress` 函数签名：

```typescript
export function subscribeToProgress(
  taskId: string,
  onMessage: (data: ProgressEvent) => void,
  onDone: () => void
): EventSource {
```

在 `es.onmessage` 中修改解析：

```typescript
const data = JSON.parse(event.data) as ProgressEvent;
onMessage(data);
```

- [ ] **Step 3：运行前端 lint**

运行：

```bash
cd frontend
npm run lint
```

预期：通过。

- [ ] **Step 4：提交**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat: add typed frontend agent contracts"
```

---

### Task 5：Timeline 和报告组件

**文件：**
- 新建：`frontend/components/TaskTimeline.tsx`
- 新建：`frontend/components/ReportView.tsx`
- 修改：`frontend/components/ProgressPanel.tsx`

- [ ] **Step 1：创建 timeline 组件**

创建 `frontend/components/TaskTimeline.tsx`：

```tsx
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

import type { ProgressEvent, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const NODE_LABELS: Record<string, string> = {
  plan: "规划检索",
  search: "搜索报道",
  reflect: "判断覆盖",
  synthesize: "生成报告",
};

const NODE_ORDER = ["plan", "search", "reflect", "synthesize"];

interface TaskTimelineProps {
  events: ProgressEvent[];
  status: TaskStatus;
}

export default function TaskTimeline({ events, status }: TaskTimelineProps) {
  const completedNodes = new Set(
    events.filter((event) => event.event === "step").map((event) => event.node)
  );
  const hasError = events.some((event) => event.event === "error") || status === "failed";

  return (
    <div className="grid gap-3 sm:grid-cols-4">
      {NODE_ORDER.map((node) => {
        const completed = completedNodes.has(node) || status === "completed";
        const active = !completed && status === "running" && !hasError;
        const Icon = hasError && !completed ? XCircle : completed ? CheckCircle2 : active ? Loader2 : Circle;

        return (
          <div
            key={node}
            className="flex min-h-20 flex-col justify-between rounded-md border bg-card p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{NODE_LABELS[node]}</span>
              <Icon
                className={cn(
                  "size-4 text-muted-foreground",
                  completed && "text-emerald-600",
                  active && "animate-spin text-primary",
                  hasError && !completed && "text-destructive"
                )}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {completed ? "已完成" : active ? "进行中" : hasError ? "未完成" : "等待中"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2：创建结构化报告组件**

创建 `frontend/components/ReportView.tsx`：

```tsx
import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PrismReport } from "@/lib/types";

interface ReportViewProps {
  report: PrismReport;
}

export default function ReportView({ report }: ReportViewProps) {
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">核心摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">{report.summary}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {report.stance_groups.map((group) => (
          <Card key={group.label}>
            <CardHeader className="space-y-2">
              <Badge variant="outline" className="w-fit">
                {group.label}
              </Badge>
              <CardTitle className="text-base">{group.position}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="grid gap-2 text-sm text-muted-foreground">
                {group.evidence.map((item) => (
                  <li key={item} className="rounded-md bg-muted px-3 py-2">
                    {item}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">主要分歧</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-2 text-sm text-muted-foreground">
            {report.tensions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">来源</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {report.sources.map((source) => (
            <div key={`${source.title}-${source.stance}`} className="flex items-start justify-between gap-3 rounded-md border p-3">
              <div className="grid gap-1">
                <span className="text-sm font-medium">{source.title}</span>
                <span className="text-xs text-muted-foreground">
                  {source.publisher} / {source.stance}
                </span>
              </div>
              {source.url && (
                <a href={source.url} target="_blank" rel="noreferrer" aria-label="打开来源">
                  <ExternalLink className="size-4 text-muted-foreground" />
                </a>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3：重构 ProgressPanel 使用新组件**

在 `frontend/components/ProgressPanel.tsx` 中，删除本地 `ProgressEvent`、`NODE_LABELS` 和 `Record<string, unknown>` report 类型。新增 imports：

```tsx
import ReportView from "@/components/ReportView";
import TaskTimeline from "@/components/TaskTimeline";
import type { PrismReport, ProgressEvent, TaskStatus } from "@/lib/types";
```

修改 state：

```tsx
const [status, setStatus] = useState<TaskStatus>("pending");
const [events, setEvents] = useState<ProgressEvent[]>([]);
const [report, setReport] = useState<PrismReport | null>(null);
```

用结构化报告替换原始 JSON：

```tsx
{report && <ReportView report={report} />}
```

在事件列表上方加入 timeline：

```tsx
<TaskTimeline events={events} status={status} />
```

事件列表中优先显示后端传来的 `message`：

```tsx
{event.event === "started" && (event.message ?? "任务开始执行")}
{event.event === "step" && (event.message ?? `节点完成：${event.node}`)}
{event.event === "complete" && (event.message ?? "任务完成")}
{event.event === "error" && `出错：${event.message ?? "未知错误"}`}
```

- [ ] **Step 4：运行前端 lint**

运行：

```bash
cd frontend
npm run lint
```

预期：通过。

- [ ] **Step 5：提交**

```bash
git add frontend/components/TaskTimeline.tsx frontend/components/ReportView.tsx frontend/components/ProgressPanel.tsx
git commit -m "feat: render agent timeline and report"
```

---

### Task 6：结果页工作台布局

**文件：**
- 修改：`frontend/app/result/[id]/page.tsx`
- 修改：`frontend/app/page.tsx`

- [ ] **Step 1：加宽结果页，让任务 ID 退到次要信息**

用下面内容替换 `frontend/app/result/[id]/page.tsx` 的 `return` 部分：

```tsx
return (
  <main className="min-h-screen bg-background px-4 py-8 sm:px-6 lg:px-8">
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div className="flex flex-col gap-3 border-b pb-5">
        <Link href="/" className="w-fit text-sm text-muted-foreground hover:text-foreground">
          返回首页
        </Link>
        <div className="grid gap-2">
          <h1 className="text-2xl font-semibold tracking-normal">多棱镜分析工作台</h1>
          <p className="text-sm text-muted-foreground">任务 ID：{id}</p>
        </div>
      </div>

      <ProgressPanel taskId={id} />
    </div>
  </main>
);
```

- [ ] **Step 2：首页文案和工作台语气对齐**

在 `frontend/app/page.tsx` 中，把当前 `main` 内容替换为：

```tsx
<main className="min-h-screen bg-background px-4 py-12 sm:px-6 lg:px-8">
  <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
    <div className="flex flex-col gap-2">
      <h1 className="text-3xl font-semibold tracking-normal">多棱镜 Agent</h1>
      <p className="text-sm leading-6 text-muted-foreground">
        输入一个公共事件，生成跨来源、跨立场的报道差异分析。
      </p>
    </div>
    <EventForm />
  </div>
</main>
```

- [ ] **Step 3：运行前端 lint**

运行：

```bash
cd frontend
npm run lint
```

预期：通过。

- [ ] **Step 4：提交**

```bash
git add frontend/app/result/[id]/page.tsx frontend/app/page.tsx
git commit -m "feat: polish agent workbench layout"
```

---

### Task 7：端到端验证

**文件：**
- 只有验证失败并定位到具体 bug 时才修改文件。

- [ ] **Step 1：运行后端单元测试**

运行：

```bash
cd backend
uv run python -m unittest discover -s tests -v
```

预期：全部通过。

- [ ] **Step 2：运行前端 lint**

运行：

```bash
cd frontend
npm run lint
```

预期：通过。

- [ ] **Step 3：运行前端生产构建**

运行：

```bash
cd frontend
npm run build
```

预期：Next.js build 成功完成。

- [ ] **Step 4：本地服务手动 smoke test**

按 `backend/README.md` 中已有方式启动后端 API、Redis 和 worker。然后运行：

```bash
cd frontend
npm run dev
```

打开 `http://localhost:7777`，提交 `某地推行的新政策`，验证：

- 结果页能打开并展示 task id。
- timeline 依次展示规划、搜索、反思、生成报告。
- 报告展示摘要、立场组、主要分歧和来源。
- 原始 JSON 不再作为主要结果 UI。

- [ ] **Step 5：提交验证修复**

如果验证过程中有必要修复 bug：

```bash
git add backend frontend
git commit -m "fix: stabilize agent workbench verification"
```

如果没有任何代码改动，不创建空 commit。

---

## 自检

**需求覆盖：** 本计划覆盖了适合当前项目借鉴 LangChain Next.js template 的部分：流式进度体验、结构化输出、结果页工作台化。RAG ingestion、真实外部搜索和 LLM 接入刻意不放进这个 MVP，避免第一版范围过大。

**占位符检查：** 没有使用 `TBD`、`TODO`、`implement later`、`fill in details` 或 “Similar to Task N” 这类不可执行占位。

**类型一致性：** 后端报告字段统一为 `summary`、`stance_groups`、`tensions`、`sources`；前端 `PrismReport` 使用同名字段。进度事件名称在 `progress.py`、worker publish、`lib/types.ts` 和 `ProgressPanel` 中保持一致。

---

计划已保存到 `docs/superpowers/plans/2026-07-02-agent-workbench.md`。执行方式有两个：

**1. Subagent-Driven（推荐）**：每个任务派发一个 fresh subagent，我在任务之间 review，迭代更快。

**2. Inline Execution**：在当前会话中用 `executing-plans` 按批次执行，并在关键节点检查。
