FROM python:3.11-alpine

RUN apk add --no-cache git build-base libffi-dev openssl-dev

# 設定環境變數：確保 Python 輸出不被緩衝
ENV PYTHONUNBUFFERED=1

# 設定工作目錄為 /workspace（RefactorAgent 的 root_dir）
WORKDIR /workspace

# 建立必要的目錄結構
RUN mkdir -p /workspace/memory /workspace/artifacts /workspace/agent

# 安裝 Agent 依賴（包含 FastAPI）
COPY agent/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# 複製 Agent 程式碼到 /workspace/agent/
COPY agent/*.py /workspace/agent/
COPY agent/.env* /workspace/agent/

# 複製 memory 資料夾（包含 AGENTS.md）
COPY agent/workspace/memory/ /workspace/memory/

# 確保 .env 存在
RUN if [ ! -f /workspace/agent/.env ] && [ -f /workspace/agent/.env.example ]; then \
        cp /workspace/agent/.env.example /workspace/agent/.env; \
    fi

# 暴露 AI Server port
EXPOSE 8000

# 啟動 AI Server（在 /workspace 目錄下執行）
CMD ["uvicorn", "agent.ai_server:app", "--host", "0.0.0.0", "--port", "8000"]
