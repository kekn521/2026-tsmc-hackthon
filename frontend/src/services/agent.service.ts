import { api } from './api'
import { getToken } from '@/utils/token'
import type { AgentRun, AgentRunDetail, AgentRunListResponse, AgentLogEvent } from '@/types/agent.types'

/**
 * 啟動 Agent Run
 */
export const startAgentRunAPI = async (projectId: string): Promise<AgentRun> => {
  const response = await api.post(`/api/v1/projects/${projectId}/agent/run`, {})
  return response.data
}

/**
 * 取得專案的所有 Agent Runs
 */
export const getAgentRunsAPI = async (projectId: string): Promise<AgentRunListResponse> => {
  const response = await api.get(`/api/v1/projects/${projectId}/agent/runs`)
  return response.data
}

/**
 * 取得單一 Agent Run 詳情
 */
export const getAgentRunDetailAPI = async (
  projectId: string,
  runId: string
): Promise<AgentRunDetail> => {
  const response = await api.get(`/api/v1/projects/${projectId}/agent/runs/${runId}`)
  return response.data
}

/**
 * 取得 plan.md 下載 URL
 */
export const downloadPlanMdAPI = (projectId: string, runId: string): string => {
  return `${import.meta.env.VITE_API_BASE_URL}/api/v1/projects/${projectId}/agent/runs/${runId}/artifacts/plan.md`
}

/**
 * 取得 plan.json 下載 URL
 */
export const downloadPlanJsonAPI = (projectId: string, runId: string): string => {
  return `${import.meta.env.VITE_API_BASE_URL}/api/v1/projects/${projectId}/agent/runs/${runId}/artifacts/plan.json`
}

/**
 * 停止 Agent Run
 */
export const stopAgentRunAPI = async (projectId: string, runId: string): Promise<any> => {
  const response = await api.post(`/api/v1/projects/${projectId}/agent/runs/${runId}/stop`)
  return response.data
}

/**
 * 繼續 Agent Run（會建立新的 run）
 */
export const resumeAgentRunAPI = async (projectId: string, runId: string): Promise<any> => {
  const response = await api.post(`/api/v1/projects/${projectId}/agent/runs/${runId}/resume`)
  return response.data
}

/**
 * 串流 Agent Run 日誌（SSE）
 * 使用 fetch + ReadableStream 以支援 Bearer token
 *
 * @param projectId 專案 ID
 * @param runId Agent Run ID
 * @param onMessage 收到事件時的回調函數
 * @param onError 錯誤處理回調函數
 * @returns 返回取消串流的函數
 */
export const streamAgentLogsAPI = async (
  projectId: string,
  runId: string,
  onMessage: (event: AgentLogEvent) => void,
  onError?: (error: Error) => void
): Promise<() => void> => {
  const token = getToken()
  if (!token) {
    throw new Error('未登入')
  }

  const url = `${import.meta.env.VITE_API_BASE_URL}/api/v1/projects/${projectId}/agent/runs/${runId}/stream`

  const abortController = new AbortController()

  fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = 'message' // SSE 預設事件類型
      let currentData = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        // 保留最後一行（可能不完整）
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmedLine = line.trim()

          // 跳過註釋
          if (trimmedLine.startsWith(':')) continue

          // 空行表示事件結束
          if (trimmedLine === '') {
            if (currentData) {
              try {
                const data = JSON.parse(currentData)
                onMessage({
                  type: currentEvent as any,
                  ...data
                })
              } catch (e) {
                console.warn('解析 SSE 資料失敗', e, currentData)
              }
              // 重置狀態
              currentEvent = 'message'
              currentData = ''
            }
            continue
          }

          // 解析 event: 行
          if (trimmedLine.startsWith('event:')) {
            currentEvent = trimmedLine.slice(6).trim()
          }
          // 解析 data: 行
          else if (trimmedLine.startsWith('data:')) {
            currentData = trimmedLine.slice(5).trim()
          }
        }
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        onError?.(error)
      }
    })

  // 返回取消函數
  return () => abortController.abort()
}
