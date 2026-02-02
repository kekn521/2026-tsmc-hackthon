"""Deep Agent - MVP 版本 (Vertex AI + LangChain)"""
import logging
# from typing import Dict, Any, Optional
# from pathlib import Path
# from langchain.messages import (
#     AIMessage,
#     AIMessageChunk,
#     HumanMessage,
#     SystemMessage,
# )
from deepagents import create_deep_agent
from agent.models import AnthropicModelProvider
# from simple_config import BaseAgentConfig, get_config
from agent.prompts import get_system_prompt
from deepagents.backends import FilesystemBackend
from agent.chunk_parser import ChunkParser

logger = logging.getLogger(__name__)


class RefactorAgent:
    def __init__(
        self,
        model=None,
        verbose: bool = True,
    ):
        """初始化 RefactorAgent

        Args:
            model: LLM 模型實例
            verbose: 是否顯示詳細的 chunk 解析資訊
        """
        self.model = model
        self.verbose = verbose
        self.root_dir = "/workspace/"  # 改為絕對路徑，確保容器內正確存取
        self._agent_init()

    def _agent_init(self):
        if not self.model:
            raise ValueError("model is not set")

        self.agent = create_deep_agent(
            model=self.model,
            memory=[
                f"{self.root_dir}/memory/AGENTS.md",
            ],
            tools=[],
            backend=FilesystemBackend(
                root_dir=self.root_dir,
                virtual_mode=True
            ),
            system_prompt=get_system_prompt("default")
        )

    def run(self, user_message: str = "檢視我的專案資料夾結構", event_callback=None):
        """執行 Agent 並使用 ChunkParser 解析串流輸出

        Args:
            user_message: 使用者訊息
            event_callback: 可選的回調函數，用於處理每個解析事件
                          函數簽名: callback(event_type: str, data: dict)
        """
        # 初始化 ChunkParser（傳入 callback）
        parser = ChunkParser(verbose=self.verbose, event_callback=event_callback)

        print(f"\n{'='*60}", flush=True)
        print(f"🚀 開始執行 Agent", flush=True)
        print(f"{'='*60}\n", flush=True)
        print(f"📝 User Message: {user_message}\n", flush=True)
        print(f"{'─'*60}", flush=True)
        print(f"💬 AI Response:\n", flush=True)

        # 串流執行
        result = self.agent.stream({
            "messages": [
                {"role": "user", "content": user_message}
            ]
        })

        # 使用 ChunkParser 解析每個 chunk
        for chunk in result:
            parser.parse(chunk)

        # 顯示總結
        parser.print_summary()


if __name__ == "__main__":
    # 初始化 LLM (根據環境變數 LLM_PROVIDER 自動選擇)
    provider = AnthropicModelProvider()
    model = provider.get_model()

    # 創建 Agent (verbose=True 會顯示詳細的 token usage, tool calls 等資訊)
    agent = RefactorAgent(model, verbose=True)
    message = """
    檢視我的資料夾結構，並整理一個將此專案重構成 typescript 的計畫，並將檔案寫入 ./memory/plan.md 檔案
    """
    # 執行 Agent
    agent.run(user_message=message)
