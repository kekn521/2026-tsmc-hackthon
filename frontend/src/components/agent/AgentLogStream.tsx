import { useEffect, useState, useRef } from 'react'
import { streamAgentLogsAPI } from '@/services/agent.service'
import type { AgentLogEvent } from '@/types/agent.types'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface Props {
  projectId: string
  runId: string
  autoStart?: boolean
}

export function AgentLogStream({ projectId, runId, autoStart = true }: Props) {
  const [logs, setLogs] = useState<AgentLogEvent[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoScroll, setAutoScroll] = useState(false) // 預設不自動滾動，方便 debug
  const cancelStreamRef = useRef<(() => void) | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoStart) {
      startStream()
    }
    return () => {
      cancelStreamRef.current?.()
    }
  }, [runId, autoStart])

  useEffect(() => {
    // 只在啟用自動滾動時才滾動到底部
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const startStream = async () => {
    setIsStreaming(true)
    setError(null)
    setLogs([])

    try {
      const cancelFn = await streamAgentLogsAPI(
        projectId,
        runId,
        (event) => {
          setLogs((prev) => [...prev, event])
        },
        (err) => {
          setError(err.message)
          setIsStreaming(false)
        }
      )
      cancelStreamRef.current = cancelFn
    } catch (err: any) {
      setError(err.message)
      setIsStreaming(false)
    }
  }

  const stopStream = () => {
    cancelStreamRef.current?.()
    setIsStreaming(false)
  }

  return (
    <Card className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold">即時執行日誌</h3>
          <div className="flex items-center gap-2">
            {isStreaming ? (
              <>
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-sm text-green-600">串流中</span>
              </>
            ) : (
              <>
                <span className="inline-block w-2 h-2 bg-gray-400 rounded-full" />
                <span className="text-sm text-gray-600">未連線</span>
              </>
            )}
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            onClick={() => setAutoScroll(!autoScroll)}
            variant={autoScroll ? "default" : "outline"}
            size="sm"
            title={autoScroll ? "關閉自動滾動" : "啟用自動滾動"}
          >
            {autoScroll ? "📍 自動滾動" : "🔒 固定視窗"}
          </Button>
          {isStreaming ? (
            <Button onClick={stopStream} variant="destructive" size="sm">
              停止串流
            </Button>
          ) : (
            <Button onClick={startStream} variant="default" size="sm">
              開始串流
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded mb-3 text-sm">
          ⚠️ {error}
        </div>
      )}

      <div
        ref={logsContainerRef}
        className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm h-96 overflow-y-auto scroll-smooth"
        style={{ scrollBehavior: 'smooth' }}
      >
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            {isStreaming ? '等待日誌...' : '點擊「開始串流」查看日誌'}
          </div>
        ) : (
          logs.map((log, idx) => <LogLine key={idx} event={log} />)
        )}
        <div ref={logsEndRef} />
      </div>
    </Card>
  )
}

function LogLine({ event }: { event: AgentLogEvent }) {
  const { type, message, timestamp, content, results } = event

  let color = 'text-gray-300'
  let icon = '📝'
  let bgColor = ''
  let borderColor = ''

  switch (type) {
    case 'llm_response':
    case 'ai_content':
      color = 'text-green-400'
      bgColor = 'bg-green-950/20'
      borderColor = 'border-l-2 border-green-500'
      icon = '🤖'
      break
    case 'tool_call':
    case 'tool_calls':
      color = 'text-blue-400'
      bgColor = 'bg-blue-950/20'
      borderColor = 'border-l-2 border-blue-500'
      icon = '🔧'
      break
    case 'tool_result':
    case 'tools_execution':
      color = 'text-cyan-400'
      bgColor = 'bg-cyan-950/20'
      borderColor = 'border-l-2 border-cyan-500'
      icon = '✅'
      break
    case 'thinking':
      color = 'text-yellow-400'
      bgColor = 'bg-yellow-950/20'
      borderColor = 'border-l-2 border-yellow-500'
      icon = '💭'
      break
    case 'status':
      color = 'text-purple-400'
      bgColor = 'bg-purple-950/20'
      borderColor = 'border-l-2 border-purple-500'
      icon = '📊'
      break
    case 'log':
      color = 'text-gray-400'
      icon = '📄'
      break
    case 'token_usage':
      color = 'text-yellow-300'
      bgColor = 'bg-yellow-950/10'
      icon = '🔢'
      break
    case 'response_metadata':
      color = 'text-gray-500'
      icon = 'ℹ️'
      break
  }

  // 特殊處理 tool_calls, tools_execution, token_usage, response_metadata, todo_update
  if (type === 'tool_calls' || type === 'tool_call') {
    return <ToolCallsDisplay event={event} />
  }

  if (type === 'tools_execution' || type === 'tool_result') {
    return <ToolResultsDisplay event={event} />
  }

  if (type === 'token_usage') {
    return <TokenUsageDisplay event={event} />
  }

  if (type === 'response_metadata') {
    return <ResponseMetadataDisplay event={event} />
  }

  if (type === 'todo_update') {
    return <TodosDisplay event={event} />
  }

  // 智能格式化內容
  const displayContent = formatLogContent(message, content, results, type)

  return (
    <div className={`${bgColor} ${borderColor} mb-2 py-2 px-3 rounded hover:bg-opacity-100 transition-all duration-200 ease-in-out`}>
      <div className={`${color} flex items-start gap-2`}>
        <span className="flex-shrink-0 text-base mt-0.5">{icon}</span>
        <div className="flex-1 min-w-0 overflow-hidden">
          {timestamp && (
            <div className="text-xs text-gray-500 mb-1 font-sans">
              {new Date(timestamp).toLocaleTimeString('zh-TW')}
            </div>
          )}
          <div className="break-words whitespace-pre-wrap">{displayContent}</div>
        </div>
      </div>
    </div>
  )
}

/**
 * Tool Calls 專用顯示組件
 */
function ToolCallsDisplay({ event }: { event: AgentLogEvent }) {
  const { timestamp, content, tool_calls } = event

  // 提取 tool_calls 陣列
  const calls = tool_calls || content?.tool_calls || (Array.isArray(content) ? content : [])

  if (!calls || calls.length === 0) {
    return (
      <div className="bg-blue-950/20 border-l-2 border-blue-500 mb-2 py-2 px-3 rounded">
        <div className="text-blue-400 flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">🔧</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <span className="font-sans text-gray-400">工具調用（無詳細資訊）</span>
          </div>
        </div>
      </div>
    )
  }

  // 檢查是否有 write_todos 調用
  const writeTodosCall = calls.find((call: any) => {
    const toolName = call.name || call.function?.name || call.tool_name || ''
    return toolName === 'write_todos'
  })

  // 如果有 write_todos，顯示特別的 UI
  if (writeTodosCall) {
    return <WriteTodosCallDisplay event={event} call={writeTodosCall} allCalls={calls} />
  }

  return (
    <div className="bg-blue-950/20 border-l-2 border-blue-500 mb-2 py-2 px-3 rounded">
      <div className="text-blue-400">
        <div className="flex items-start gap-2 mb-2">
          <span className="flex-shrink-0 text-base mt-0.5">🔧</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans">工具調用 ({calls.length})</div>
          </div>
        </div>

        <div className="ml-7 space-y-2">
          {calls.map((call: any, idx: number) => {
            const toolName = call.name || call.function?.name || call.tool_name || '未知工具'
            const args = call.args || call.function?.arguments || call.arguments || {}

            return (
              <div key={idx} className="bg-blue-900/30 rounded p-2 font-sans text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-blue-300 font-mono font-semibold">{toolName}</span>
                  {call.id && (
                    <span className="text-xs text-gray-500 font-mono">[{call.id.slice(0, 8)}]</span>
                  )}
                </div>

                {Object.keys(args).length > 0 && (
                  <details className="cursor-pointer mt-1">
                    <summary className="text-gray-400 hover:text-gray-300 text-xs">
                      參數 ({Object.keys(args).length} 個)
                    </summary>
                    <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto border border-gray-700 text-gray-300">
                      {JSON.stringify(args, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/**
 * write_todos 專用顯示組件（調用時）
 */
function WriteTodosCallDisplay({ event, call, allCalls }: { event: AgentLogEvent; call: any; allCalls: any[] }) {
  const { timestamp } = event
  const args = call.args || call.function?.arguments || call.arguments || {}
  const todos = args.todos || []

  return (
    <div className="bg-purple-950/20 border-l-2 border-purple-500 mb-2 py-2 px-3 rounded">
      <div className="text-purple-400">
        <div className="flex items-start gap-2 mb-3">
          <span className="flex-shrink-0 text-base mt-0.5">📝</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans flex items-center gap-2">
              <span>正在寫入 TODO 列表</span>
              <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-pulse"></span>
            </div>
          </div>
        </div>

        {todos.length > 0 && (
          <div className="ml-7 space-y-2">
            <div className="text-xs text-purple-300 font-sans mb-2">
              準備寫入 {todos.length} 個任務
            </div>
            {todos.map((todo: any, idx: number) => {
              const task = todo.task || todo.title || todo.description || `任務 #${idx + 1}`
              const status = todo.status || 'pending'

              return (
                <div key={idx} className="bg-purple-900/30 rounded p-2 font-sans text-sm flex items-start gap-2">
                  <span className="text-purple-300 flex-shrink-0">•</span>
                  <div className="flex-1">
                    <div className="text-gray-200">{task}</div>
                    <div className="text-xs text-gray-500 mt-1">狀態: {status}</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* 顯示其他工具調用 */}
        {allCalls.length > 1 && (
          <details className="cursor-pointer mt-3 ml-7">
            <summary className="text-xs text-gray-500 hover:text-gray-400 font-sans">
              其他工具調用 ({allCalls.length - 1} 個)
            </summary>
            <div className="mt-2 space-y-1">
              {allCalls
                .filter((c: any) => {
                  const name = c.name || c.function?.name || c.tool_name || ''
                  return name !== 'write_todos'
                })
                .map((c: any, idx: number) => {
                  const name = c.name || c.function?.name || c.tool_name || '未知'
                  return (
                    <div key={idx} className="text-xs text-gray-400 font-mono">
                      • {name}
                    </div>
                  )
                })}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}

/**
 * Tool Results 專用顯示組件（執行結果）
 */
function ToolResultsDisplay({ event }: { event: AgentLogEvent }) {
  const { timestamp, content, results } = event

  // 提取 results 陣列
  const execResults = results || content?.results || (Array.isArray(content) ? content : [])

  if (!execResults || execResults.length === 0) {
    return (
      <div className="bg-cyan-950/20 border-l-2 border-cyan-500 mb-2 py-2 px-3 rounded">
        <div className="text-cyan-400 flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">✅</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <span className="font-sans text-gray-400">工具執行結果（無詳細資訊）</span>
          </div>
        </div>
      </div>
    )
  }

  // 檢查是否有 write_todos 的結果
  const writeTodosResult = execResults.find((result: any) => {
    const toolName = result.name || result.tool_name || ''
    return toolName === 'write_todos'
  })

  // 如果有 write_todos 結果，顯示特別的 UI
  if (writeTodosResult) {
    return <WriteTodosResultDisplay event={event} result={writeTodosResult} allResults={execResults} />
  }

  return (
    <div className="bg-cyan-950/20 border-l-2 border-cyan-500 mb-2 py-2 px-3 rounded">
      <div className="text-cyan-400">
        <div className="flex items-start gap-2 mb-2">
          <span className="flex-shrink-0 text-base mt-0.5">✅</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans">工具執行結果 ({execResults.length})</div>
          </div>
        </div>

        <div className="ml-7 space-y-3">
          {execResults.map((result: any, idx: number) => {
            const toolName = result.name || result.tool_name || '未知工具'
            const resultContent = result.content || result.output || result.result || ''
            const toolCallId = result.tool_call_id || result.id
            const contentLength = result.content_length

            return (
              <div key={idx} className="bg-cyan-900/30 rounded p-3 font-sans text-sm">
                {/* 工具名稱和 ID */}
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-cyan-300 font-mono font-semibold">{toolName}</span>
                  {toolCallId && (
                    <span className="text-xs text-gray-500 font-mono">[{toolCallId.slice(0, 12)}]</span>
                  )}
                  {contentLength && (
                    <span className="text-xs text-gray-500">({contentLength} 字元)</span>
                  )}
                </div>

                {/* 結果內容 */}
                {resultContent && (
                  <div className="bg-gray-900/50 rounded p-2 mt-2">
                    {typeof resultContent === 'string' ? (
                      resultContent.length > 500 ? (
                        <details className="cursor-pointer">
                          <summary className="text-gray-400 hover:text-gray-300 text-xs mb-2">
                            內容預覽（點擊展開完整內容）
                          </summary>
                          <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words">
                            {resultContent}
                          </pre>
                        </details>
                      ) : (
                        <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words">
                          {resultContent}
                        </pre>
                      )
                    ) : (
                      <pre className="text-xs text-gray-300 overflow-x-auto">
                        {JSON.stringify(resultContent, null, 2)}
                      </pre>
                    )}
                  </div>
                )}

                {/* 如果有其他欄位，提供查看選項 */}
                {Object.keys(result).length > 4 && (
                  <details className="cursor-pointer mt-2">
                    <summary className="text-xs text-gray-500 hover:text-gray-400">
                      查看完整數據
                    </summary>
                    <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto border border-gray-700 text-gray-300">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/**
 * write_todos 結果專用顯示組件
 */
function WriteTodosResultDisplay({ event, result, allResults }: { event: AgentLogEvent; result: any; allResults: any[] }) {
  const { timestamp } = event
  const resultContent = result.content || result.output || result.result || ''

  // 嘗試從結果中提取 todos
  let todos: any[] = []
  try {
    // 結果可能是 JSON 字串或純文字
    if (typeof resultContent === 'string') {
      // 嘗試解析 JSON
      if (resultContent.trim().startsWith('{') || resultContent.trim().startsWith('[')) {
        const parsed = JSON.parse(resultContent)
        todos = parsed.todos || (Array.isArray(parsed) ? parsed : [])
      }
    } else if (typeof resultContent === 'object') {
      todos = resultContent.todos || (Array.isArray(resultContent) ? resultContent : [])
    }
  } catch (e) {
    // 解析失敗，忽略
  }

  return (
    <div className="bg-purple-950/20 border-l-2 border-purple-500 mb-2 py-2 px-3 rounded">
      <div className="text-purple-400">
        <div className="flex items-start gap-2 mb-3">
          <span className="flex-shrink-0 text-base mt-0.5">✅</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans text-green-400">
              ✓ TODO 列表已成功寫入
            </div>
          </div>
        </div>

        {/* 顯示寫入的 TODOs */}
        {todos.length > 0 ? (
          <div className="ml-7 space-y-2">
            <div className="text-xs text-purple-300 font-sans mb-2">
              已寫入 {todos.length} 個任務
            </div>
            {todos.map((todo: any, idx: number) => {
              const task = todo.task || todo.title || todo.description || `任務 #${idx + 1}`
              const status = todo.status || 'pending'

              let statusIcon = '○'
              let statusColor = 'text-yellow-400'

              switch (status.toLowerCase()) {
                case 'completed':
                case 'done':
                  statusIcon = '✓'
                  statusColor = 'text-green-400'
                  break
                case 'in_progress':
                case 'running':
                  statusIcon = '▶'
                  statusColor = 'text-blue-400'
                  break
                case 'blocked':
                  statusIcon = '✖'
                  statusColor = 'text-red-400'
                  break
              }

              return (
                <div key={idx} className="bg-purple-900/30 rounded p-2 font-sans text-sm flex items-start gap-2">
                  <span className={`${statusColor} flex-shrink-0 font-bold`}>{statusIcon}</span>
                  <div className="flex-1">
                    <div className="text-gray-200">{task}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {status} {todo.priority && `• ${todo.priority} priority`}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          // 如果無法解析 todos，顯示原始內容
          <div className="ml-7">
            <div className="bg-purple-900/30 rounded p-3 font-sans text-sm">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words">
                {typeof resultContent === 'string' ? resultContent : JSON.stringify(resultContent, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* 顯示其他工具結果 */}
        {allResults.length > 1 && (
          <details className="cursor-pointer mt-3 ml-7">
            <summary className="text-xs text-gray-500 hover:text-gray-400 font-sans">
              其他工具結果 ({allResults.length - 1} 個)
            </summary>
            <div className="mt-2 space-y-1">
              {allResults
                .filter((r: any) => {
                  const name = r.name || r.tool_name || ''
                  return name !== 'write_todos'
                })
                .map((r: any, idx: number) => {
                  const name = r.name || r.tool_name || '未知'
                  return (
                    <div key={idx} className="text-xs text-gray-400 font-mono">
                      • {name}
                    </div>
                  )
                })}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}

/**
 * Token Usage 專用顯示組件
 */
function TokenUsageDisplay({ event }: { event: AgentLogEvent }) {
  const { timestamp, content } = event

  // Debug: 記錄收到的數據
  console.log('[TokenUsageDisplay] event:', event)
  console.log('[TokenUsageDisplay] content:', content)

  // 提取 token 使用資訊
  const usage = content?.usage || content

  // 如果完全沒有數據，顯示錯誤訊息
  if (!content) {
    return (
      <div className="bg-yellow-950/10 border-l-2 border-yellow-500 mb-2 py-2 px-3 rounded">
        <div className="text-yellow-300 flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">🔢</span>
          <div className="flex-1 font-sans text-sm">
            ⚠️ Token Usage 事件無內容數據
          </div>
        </div>
      </div>
    )
  }

  if (!usage || typeof usage !== 'object') {
    // 無法解析，顯示原始數據
    return <RawDataDisplay event={event} icon="🔢" color="text-yellow-300" bgColor="bg-yellow-950/10" borderColor="border-yellow-500" />
  }

  const inputTokens = usage.input_tokens || usage.prompt_tokens || 0
  const outputTokens = usage.output_tokens || usage.completion_tokens || 0
  const totalTokens = usage.total_tokens || inputTokens + outputTokens

  // 提取快取資訊（支援多種格式）
  const cacheRead = usage.cache_read_input_tokens || usage.input_token_details?.cache_read || 0
  const cacheCreation = usage.cache_creation_input_tokens || usage.input_token_details?.cache_creation || 0

  return (
    <div className="bg-yellow-950/10 border-l-2 border-yellow-500 mb-2 py-2 px-3 rounded">
      <div className="text-yellow-300">
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">🔢</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}

            <div className="font-semibold font-sans text-sm mb-2">Token 使用統計</div>

            <div className="flex items-center gap-4 font-sans text-sm flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">輸入:</span>
                <span className="font-mono font-semibold">{inputTokens.toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">輸出:</span>
                <span className="font-mono font-semibold">{outputTokens.toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">總計:</span>
                <span className="font-mono font-semibold text-yellow-200">{totalTokens.toLocaleString()}</span>
              </div>
            </div>

            {/* 顯示快取資訊 */}
            {(cacheRead > 0 || cacheCreation > 0) && (
              <div className="mt-2 pt-2 border-t border-yellow-900/30 space-y-1">
                {cacheRead > 0 && (
                  <div className="text-xs text-gray-400 font-sans flex items-center gap-2">
                    <span>💾 快取讀取:</span>
                    <span className="font-mono text-green-400">{cacheRead.toLocaleString()} tokens</span>
                  </div>
                )}
                {cacheCreation > 0 && (
                  <div className="text-xs text-gray-400 font-sans flex items-center gap-2">
                    <span>📝 快取建立:</span>
                    <span className="font-mono text-blue-400">{cacheCreation.toLocaleString()} tokens</span>
                  </div>
                )}
              </div>
            )}

            {/* 顯示完整資料的摺疊選項 */}
            <details className="cursor-pointer mt-2">
              <summary className="text-xs text-gray-500 hover:text-gray-400 font-sans">
                查看完整數據
              </summary>
              <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto border border-gray-700 text-gray-300">
                {JSON.stringify(content, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Response Metadata 專用顯示組件
 */
function ResponseMetadataDisplay({ event }: { event: AgentLogEvent }) {
  const { timestamp, content } = event

  // Debug: 記錄收到的數據
  console.log('[ResponseMetadataDisplay] event:', event)
  console.log('[ResponseMetadataDisplay] content:', content)

  // 如果完全沒有數據，顯示錯誤訊息
  if (!content) {
    return (
      <div className="bg-gray-900/20 border-l-2 border-gray-600 mb-2 py-2 px-3 rounded">
        <div className="text-gray-400 flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">ℹ️</span>
          <div className="flex-1 font-sans text-sm">
            ⚠️ Response Metadata 事件無內容數據
          </div>
        </div>
      </div>
    )
  }

  // 提取 metadata
  const metadata = content?.metadata || content

  if (!metadata || typeof metadata !== 'object') {
    // 無法解析，顯示原始數據
    return <RawDataDisplay event={event} icon="ℹ️" color="text-gray-500" bgColor="bg-gray-900/20" borderColor="border-gray-600" />
  }

  const modelName = metadata.model || metadata.model_name || '未知'
  const stopReason = metadata.stop_reason || '未知'
  const messageId = metadata.id || ''
  const provider = metadata.model_provider || ''

  return (
    <div className="bg-gray-900/20 border-l-2 border-gray-600 mb-2 py-2 px-3 rounded">
      <div className="text-gray-400">
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">ℹ️</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}

            <div className="font-semibold font-sans text-sm mb-2">回應元數據</div>

            <div className="space-y-1 text-xs font-sans">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">模型:</span>
                <span className="font-mono text-gray-300">{modelName}</span>
                {provider && <span className="text-gray-600">({provider})</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">停止原因:</span>
                <span className="font-mono text-gray-300">{stopReason}</span>
              </div>
              {messageId && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">訊息 ID:</span>
                  <span className="font-mono text-gray-500 text-[10px]">{messageId}</span>
                </div>
              )}
            </div>

            {/* 顯示完整資料的摺疊選項 */}
            <details className="cursor-pointer mt-2">
              <summary className="text-xs text-gray-500 hover:text-gray-400 font-sans">
                查看完整數據
              </summary>
              <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto border border-gray-700 text-gray-300">
                {JSON.stringify(content, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * TODOs 專用顯示組件
 */
function TodosDisplay({ event }: { event: AgentLogEvent }) {
  const { timestamp, content } = event

  // Debug: 記錄收到的數據
  console.log('[TodosDisplay] event:', event)
  console.log('[TodosDisplay] content:', content)

  // 如果完全沒有數據，顯示錯誤訊息
  if (!content) {
    return (
      <div className="bg-purple-950/20 border-l-2 border-purple-500 mb-2 py-2 px-3 rounded">
        <div className="text-purple-400 flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">📝</span>
          <div className="flex-1 font-sans text-sm">
            ⚠️ TODO 更新事件無內容數據
          </div>
        </div>
      </div>
    )
  }

  // 提取 todos 列表
  const todos = content?.todos || []

  if (!todos || todos.length === 0) {
    // 顯示原始數據
    return <RawDataDisplay event={event} icon="📝" color="text-purple-400" bgColor="bg-purple-950/20" borderColor="border-purple-500" />
  }

  return (
    <div className="bg-purple-950/20 border-l-2 border-purple-500 mb-2 py-2 px-3 rounded">
      <div className="text-purple-400">
        <div className="flex items-start gap-2 mb-3">
          <span className="flex-shrink-0 text-base mt-0.5">📝</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans">TODO 列表更新 ({todos.length})</div>
          </div>
        </div>

        <div className="ml-7 space-y-2">
          {todos.map((todo: any, idx: number) => {
            const task = todo.task || todo.title || todo.description || `任務 #${idx + 1}`
            const status = todo.status || 'pending'
            const priority = todo.priority
            const todoId = todo.id

            // 狀態樣式
            let statusColor = 'text-gray-400'
            let statusBg = 'bg-gray-800'
            let statusIcon = '○'

            switch (status.toLowerCase()) {
              case 'completed':
              case 'done':
                statusColor = 'text-green-400'
                statusBg = 'bg-green-900/30'
                statusIcon = '✓'
                break
              case 'in_progress':
              case 'running':
                statusColor = 'text-blue-400'
                statusBg = 'bg-blue-900/30'
                statusIcon = '▶'
                break
              case 'blocked':
                statusColor = 'text-red-400'
                statusBg = 'bg-red-900/30'
                statusIcon = '✖'
                break
              case 'pending':
              default:
                statusColor = 'text-yellow-400'
                statusBg = 'bg-yellow-900/30'
                statusIcon = '○'
                break
            }

            // 優先級樣式
            let priorityColor = 'text-gray-500'
            let priorityIcon = ''

            if (priority) {
              switch (priority.toLowerCase()) {
                case 'high':
                  priorityColor = 'text-red-400'
                  priorityIcon = '🔥'
                  break
                case 'medium':
                  priorityColor = 'text-orange-400'
                  priorityIcon = '⚡'
                  break
                case 'low':
                  priorityColor = 'text-blue-400'
                  priorityIcon = '💤'
                  break
              }
            }

            return (
              <div key={idx} className={`${statusBg} rounded p-3 font-sans text-sm transition-all duration-200 ease-in-out hover:bg-opacity-100 hover:scale-[1.01]`}>
                <div className="flex items-start gap-3">
                  {/* 狀態圖示 */}
                  <span className={`${statusColor} font-bold text-base flex-shrink-0 mt-0.5`}>
                    {statusIcon}
                  </span>

                  <div className="flex-1 min-w-0">
                    {/* 任務標題 */}
                    <div className="flex items-start gap-2 mb-1">
                      <span className="text-gray-200 font-medium break-words flex-1">{task}</span>
                      {priority && (
                        <span className={`${priorityColor} text-xs flex-shrink-0`}>
                          {priorityIcon} {priority.toUpperCase()}
                        </span>
                      )}
                    </div>

                    {/* 狀態和 ID */}
                    <div className="flex items-center gap-3 text-xs">
                      <span className={`${statusColor} font-mono`}>{status}</span>
                      {todoId && (
                        <span className="text-gray-600 font-mono">#{todoId.slice(0, 8)}</span>
                      )}
                    </div>

                    {/* 額外描述 */}
                    {todo.description && todo.description !== task && (
                      <div className="mt-2 text-xs text-gray-400 border-l-2 border-gray-700 pl-2">
                        {todo.description}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* 摘要統計 */}
        <div className="mt-3 ml-7 flex items-center gap-4 text-xs font-sans">
          <span className="text-gray-500">
            總計: <span className="text-purple-300 font-semibold">{todos.length}</span>
          </span>
          <span className="text-gray-500">
            完成: <span className="text-green-400 font-semibold">
              {todos.filter((t: any) => ['completed', 'done'].includes(t.status?.toLowerCase())).length}
            </span>
          </span>
          <span className="text-gray-500">
            進行中: <span className="text-blue-400 font-semibold">
              {todos.filter((t: any) => ['in_progress', 'running'].includes(t.status?.toLowerCase())).length}
            </span>
          </span>
        </div>

        {/* 查看完整數據 */}
        <details className="cursor-pointer mt-3 ml-7">
          <summary className="text-xs text-gray-500 hover:text-gray-400 font-sans">
            查看完整數據
          </summary>
          <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto border border-gray-700 text-gray-300">
            {JSON.stringify(content, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  )
}

/**
 * 原始數據顯示組件（fallback）
 */
function RawDataDisplay({
  event,
  icon,
  color,
  bgColor,
  borderColor
}: {
  event: AgentLogEvent
  icon: string
  color: string
  bgColor: string
  borderColor: string
}) {
  const { timestamp, content, type } = event

  return (
    <div className={`${bgColor} ${borderColor} border-l-2 mb-2 py-2 px-3 rounded`}>
      <div className={color}>
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 text-base mt-0.5">{icon}</span>
          <div className="flex-1">
            {timestamp && (
              <div className="text-xs text-gray-500 mb-1 font-sans">
                {new Date(timestamp).toLocaleTimeString('zh-TW')}
              </div>
            )}
            <div className="font-semibold font-sans text-sm mb-2">{type}</div>
            <pre className="text-xs bg-gray-800 p-2 rounded overflow-x-auto border border-gray-700 text-gray-300">
              {JSON.stringify(content, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * 智能格式化日誌內容 - 只在無法解析時才顯示 JSON
 */
function formatLogContent(
  message: string | undefined,
  content: any,
  results: any[] | undefined,
  _type: string
): React.ReactNode {
  // 優先使用 message
  if (message) {
    return <span className="font-sans">{message}</span>
  }

  // 處理結構化 content
  if (content !== undefined && content !== null) {
    // 字串直接顯示
    if (typeof content === 'string') {
      return <span className="font-sans">{content}</span>
    }

    // 數字或布林值
    if (typeof content === 'number' || typeof content === 'boolean') {
      return <span className="font-sans font-semibold">{String(content)}</span>
    }

    // 陣列處理
    if (Array.isArray(content)) {
      if (content.length === 0) {
        return <span className="text-gray-500 italic font-sans">（空陣列）</span>
      }
      if (content.length === 1 && typeof content[0] === 'string') {
        return <span className="font-sans">{content[0]}</span>
      }
      // 多個項目或複雜結構
      return (
        <div className="space-y-1 font-sans">
          {content.map((item, idx) => (
            <div key={idx} className="flex gap-2">
              <span className="text-gray-500 flex-shrink-0">[{idx}]</span>
              <span className="flex-1">{formatValue(item)}</span>
            </div>
          ))}
        </div>
      )
    }

    // 物件處理
    if (typeof content === 'object') {
      // 提取常見訊息欄位
      if (content.message) return <span className="font-sans">{content.message}</span>
      if (content.text) return <span className="font-sans">{content.text}</span>
      if (content.content && typeof content.content === 'string') {
        return <span className="font-sans">{content.content}</span>
      }
      if (content.output) return <span className="font-sans">{content.output}</span>

      // 簡單物件 (<=3 個鍵值) 格式化顯示
      const keys = Object.keys(content)
      if (keys.length === 0) {
        return <span className="text-gray-500 italic font-sans">（空物件）</span>
      }
      if (keys.length <= 3) {
        return (
          <div className="space-y-0.5 font-sans">
            {keys.map((key) => (
              <div key={key} className="flex gap-2">
                <span className="text-gray-400 flex-shrink-0">{key}:</span>
                <span className="flex-1 text-gray-200">{formatValue(content[key])}</span>
              </div>
            ))}
          </div>
        )
      }

      // 複雜物件 - 顯示摺疊的 JSON
      return (
        <details className="cursor-pointer">
          <summary className="text-gray-400 hover:text-gray-300 font-sans">
            展開查看詳細資料 ({keys.length} 個欄位)
          </summary>
          <pre className="text-xs bg-gray-800 p-2 rounded mt-2 overflow-x-auto border border-gray-700">
            {JSON.stringify(content, null, 2)}
          </pre>
        </details>
      )
    }
  }

  // 處理 results 陣列
  if (results && Array.isArray(results) && results.length > 0) {
    if (results.length === 1) {
      return <span className="font-sans">{formatValue(results[0])}</span>
    }
    return (
      <div className="space-y-1 font-sans">
        {results.map((result, idx) => (
          <div key={idx} className="flex gap-2">
            <span className="text-gray-500 flex-shrink-0">[{idx}]</span>
            <span className="flex-1">{formatValue(result)}</span>
          </div>
        ))}
      </div>
    )
  }

  // 完全無內容
  return <span className="text-gray-600 italic font-sans text-sm">（無內容）</span>
}

/**
 * 格式化單一值
 */
function formatValue(value: any): string {
  if (value === null) return '(null)'
  if (value === undefined) return '(undefined)'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)

  if (typeof value === 'object') {
    // 空物件或陣列
    if (Array.isArray(value) && value.length === 0) return '[]'
    if (Object.keys(value).length === 0) return '{}'

    // 簡單物件 - 轉為緊湊格式
    const keys = Object.keys(value)
    if (keys.length <= 2) {
      return keys.map((k) => `${k}=${JSON.stringify(value[k])}`).join(', ')
    }

    // 複雜物件 - 顯示類型
    return `{${keys.length} 個欄位}`
  }

  return String(value)
}
