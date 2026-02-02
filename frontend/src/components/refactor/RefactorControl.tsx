import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { startAgentRunAPI, getAgentRunsAPI, stopAgentRunAPI, resumeAgentRunAPI } from '@/services/agent.service'
import { reprovisionProjectAPI } from '@/services/project.service'
import { AgentLogStream } from '@/components/agent/AgentLogStream'
import type { AgentRunDetail } from '@/types/agent.types'
import { PlayCircle, StopCircle, RefreshCw, RotateCcw } from 'lucide-react'

interface RefactorControlProps {
  projectId: string
  projectStatus: string
  onProjectUpdate?: () => void
}

export function RefactorControl({ projectId, projectStatus, onProjectUpdate }: RefactorControlProps) {
  const [currentRun, setCurrentRun] = useState<AgentRunDetail | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [isResuming, setIsResuming] = useState(false)
  const [isReprovisioning, setIsReprovisioning] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const [loading, setLoading] = useState(false)

  // 載入當前執行的 run
  useEffect(() => {
    loadCurrentRun()
  }, [projectId])

  // 輪詢更新狀態
  useEffect(() => {
    if (currentRun?.status === 'RUNNING') {
      const interval = setInterval(loadCurrentRun, 5000)
      return () => clearInterval(interval)
    }
  }, [currentRun?.status])

  const loadCurrentRun = async () => {
    try {
      setLoading(true)
      const data = await getAgentRunsAPI(projectId)

      // 找到最新的 RUNNING run
      const runningRun = data.runs.find((r) => r.status === 'RUNNING')

      if (runningRun) {
        setCurrentRun(runningRun)
        if (!showLogs) {
          setShowLogs(true)
        }
      } else if (currentRun?.status === 'RUNNING') {
        // 之前的 run 已完成
        const updatedRun = data.runs.find((r) => r.id === currentRun.id)
        setCurrentRun(updatedRun || null)
      }
    } catch (error) {
      console.error('載入 Agent Run 失敗', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    setIsStarting(true)
    try {
      await startAgentRunAPI(projectId)
      await loadCurrentRun()
      setShowLogs(true)
      onProjectUpdate?.() // 通知父組件更新專案狀態
    } catch (error: any) {
      alert(error.response?.data?.detail || '啟動失敗')
    } finally {
      setIsStarting(false)
    }
  }

  const handleStop = async () => {
    if (!currentRun) return

    if (!confirm('確定要停止重構嗎？')) return

    setIsStopping(true)
    try {
      await stopAgentRunAPI(projectId, currentRun.id)
      await loadCurrentRun()
      setShowLogs(false)
      onProjectUpdate?.() // 通知父組件更新專案狀態
    } catch (error: any) {
      alert(error.response?.data?.detail || '停止失敗')
    } finally {
      setIsStopping(false)
    }
  }

  const handleResume = async () => {
    if (!currentRun) return

    setIsResuming(true)
    try {
      const result = await resumeAgentRunAPI(projectId, currentRun.id)
      // 更新為新的 run
      await loadCurrentRun()
      setShowLogs(true)
      onProjectUpdate?.() // 通知父組件更新專案狀態
      alert(`已建立新的重構任務：${result.run_id}`)
    } catch (error: any) {
      alert(error.response?.data?.detail || '繼續失敗')
    } finally {
      setIsResuming(false)
    }
  }

  const handleReprovision = async () => {
    if (!confirm('確定要重設專案嗎？這將刪除容器並重新建立，所有未保存的資料將遺失。')) return

    setIsReprovisioning(true)
    try {
      await reprovisionProjectAPI(projectId)
      setCurrentRun(null)
      setShowLogs(false)
      onProjectUpdate?.()
      alert('專案重設成功！容器正在重新建立中...')
    } catch (error: any) {
      alert(error.response?.data?.detail || '重設失敗')
    } finally {
      setIsReprovisioning(false)
    }
  }

  const isRunning = currentRun?.status === 'RUNNING'
  const canStart = projectStatus === 'READY' && !isRunning
  const isDone = currentRun?.status === 'DONE'
  const isFailed = currentRun?.status === 'FAILED'
  const isStopped = currentRun?.status === 'STOPPED'
  const canResume = isStopped || isFailed

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            🤖 AI 自動重構
            {isRunning && (
              <Badge variant="default" className="animate-pulse">
                執行中
              </Badge>
            )}
            {isDone && <Badge variant="success">已完成</Badge>}
            {isFailed && <Badge variant="destructive">失敗</Badge>}
            {isStopped && <Badge variant="secondary">已停止</Badge>}
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 控制按鈕 */}
        <div className="flex gap-3">
          {/* 開始重構 */}
          {canStart && (
            <Button
              onClick={handleStart}
              disabled={isStarting}
              className="flex-1"
              size="lg"
            >
              <PlayCircle className="w-5 h-5 mr-2" />
              {isStarting ? '啟動中...' : '開始重構'}
            </Button>
          )}

          {/* 停止重構 */}
          {isRunning && (
            <Button
              onClick={handleStop}
              variant="destructive"
              className="flex-1"
              size="lg"
              disabled={isStopping}
            >
              <StopCircle className="w-5 h-5 mr-2" />
              {isStopping ? '停止中...' : '停止重構'}
            </Button>
          )}

          {/* 繼續重構 */}
          {canResume && (
            <Button
              onClick={handleResume}
              variant="default"
              className="flex-1"
              size="lg"
              disabled={isResuming}
            >
              <PlayCircle className="w-5 h-5 mr-2" />
              {isResuming ? '啟動中...' : '繼續重構'}
            </Button>
          )}

          {/* 重新整理狀態 */}
          <Button
            onClick={loadCurrentRun}
            variant="ghost"
            size="lg"
            disabled={loading}
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* 重設專案按鈕（獨立一行） */}
        <div className="flex justify-end">
          <Button
            onClick={handleReprovision}
            variant="outline"
            size="sm"
            disabled={isReprovisioning || isRunning}
            className="border-orange-500 text-orange-600 hover:bg-orange-50"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            {isReprovisioning ? '重設中...' : '重設專案'}
          </Button>
        </div>

        {/* 狀態資訊 */}
        {currentRun && (
          <div className="bg-muted/50 rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Run ID:</span>
              <span className="font-mono">{currentRun.id}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">階段:</span>
              <span className="font-medium">{currentRun.phase}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">迭代:</span>
              <span>#{currentRun.iteration_index}</span>
            </div>
            {currentRun.created_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">開始時間:</span>
                <span>{new Date(currentRun.created_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        )}

        {/* 提示訊息 */}
        {!currentRun && (
          <div className="text-center py-8 text-muted-foreground">
            點擊「開始重構」啟動 AI 分析
          </div>
        )}

        {/* 完成狀態 */}
        {isDone && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <span className="text-2xl">✅</span>
              <div className="flex-1">
                <h4 className="font-semibold text-green-800">重構完成！</h4>
                <p className="text-sm text-green-700 mt-1">
                  分析結果已生成，可在下方查看完整日誌。
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 失敗狀態 */}
        {isFailed && currentRun?.error_message && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <span className="text-2xl">❌</span>
              <div className="flex-1">
                <h4 className="font-semibold text-red-800">執行失敗</h4>
                <p className="text-sm text-red-700 mt-1">{currentRun.error_message}</p>
              </div>
            </div>
          </div>
        )}

        {/* 停止狀態 */}
        {isStopped && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <span className="text-2xl">⏸️</span>
              <div className="flex-1">
                <h4 className="font-semibold text-yellow-800">重構已停止</h4>
                <p className="text-sm text-yellow-700 mt-1">
                  點擊「繼續重構」可以重新啟動分析任務。
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 日誌串流 */}
        {currentRun && showLogs && (
          <div className="mt-4">
            <AgentLogStream
              projectId={projectId}
              runId={currentRun.id}
              autoStart={true}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
