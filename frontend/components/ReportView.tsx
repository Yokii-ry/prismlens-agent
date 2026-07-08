"use client";

import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  GitCompareArrows,
  SearchX,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface DivergenceItem {
  topic: string;
  perspectives: string[];
}

interface PrismReport {
  consensus: string[];
  divergence: DivergenceItem[];
  silence: string[];
}

interface ReportViewProps {
  report: Record<string, unknown>;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isDivergenceItem(value: unknown): value is DivergenceItem {
  if (!value || typeof value !== "object") return false;

  const item = value as Record<string, unknown>;
  return typeof item.topic === "string" && isStringArray(item.perspectives);
}

function parseReport(report: Record<string, unknown>): PrismReport | null {
  const { consensus, divergence, silence } = report;

  if (
    !isStringArray(consensus) ||
    !Array.isArray(divergence) ||
    !divergence.every(isDivergenceItem) ||
    !isStringArray(silence)
  ) {
    return null;
  }

  return { consensus, divergence, silence };
}

export default function ReportView({ report }: ReportViewProps) {
  const parsed = parseReport(report);

  if (!parsed) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileText className="size-4" aria-hidden="true" />
            原始报告
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-[480px] overflow-auto rounded-lg bg-muted p-4 text-xs leading-6 text-muted-foreground">
            {JSON.stringify(report, null, 2)}
          </pre>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    { label: "共识", value: parsed.consensus.length },
    { label: "分歧", value: parsed.divergence.length },
    { label: "缺口", value: parsed.silence.length },
  ];

  return (
    <section className="space-y-5" aria-label="分析结果">
      <Card className="bg-muted/30">
        <CardHeader className="border-b">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2">
              <CardTitle className="flex items-center gap-2 text-xl">
                <FileText className="size-5" aria-hidden="true" />
                分析结果
              </CardTitle>
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                先看共同事实，再逐项比较冲突叙述，最后检查尚未覆盖的信息缺口。
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {stats.map((item) => (
                <div
                  key={item.label}
                  className="rounded-lg border bg-background px-4 py-3 text-center"
                >
                  <div className="text-lg font-semibold leading-none">
                    {item.value}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {item.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {parsed.consensus.map((item, index) => (
              <div
                key={item}
                className="flex gap-3 rounded-lg border bg-background p-4"
              >
                <CheckCircle2
                  className="mt-0.5 size-4 shrink-0 text-emerald-600"
                  aria-hidden="true"
                />
                <p className="text-sm leading-6">
                  <span className="mr-2 font-mono text-xs text-muted-foreground">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {item}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <GitCompareArrows className="size-4" aria-hidden="true" />
            分歧议题
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {parsed.divergence.map((item) => (
            <article key={item.topic} className="rounded-lg border">
              <div className="flex flex-col gap-2 border-b bg-muted/40 p-4 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-medium leading-6">{item.topic}</h3>
                <Badge variant="outline">{item.perspectives.length} 个角度</Badge>
              </div>
              <div className="divide-y">
                {item.perspectives.map((perspective, index) => (
                  <div key={perspective} className="grid gap-3 p-4 sm:grid-cols-[96px_1fr]">
                    <div className="font-mono text-xs text-muted-foreground">
                      视角 {index + 1}
                    </div>
                    <p className="text-sm leading-6 text-foreground/90">
                      {perspective}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </CardContent>
      </Card>

      <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-900/60 dark:bg-amber-950/20">
        <CardHeader className="border-b border-amber-200/70 dark:border-amber-900/60">
          <CardTitle className="flex items-center gap-2 text-base">
            <SearchX className="size-4" aria-hidden="true" />
            信息缺口
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {parsed.silence.map((item) => (
              <div key={item} className="flex gap-3 rounded-lg bg-background/75 p-4 ring-1 ring-border">
                <AlertTriangle
                  className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400"
                  aria-hidden="true"
                />
                <p className="text-sm leading-6">{item}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
