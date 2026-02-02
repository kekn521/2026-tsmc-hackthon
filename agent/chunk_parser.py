"""ChunkParser - 解析並美化顯示 LangChain streaming chunks"""
import json
import re
from langchain.messages import AIMessage, AIMessageChunk


class ChunkParser:
    """解析並美化顯示 LangChain streaming chunks

    參考: https://docs.langchain.com/oss/python/langchain/messages#attributes

    主要功能:
    - 解析 AIMessageChunk 的各種屬性
    - 顯示 token usage (input_tokens, output_tokens)
    - 顯示 tool calls (name, args, id)
    - 格式化輸出讓中間過程清晰可見
    """

    def __init__(self, verbose: bool = True, event_callback=None):
        """初始化 ChunkParser

        Args:
            verbose: 是否顯示詳細資訊 (包含 metadata, tool calls 等)
            event_callback: 可選的回調函數，用於處理每個解析事件
                          函數簽名: callback(event_type: str, data: dict)
        """
        self.verbose = verbose
        self.event_callback = event_callback
        self.chunk_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def parse(self, chunk: dict) -> None:
        """解析並顯示單一 chunk

        Args:
            chunk: 從 agent.stream() 返回的 chunk 字典
        """
        self.chunk_count += 1

        # 檢查 chunk 結構
        if 'model' in chunk:
            self._parse_model_chunk(chunk['model'])
        elif 'tools' in chunk:
            self._parse_tools_chunk(chunk['tools'])
        elif self._is_middleware_chunk(chunk):
            # Middleware chunks (TodoListMiddleware, SummarizationMiddleware 等)
            self._parse_middleware_chunk(chunk)
        else:
            # 其他類型的 chunk (e.g., metadata, status)
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"[Chunk #{self.chunk_count}] 未知類型")
                print(f"{'='*60}")
                print(json.dumps(chunk, indent=2, ensure_ascii=False, default=str))

    def _parse_model_chunk(self, model_chunk: dict) -> None:
        """解析 model chunk (包含 AI 訊息)"""
        messages = model_chunk.get('messages', [])

        for msg in messages:
            # 處理 AIMessageChunk
            if isinstance(msg, (AIMessage, AIMessageChunk)):
                self._display_ai_message(msg)
            elif isinstance(msg, dict):
                # 有時候是字典格式
                self._display_message_dict(msg)

    def _display_ai_message(self, msg) -> None:
        """顯示 AIMessage/AIMessageChunk 的詳細資訊"""

        # 1. Content (文字內容)
        if hasattr(msg, 'content') and msg.content:
            content = msg.content
            content_text = ""

            if isinstance(content, str):
                content_text = content
                # 文字內容 - 直接串流輸出
                print(content, end="", flush=True)
            elif isinstance(content, list):
                # 多模態內容 (text, image, etc.)
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            text = block.get('text', '')
                            content_text += text
                            print(text, end="", flush=True)
                    else:
                        text = str(block)
                        content_text += text
                        print(text, end="", flush=True)

            # 發送 content 事件
            if content_text and self.event_callback:
                self.event_callback("ai_content", {"content": content_text})

        # 2. Tool Calls (工具調用)
        if hasattr(msg, 'tool_calls') and msg.tool_calls and self.verbose:
            print(f"\n\n{'─'*60}")
            print(f"🔧 [Tool Calls] 偵測到工具調用:")

            tool_calls_data = []
            for i, tool_call in enumerate(msg.tool_calls, 1):
                print(f"\n  #{i} {tool_call.get('name', 'unknown')}")
                print(f"      ID: {tool_call.get('id', 'N/A')}")
                print(f"      Args: {json.dumps(tool_call.get('args', {}), indent=8, ensure_ascii=False)}")

                tool_calls_data.append({
                    "name": tool_call.get('name', 'unknown'),
                    "id": tool_call.get('id', 'N/A'),
                    "args": tool_call.get('args', {})
                })

            print(f"{'─'*60}\n")

            # 發送 tool_calls 事件
            if self.event_callback:
                self.event_callback("tool_calls", {"tool_calls": tool_calls_data})

        # 3. Usage Metadata (Token 使用量)
        if hasattr(msg, 'usage_metadata') and msg.usage_metadata and self.verbose:
            usage = msg.usage_metadata
            if isinstance(usage, dict):
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)

                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens

                print(f"\n\n{'─'*60}")
                print(f"📊 [Token Usage]")
                print(f"  Input:  {input_tokens:,} tokens")
                print(f"  Output: {output_tokens:,} tokens")
                print(f"  Total:  {total_tokens:,} tokens")

                usage_data = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                }

                # 顯示額外細節 (如果有)
                if 'input_token_details' in usage:
                    details = usage['input_token_details']
                    print(f"  Input Details: cache_read={details.get('cache_read', 0)}, audio={details.get('audio', 0)}")
                    usage_data['input_token_details'] = details

                if 'output_token_details' in usage:
                    details = usage['output_token_details']
                    reasoning = details.get('reasoning', 0)
                    if reasoning > 0:
                        print(f"  Reasoning Tokens: {reasoning:,}")
                    usage_data['output_token_details'] = details

                print(f"{'─'*60}\n")

                # 發送 token_usage 事件
                if self.event_callback:
                    self.event_callback("token_usage", usage_data)

        # 4. Response Metadata (回應元資料)
        if hasattr(msg, 'response_metadata') and msg.response_metadata and self.verbose:
            metadata = msg.response_metadata
            if isinstance(metadata, dict) and metadata:
                print(f"\n{'─'*60}")
                print(f"ℹ️  [Response Metadata]")
                print(json.dumps(metadata, indent=2, ensure_ascii=False, default=str))
                print(f"{'─'*60}\n")

                # 發送 response_metadata 事件
                if self.event_callback:
                    self.event_callback("response_metadata", {"metadata": metadata})

    def _display_message_dict(self, msg_dict: dict) -> None:
        """顯示字典格式的訊息"""
        content = msg_dict.get('content', '')
        if content:
            print(content, end="", flush=True)

        if self.verbose and msg_dict.get('tool_calls'):
            print(f"\n\n🔧 [Tool Calls]: {len(msg_dict['tool_calls'])} calls")

    def _parse_tools_chunk(self, tools_chunk: dict) -> None:
        """解析 tools chunk (工具執行結果)"""
        messages = tools_chunk.get('messages', [])

        print(f"\n\n{'='*60}")
        print(f"🛠️  [Tools Execution] {len(messages)} result(s)")
        print(f"{'='*60}")

        tools_results = []

        for i, msg in enumerate(messages, 1):
            # 提取 name 和 content
            name = None
            content = None
            tool_call_id = None
            
            if hasattr(msg, 'name'):
                name = msg.name
            if hasattr(msg, 'content'):
                content = msg.content
            if hasattr(msg, 'tool_call_id'):
                tool_call_id = msg.tool_call_id
            
            # 如果是字串格式，嘗試解析
            if isinstance(msg, str):
                # 解析 "content='...' name='...' id='...' tool_call_id='...'" 格式
                name_match = re.search(r"name='([^']*)'", msg)
                content_match = re.search(r"content='(.*?)' name=", msg, re.DOTALL)
                tool_call_id_match = re.search(r"tool_call_id='([^']*)'", msg)
                
                if name_match:
                    name = name_match.group(1)
                if content_match:
                    content = content_match.group(1)
                    # 處理轉義字元
                    content = content.replace('\\n', '\n').replace('\\t', '\t')
                if tool_call_id_match:
                    tool_call_id = tool_call_id_match.group(1)
            
            # 顯示結果
            print(f"\n  #{i} 📄 {name or 'unknown'}")
            if tool_call_id:
                print(f"     ID: {tool_call_id[:20]}...")
            print(f"     {'─'*50}")
            if content:
                # 顯示內容（限制長度）
                content_preview = content[:500] if len(content) > 500 else content
                # 縮排每一行
                for line in content_preview.split('\n'):
                    print(f"     {line}")
                if len(content) > 500:
                    print(f"     ... (共 {len(content)} 字元)")
            print(f"     {'─'*50}")

            # 收集工具結果
            tools_results.append({
                "name": name or 'unknown',
                "tool_call_id": tool_call_id,
                "content": content[:500] if content and len(content) > 500 else content,
                "content_length": len(content) if content else 0
            })

        print(f"{'='*60}\n")

        # 發送 tools_execution 事件
        if self.event_callback:
            self.event_callback("tools_execution", {"results": tools_results})

    def _is_middleware_chunk(self, chunk: dict) -> bool:
        """檢查是否為 middleware chunk"""
        middleware_patterns = [
            'TodoListMiddleware',
            'SummarizationMiddleware',
            'MemoryMiddleware',
            'Middleware',
        ]
        for key in chunk.keys():
            for pattern in middleware_patterns:
                if pattern in key:
                    return True
        return False

    def _parse_middleware_chunk(self, chunk: dict) -> None:
        """解析 middleware chunk
        
        Middleware chunks 通常包含:
        - TodoListMiddleware.after_model
        - SummarizationMiddleware.before_model
        - 等等
        """
        for key, value in chunk.items():
            if value is None:
                # 空值的 middleware event，靜默跳過
                continue
            
            # 提取 middleware 名稱和事件類型
            if '.' in key:
                middleware_name, event_type = key.rsplit('.', 1)
            else:
                middleware_name, event_type = key, 'unknown'
            
            if self.verbose:
                print(f"\n{'─'*60}")
                print(f"⚙️  [{middleware_name}] {event_type}")
                print(f"{'─'*60}")
                if isinstance(value, dict):
                    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
                else:
                    print(str(value))
                print(f"{'─'*60}\n")

    def print_summary(self) -> None:
        """顯示總結資訊"""
        if self.verbose:
            print(f"\n\n{'='*60}")
            print(f"📈 [Session Summary]")
            print(f"{'='*60}")
            print(f"  Total Chunks: {self.chunk_count}")
            print(f"  Total Input Tokens: {self.total_input_tokens:,}")
            print(f"  Total Output Tokens: {self.total_output_tokens:,}")
            print(f"  Grand Total: {self.total_input_tokens + self.total_output_tokens:,} tokens")
            print(f"{'='*60}\n")
