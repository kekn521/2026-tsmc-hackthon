import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Download, Clock, CheckCircle, XCircle } from 'lucide-react'
import type { AgentRunDetail, AgentPhase } from '@/types/agent.types'
import { downloadPlanMdAPI } from '@/services/agent.service'

interface AgentRunStatusCardProps {
  run: AgentRunDetail
  projectId: string
}

const phaseLabels: Record<AgentPhase, string> = {
  plan: '計劃生成',
  test: '測試驗證',
  exec: '執行重構',
}

export function AgentRunStatusCard({ run, projectId }: AgentRunStatusCardProps) {
  const isRunning = run.status === 'RUNNING'
  const isDone = run.status === 'DONE'
  const isFailed = run.status === 'FAILED'

  const handleDownload = () => {
    const url = downloadPlanMdAPI(projectId, run.id)
    window.open(url, '_blank')
  }

  return (
    <div className="space-y-3 p-4 border rounded-lg bg-muted/50">
      {/* 狀態標籤 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Clock className="w-4 h-4 animate-pulse text-blue-500" />}
          {isDone && <CheckCircle className="w-4 h-4 text-green-500" />}
          {isFailed && <XCircle className="w-4 h-4 text-red-500" />}

          <Badge variant={isRunning ? 'default' : isDone ? 'success' : 'destructive'}>
            {run.status}
          </Badge>
        </div>
        <span className="text-sm text-muted-foreground">
          迭代 #{run.iteration_index}
        </span>
      </div>

      {/* Phase 進度條 */}
      <div className="flex items-center gap-2">
        {(['plan', 'test', 'exec'] as AgentPhase[]).map((phase, index) => {
          const phases = ['plan', 'test', 'exec']
          const currentIndex = phases.indexOf(run.phase)
          const isActive = index <= currentIndex

          return (
            <div key={phase} className="flex items-center flex-1">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full border-2 text-xs font-semibold
                ${
                  isActive
                    ? 'bg-blue-500 border-blue-500 text-white'
                    : 'border-gray-300 text-gray-400'
                }`}
              >
                {isActive ? '●' : '○'}
              </div>
              {index < 2 && (
                <div className={`flex-1 h-0.5 ${isActive ? 'bg-blue-500' : 'bg-gray-300'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Phase 標籤 */}
      <div className="flex justify-between text-xs text-muted-foreground">
        {(['plan', 'test', 'exec'] as AgentPhase[]).map((phase) => (
          <span key={phase} className={run.phase === phase ? 'font-semibold text-blue-600' : ''}>
            {phaseLabels[phase]}
          </span>
        ))}
      </div>

      {/* 狀態訊息 */}
      <div className="text-sm text-muted-foreground">
        {isRunning && `AI 正在${phaseLabels[run.phase]}...`}
      </div>

      {/* 執行完成橫幅 */}
      {isDone && (
        <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <span className="text-2xl">✅</span>
            <div className="flex-1">
              <h4 className="font-semibold text-green-800">執行完成！</h4>
              <p className="text-sm text-green-700 mt-1">
                分析結果已生成，可下載查看重構計劃。
              </p>
              {run.artifacts_path && (
                <p className="text-xs text-green-600 mt-2 font-mono">
                  📁 Artifacts: {run.artifacts_path}
                </p>
              )}
              <Button onClick={handleDownload} variant="outline" size="sm" className="mt-3">
                <Download className="w-4 h-4 mr-2" />
                下載分析結果
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 執行失敗橫幅 */}
      {isFailed && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <span className="text-2xl">❌</span>
            <div className="flex-1">
              <h4 className="font-semibold text-red-800">執行失敗</h4>
              <p className="text-sm text-red-700 mt-1">{run.error_message}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
