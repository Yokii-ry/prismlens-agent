// 后端接口地址，开发阶段指向本地FastAPI
const API_BASE = "http://127.0.0.1:8000/api";

interface ApiResponse<T> {
  code: string;
  status: "success" | "error";
  message: string;
  data: T;
}

interface TaskData {
  task_id: string;
  task_status: string;
  event_query: string;
  final_report: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
}

const pendingTaskRequests = new Map<string, Promise<TaskData>>();

async function readApiData<T>(res: Response): Promise<T> {
  const payload = (await res.json()) as ApiResponse<T>;
  if (!res.ok || payload.status !== "success") {
    throw new Error(payload.message || "请求失败");
  }
  return payload.data;
}

// 提交任务接口
// 返回值是 { task_id: string, status: string }
export async function createTask(eventQuery: string) {
  const res = await fetch(
    // 注意后端接口用的是query参数，不是请求body
    `${API_BASE}/tasks?event_query=${encodeURIComponent(eventQuery)}`,
    { method: "POST" }
  );
  return readApiData<{ task_id: string; task_status: string }>(res);
}

// 查询任务状态接口
export async function getTask(taskId: string) {
  const pending = pendingTaskRequests.get(taskId);
  if (pending) return pending;

  const request = fetch(`${API_BASE}/tasks/${taskId}`)
    .then((res) => readApiData<TaskData>(res))
    .finally(() => {
      pendingTaskRequests.delete(taskId);
    });

  pendingTaskRequests.set(taskId, request);
  return request;
}

// 订阅SSE进度推送
// 用法：subscribeToProgress(taskId, (event) => { console.log(event) })
export function subscribeToProgress(
  taskId: string,
  // onMessage是一个回调函数，每收到一条SSE消息就调用一次
  onMessage: (data: Record<string, unknown>) => void,
  // onDone是任务结束时的回调（complete或error）
  onDone: () => void
): EventSource {
  // EventSource是浏览器原生支持SSE的API，不需要装任何库
  const es = new EventSource(`${API_BASE}/tasks/${taskId}/stream`);

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
      // 收到complete或error，说明任务结束，关闭SSE连接
      if (data.event === "complete" || data.event === "error") {
        es.close();
        onDone();
      }
    } catch {
      // JSON解析失败，忽略这条消息
    }
  };

  es.onerror = () => {
    es.close();
    onDone();
  };

  return es;
}
