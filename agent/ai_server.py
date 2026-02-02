"""Container AI Server - HTTP interface for CloudRun (Async Task Pattern)"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import logging
import sys
import uuid
import traceback

from agent.models import AnthropicModelProvider
from agent.deep_agent import RefactorAgent

# 配置 logging 輸出到 stdout（確保日誌可被收集）
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI(title="AI Server", version="1.0.0")
logger = logging.getLogger(__name__)

# 任務狀態枚舉
class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

# 內存任務儲存（單容器內有效）
tasks: Dict[str, Dict] = {}

# 日誌儲存（用於 stream）
task_logs: Dict[str, list] = {}

class RunRequest(BaseModel):
    init_prompt: str
    verbose: bool = True

class CloneRequest(BaseModel):
    repo_url: str
    branch: str = "main"

class RunResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None


def log_task(task_id: str, message: str):
    """記錄任務日誌（用於 stream）"""
    if task_id not in task_logs:
        task_logs[task_id] = []
    timestamp = datetime.utcnow().isoformat()
    task_logs[task_id].append({"timestamp": timestamp, "message": message})
    logger.info(f"[{task_id}] {message}")


def execute_agent(task_id: str, init_prompt: str, verbose: bool):
    """背景執行 Agent（在 BackgroundTasks 中執行）"""
    try:
        # 初始化日誌
        task_logs[task_id] = []

        # 更新狀態為 RUNNING
        tasks[task_id]["status"] = TaskStatus.RUNNING
        tasks[task_id]["started_at"] = datetime.utcnow().isoformat()

        print(f"🚀 [DEBUG] Task {task_id}: 開始執行", flush=True)
        log_task(task_id, "🚀 開始執行 Agent")

        # 初始化 LLM
        print(f"🔧 [DEBUG] Task {task_id}: 初始化 LLM", flush=True)
        log_task(task_id, "🔧 初始化 LLM...")
        provider = AnthropicModelProvider()
        model = provider.get_model()
        print(f"✅ [DEBUG] Task {task_id}: LLM 初始化完成", flush=True)
        log_task(task_id, "✅ LLM 初始化完成")

        # 建立並執行 RefactorAgent
        print(f"🤖 [DEBUG] Task {task_id}: 建立 RefactorAgent", flush=True)
        log_task(task_id, "🤖 建立 RefactorAgent...")
        agent = RefactorAgent(model, verbose=verbose)
        print(f"✅ [DEBUG] Task {task_id}: RefactorAgent 建立完成", flush=True)
        log_task(task_id, "✅ RefactorAgent 建立完成")

        # 定義事件回調函數，將 chunk 事件轉發到日誌
        def handle_chunk_event(event_type: str, data: dict):
            """處理 ChunkParser 的事件"""
            import json
            # 將事件序列化為 JSON 並記錄
            event_log = {
                "event_type": event_type,
                "data": data
            }
            log_task(task_id, f"[{event_type}] {json.dumps(data, ensure_ascii=False, default=str)}")

        print(f"▶️  [DEBUG] Task {task_id}: 開始執行 Agent", flush=True)
        log_task(task_id, f"▶️  執行 Agent，init_prompt: {init_prompt[:100]}...")
        agent.run(user_message=init_prompt, event_callback=handle_chunk_event)

        # 標記完成
        tasks[task_id]["status"] = TaskStatus.SUCCESS
        tasks[task_id]["finished_at"] = datetime.utcnow().isoformat()
        print(f"✅ [DEBUG] Task {task_id}: Agent 執行完成", flush=True)
        log_task(task_id, "✅ Agent 執行完成")

    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}"
        print(f"❌ [DEBUG] Task {task_id}: 錯誤 - {error_msg}", flush=True)
        print(f"[DEBUG] Traceback:\n{traceback.format_exc()}", flush=True)
        log_task(task_id, f"❌ 錯誤: {error_msg}")
        log_task(task_id, f"Traceback: {traceback.format_exc()}")
        logger.error(f"[{task_id}] {error_msg}\n{traceback.format_exc()}")
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["error_message"] = error_msg
        tasks[task_id]["finished_at"] = datetime.utcnow().isoformat()


@app.post("/run", response_model=RunResponse)
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    """啟動 Agent 執行（異步模式）

    立即返回 task_id，Agent 在背景執行。
    使用 GET /tasks/{task_id} 查詢執行狀態。
    """
    # 生成唯一 task_id
    task_id = str(uuid.uuid4())

    # 建立任務記錄
    tasks[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "init_prompt": request.init_prompt,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
    }

    # 啟動背景任務
    background_tasks.add_task(
        execute_agent,
        task_id=task_id,
        init_prompt=request.init_prompt,
        verbose=request.verbose
    )

    logger.info(f"[{task_id}] 任務已建立，開始背景執行")

    return RunResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Agent 任務已啟動，正在背景執行"
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查詢任務執行狀態"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
        error_message=task.get("error_message"),
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/tasks")
async def list_tasks():
    """列出所有任務（調試用）"""
    return {"total": len(tasks), "tasks": list(tasks.values())}


@app.get("/tasks/{task_id}/stream")
async def stream_task_logs(task_id: str):
    """SSE 串流任務執行日誌（支援結構化事件）"""
    from sse_starlette.sse import EventSourceResponse
    import asyncio
    import json as json_lib

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        """生成 SSE events"""
        last_index = 0

        while True:
            # 檢查任務狀態
            task = tasks.get(task_id)
            if not task:
                break

            # 發送新日誌
            if task_id in task_logs:
                current_logs = task_logs[task_id]
                new_logs = current_logs[last_index:]

                for log in new_logs:
                    message = log['message']

                    # 嘗試解析是否為結構化事件（[event_type] JSON）
                    if message.startswith('[') and ']' in message:
                        try:
                            # 提取 event_type 和 JSON 數據
                            close_bracket = message.index(']')
                            event_type = message[1:close_bracket]
                            json_data = message[close_bracket + 2:]  # 跳過 '] '

                            # 嘗試解析 JSON
                            data = json_lib.loads(json_data)

                            # 發送結構化事件
                            yield {
                                "event": event_type,
                                "data": json_lib.dumps(data, ensure_ascii=False)
                            }
                        except (ValueError, json_lib.JSONDecodeError):
                            # 解析失敗，作為普通日誌發送
                            yield {
                                "event": "log",
                                "data": json_lib.dumps({
                                    "timestamp": log['timestamp'],
                                    "message": message
                                }, ensure_ascii=False)
                            }
                    else:
                        # 普通日誌訊息
                        yield {
                            "event": "log",
                            "data": json_lib.dumps({
                                "timestamp": log['timestamp'],
                                "message": message
                            }, ensure_ascii=False)
                        }

                last_index = len(current_logs)

            # 如果任務完成，發送完成事件並結束
            if task["status"] in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                yield {
                    "event": "status",
                    "data": json_lib.dumps({
                        "status": task['status'].lower(),
                        "finished_at": task.get('finished_at'),
                        "error_message": task.get('error_message')
                    }, ensure_ascii=False)
                }
                break

            await asyncio.sleep(0.5)  # 每 0.5 秒檢查一次（更即時）

    return EventSourceResponse(event_generator())
