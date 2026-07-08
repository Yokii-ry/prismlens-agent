"use client";

// "use client" 告诉 Next.js 这个组件在浏览器端运行
// 因为用到了 useState、事件处理这些需要浏览器环境的东西
// 没有这行的话，Next.js 默认在服务器端渲染，useState 会报错

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createTask } from "@/lib/api";

const EXAMPLE_QUERIES = [
  "深圳近期高温天气与台风影响",
  "新能源汽车补贴调整争议",
];

export default function EventForm() {
  // 用户输入的事件描述
  const [eventQuery, setEventQuery] = useState("");
  // 是否正在提交中，用来控制按钮的disabled状态，防止重复提交
  const [loading, setLoading] = useState(false);
  // 错误信息
  const [error, setError] = useState("");

  // Next.js的路由跳转工具，类比React Router的useNavigate
  const router = useRouter();

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    // 简单校验：不能提交空内容
    if (!eventQuery.trim()) {
      setError("请输入事件描述");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // 调后端接口，提交任务
      const data = await createTask(eventQuery);
      // 提交成功后，跳转到结果页，把task_id带过去
      router.push(`/result/${data.task_id}`);
    } catch {
      setError("提交失败，请检查后端服务是否启动");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="space-y-2">
        <label htmlFor="event-query" className="text-sm font-medium">
          要分析的事件
        </label>
        <textarea
          id="event-query"
          placeholder="例如：深圳近期高温天气与台风影响"
          value={eventQuery}
          // 每次输入变化，更新eventQuery这个state
          onChange={(e) => setEventQuery(e.target.value)}
          disabled={loading}
          rows={5}
          className="min-h-40 w-full resize-none rounded-2xl border border-input bg-background px-4 py-3 text-sm leading-6 shadow-xs outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">试试</span>
        {EXAMPLE_QUERIES.map((query) => (
          <button
            key={query}
            type="button"
            onClick={() => {
              setEventQuery(query);
              setError("");
            }}
            disabled={loading}
            className="rounded-full border bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:bg-background hover:text-foreground disabled:pointer-events-none disabled:opacity-60"
          >
            {query}
          </button>
        ))}
      </div>

      <Button type="submit" size="lg" className="h-11 w-full gap-2" disabled={loading}>
        {loading ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            提交中
          </>
        ) : (
          <>
            <SendHorizonal className="size-4" aria-hidden="true" />
            开始分析
          </>
        )}
      </Button>

      {/* 只有error不为空时才显示错误信息 */}
      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </form>
  );
}
