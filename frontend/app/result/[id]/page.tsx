import Link from "next/link";
import { ArrowLeft, Layers3 } from "lucide-react";

import ProgressPanel from "@/components/ProgressPanel";

// Next.js App Router里，动态路由页面会自动收到params参数
// [id] 对应的值会通过 params.id 传进来
interface Props {
  params: Promise<{ id: string }>;
}

export default async function ResultPage({ params }: Props) {
  const { id } = await params;

  return (
    <main className="min-h-[100dvh] bg-background px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {/* 标题区域 */}
        <header className="flex flex-col gap-5 border-b pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl border bg-muted">
              <Layers3 className="size-4" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">分析任务</h1>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                任务 ID：{id}
              </p>
            </div>
          </div>

          <Link
            href="/"
            className="inline-flex w-fit items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            返回首页
          </Link>
        </header>

        {/* 进度和结果展示 */}
        <ProgressPanel taskId={id} />

      </div>
    </main>
  );
}
