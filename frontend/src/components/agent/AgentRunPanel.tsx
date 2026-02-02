import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { startAgentRunAPI, getAgentRunsAPI } from '@/services/agent.service'
import type { AgentRunDetail } from '@/types/agent.types'
import { AgentRunStatusCard } from './AgentRunStatusCard'
import { AgentRunHistory } from './AgentRunHistory'

interface AgentRunPanelProps {
  projectId: string
  projectStatus: string
  onActiveRunChange?: (runId: string | null) => void
}

export function AgentRunPanel({ projectId, projectStatus, onActiveRunChange }: AgentRunPanelProps) {
  const [runs, setRuns] = useState<AgentRunDetail[]>([])
  const [activeRun, setActiveRun] = useState<AgentRunDetail | null>(null)
  const [loading, setLoading] = useState(false)

  // 載入 runs
  useEffect(() => {
    loadRuns()
  }, [projectId])

  // 輪詢活躍 run 狀態
  useEffect(() => {
    if (activeRun?.status === 'RUNNING') {
      const interval = setInterval(loadRuns, 3000)
      return () => clearInterval(interval)
    }
  }, [activeRun?.status])

  const loadRuns = async () => {
    try {
      const data = await getAgentRunsAPI(projectId)
      setRuns(data.runs)

      // 更新 activeRun
      const running = data.runs.find((r) => r.status === 'RUNNING')
      if (running) {
        setActiveRun(running)
        onActiveRunChange?.(running.id)
      } else if (activeRun?.status === 'RUNNING') {
        // 之前的 run 完成了，重新載入
        const updated = data.runs.find((r) => r.id === activeRun.id)
        setActiveRun(updated || null)
        onActiveRunChange?.(updated?.id || null)
      }
    } catch (error) {
      console.error('載入 Agent Runs 失敗', error)
    }
  }

  const handleStart = async () => {
    setLoading(true)
    try {
      await startAgentRunAPI(projectId)
      // 重新載入 runs 以取得完整的 AgentRunDetail
      await loadRuns()
    } catch (error: any) {
      alert(error.response?.data?.detail || '啟動失敗')
    } finally {
      setLoading(false)
    }
  }

  const canStart = projectStatus === 'READY' && !activeRun

  return (
    <Card>
      <CardHeader>
        <CardTitle>🤖 AI 自動分析</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {activeRun ? (
          <AgentRunStatusCard run={activeRun} projectId={projectId} />
        ) : (
          <Button onClick={handleStart} disabled={!canStart || loading} className="w-full">
            {loading ? '啟動中...' : '🚀 啟動 AI 分析'}
          </Button>
        )}

        {runs.length > 0 && <AgentRunHistory runs={runs} projectId={projectId} />}
      </CardContent>
    </Card>
  )
}
