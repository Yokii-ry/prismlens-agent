"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  Search,
  Send,
  XCircle,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getTask, subscribeToProgress } from "@/lib/api";
import ReportView from "@/components/ReportView";

// 定义每一条进度消息的类型
interface ProgressEvent {
  event: "started" | "step" | "complete" | "error";
  node?: string;   // "step"类型的消息会带上当前跑的是哪个节点
  message?: string; // "error"类型的消息会带上错误描述
  report?: Record<string, unknown>; // "complete"类型的消息会带上最终报告
}

// 节点名字的中文映射，让进度展示更友好
const NODE_LABELS: Record<string, string> = {
  plan: "规划搜索关键词",
  search: "搜索相关报道",
  reflect: "判断覆盖是否足够",
  generate_report: "生成分析报告",
  synthesize: "生成分析报告",
};

// 任务状态对应的Badge颜色
const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive"> = {
  pending: "secondary",
  running: "default",
  completed: "default",
  failed: "destructive",
};

interface Props {
  taskId: string;
}

export default function ProgressPanel({ taskId }: Props) {
  // 任务当前状态
  const [status, setStatus] = useState<string>("pending");
  // 进度消息列表，每收到一条就追加进来
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  // 最终报告
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  // 是否已经结束（complete或error）
  const [done, setDone] = useState(false);

  useEffect(() => {
    let es: EventSource | undefined;
    let cancelled = false;

    async function loadTask() {
      try {
        // 组件挂载时，先查一次任务状态（可能任务已经跑完了，不需要再订阅SSE）
        const data = await getTask(taskId);
        if (cancelled) return;

        setStatus(data.task_status);
        if (data.task_status === "completed") {
          setReport(data.final_report);
          setDone(true);
          return;
        }
        if (data.task_status === "failed") {
          setDone(true);
          return;
        }

        // 如果任务还没结束，订阅SSE接收实时进度
        es = subscribeToProgress(
          taskId,
          // onMessage：每收到一条进度消息，追加到events列表里
          (data) => {
            const event = data as unknown as ProgressEvent;
            setEvents((prev) => [...prev, event]);

            // 收到complete事件，更新状态和报告
            if (event.event === "complete") {
              setStatus("completed");
              if (event.report) setReport(event.report);
            }

            // 收到error事件，更新状态
            if (event.event === "error") {
              setStatus("failed");
            }
          },
          // onDone：SSE连接关闭时，标记任务结束
          () => setDone(true)
        );
      } catch {
        if (cancelled) return;
        setEvents((prev) => [
          ...prev,
          { event: "error", message: "无法连接后端服务" },
        ]);
        setStatus("failed");
        setDone(true);
      }
    }

    loadTask();

    // useEffect的清理函数：组件卸载时关闭SSE连接，避免内存泄漏
    // 类比addEventListener要配对removeEventListener
    return () => {
      cancelled = true;
      es?.close();
    };
  }, [taskId]); // 只在taskId变化时重新执行

  return (
    <div className="flex flex-col gap-4">
      {/* 任务状态Badge */}
      <Card className="bg-muted/20">
        <CardContent>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-medium">任务状态</div>
              <p className="mt-1 text-sm text-muted-foreground">
                {status === "completed"
                  ? "分析已完成，报告已生成。"
                  : status === "failed"
                    ? "任务未能完成，请检查后端服务或任务日志。"
                    : "系统正在准备或执行分析任务。"}
              </p>
            </div>
            <Badge variant={STATUS_COLORS[status] ?? "default"}>{status}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* 实时进度列表 */}
      {events.length > 0 && (
        <Card className={status === "failed" ? "border-destructive/25" : undefined}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Search className="size-4" aria-hidden="true" />
              执行进度
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-3">
              {events.map((event, index) => (
                <li key={index} className="flex items-start gap-3 text-sm">
                  <ProgressEventIcon event={event} />
                  <span className="leading-6">
                    {event.event === "started" && "任务开始执行"}
                    {event.event === "step" && (
                      // 优先用中文映射，没有的话直接显示节点名
                      NODE_LABELS[event.node ?? ""] ?? `节点完成：${event.node}`
                    )}
                    {event.event === "complete" && "任务完成"}
                    {event.event === "error" && `出错：${event.message}`}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 最终报告，只有任务完成后才显示 */}
      {report && (
        <ReportView report={report} />
      )}

      {/* 任务还在跑，显示一个等待提示 */}
      {!done && status === "running" && (
        <div className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          正在分析中，请稍候
        </div>
      )}
    </div>
  );
}

function ProgressEventIcon({ event }: { event: ProgressEvent }) {
  if (event.event === "started") {
    return (
      <Send
        className="mt-1 size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
    );
  }
  if (event.event === "step") {
    return (
      <Circle
        className="mt-1 size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
    );
  }
  if (event.event === "complete") {
    return (
      <CheckCircle2
        className="mt-1 size-4 shrink-0 text-emerald-600"
        aria-hidden="true"
      />
    );
  }
  if (event.event === "error") {
    return (
      <XCircle
        className="mt-1 size-4 shrink-0 text-destructive"
        aria-hidden="true"
      />
    );
  }

  return (
    <Loader2
      className="mt-1 size-4 shrink-0 animate-spin text-muted-foreground"
      aria-hidden="true"
    />
  );
}
