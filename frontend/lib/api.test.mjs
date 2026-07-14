import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import ts from "typescript";

function loadApiModule() {
  const source = readFileSync(new URL("./api.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const dir = mkdtempSync(join(tmpdir(), "prismlens-api-test-"));
  const modulePath = join(dir, "api.cjs");
  writeFileSync(modulePath, outputText);
  return import(modulePath);
}

test("getTask dedupes concurrent requests for the same task", async () => {
  const { getTask } = await loadApiModule();
  const calls = [];

  globalThis.fetch = async (url) => {
    calls.push(String(url));
    return {
      ok: true,
      json: async () => ({
        status: "success",
        message: "Task fetched",
        data: {
          task_id: "task-1",
          task_status: "running",
          event_query: "query",
          final_report: null,
          error_message: null,
          created_at: "2026-07-02T00:00:00",
        },
      }),
    };
  };

  const [first, second] = await Promise.all([getTask("task-1"), getTask("task-1")]);

  assert.equal(calls.length, 1);
  assert.deepEqual(first, second);
});

test("createTask uses the unversioned API prefix by default", async () => {
  const previousApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  try {
    const { createTask } = await loadApiModule();
    const calls = [];

    globalThis.fetch = async (url) => {
      calls.push(String(url));
      return {
        ok: true,
        json: async () => ({
          status: "success",
          message: "Task created",
          data: {
            task_id: "task-1",
            task_status: "pending",
          },
        }),
      };
    };

    await createTask("query");

    assert.equal(
      calls[0],
      "http://127.0.0.1:8000/api/tasks?event_query=query"
    );
  } finally {
    if (previousApiBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
    } else {
      process.env.NEXT_PUBLIC_API_BASE_URL = previousApiBaseUrl;
    }
  }
});
