import { FileSearch, Layers3 } from "lucide-react";

import EventForm from "@/components/EventForm";

const reportPoints = [
  {
    title: "哪些事实一致",
    description: "快速确认多方来源都承认的基础事实。",
  },
  {
    title: "哪里出现分歧",
    description: "把不同来源的叙述差异拆成清楚的议题。",
  },
  {
    title: "还缺什么信息",
    description: "列出报道没有覆盖、但值得继续追查的角度。",
  },
];

// 这个页面不需要 "use client"，因为它本身没有用任何浏览器API
// 只是把EventForm组件渲染出来，EventForm自己内部已经有 "use client" 了
export default function Home() {
  return (
    <main className="min-h-[100dvh] bg-background px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl border bg-muted">
              <Layers3 className="size-4" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium leading-none">多棱镜 Agent</p>
              <p className="mt-1 text-xs text-muted-foreground">媒体立场分析助手</p>
            </div>
          </div>
        </header>

        <section className="overflow-hidden rounded-3xl border bg-card shadow-sm">
          <div className="grid lg:grid-cols-[0.86fr_1.14fr]">
            <div className="flex min-h-[420px] flex-col justify-between bg-foreground p-6 text-background sm:p-8 lg:p-10">
              <div className="space-y-5">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-background/20 px-3 py-1.5 text-xs text-background/70">
                  <FileSearch className="size-3.5" aria-hidden="true" />
                  输入事件，生成报告
                </div>
                <div className="space-y-4">
                  <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                    把杂乱报道整理成判断依据
                  </h1>
                  <p className="max-w-xl text-base leading-7 text-background/70">
                    多棱镜会检索多方来源，提炼共识、分歧和信息缺口，生成一份可读的分析报告。
                  </p>
                </div>
              </div>

              <div className="mt-10 grid gap-3">
                {reportPoints.map((item) => (
                  <div key={item.title} className="border-t border-background/15 pt-3">
                    <div className="text-sm font-medium">{item.title}</div>
                    <p className="mt-1 text-sm leading-6 text-background/60">
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center p-4 sm:p-6 lg:p-10">
              <div className="w-full">
                <div className="mb-6 space-y-2">
                  <h2 className="text-2xl font-semibold tracking-tight">
                    开始分析
                  </h2>
                  <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                    直接描述你关心的事件。地点、主体、时间越明确，报告越稳定。
                  </p>
                </div>
                <EventForm />
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
