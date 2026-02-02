import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getProjectAPI,
  provisionProjectAPI,
  stopProjectAPI,
  deleteProjectAPI,
  updateProjectAPI,
} from '@/services/project.service'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { Project } from '@/types/project.types'
import { RefactorControl } from '@/components/refactor/RefactorControl'

const statusColors: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning'> = {
  CREATED: 'secondary',
  PROVISIONING: 'warning',
  READY: 'success',
  RUNNING: 'default',
  STOPPED: 'secondary',
  FAILED: 'destructive',
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)

  // 編輯相關狀態
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    repo_url: '',
    branch: '',
    init_prompt: '',
  })
  const [urlWarning, setUrlWarning] = useState('')
  const [suggestedUrl, setSuggestedUrl] = useState('')

  useEffect(() => {
    if (id) {
      loadProject()
    }
  }, [id])

  const loadProject = async () => {
    try {
      const data = await getProjectAPI(id!)
      setProject(data)
    } catch (error) {
      console.error('載入專案失敗', error)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 驗證並修正 Git repository URL
   */
  const validateAndFixUrl = (url: string) => {
    setUrlWarning('')
    setSuggestedUrl('')

    if (!url) return

    // 檢測常見錯誤：GitHub 網頁 URL
    if (url.includes('/tree/') || url.includes('/blob/') || url.includes('?tab=')) {
      const match = url.match(/https?:\/\/github\.com\/([^\/]+)\/([^\/\?]+)/)
      if (match) {
        const [, owner, repo] = match
        const correctedUrl = `https://github.com/${owner}/${repo}.git`
        setUrlWarning('⚠️ 您輸入的是 GitHub 網頁 URL，而不是 Git repository URL')
        setSuggestedUrl(correctedUrl)
      }
    }
    // 檢測 GitHub URL 但缺少 .git
    else if (url.match(/^https?:\/\/github\.com\/[^\/]+\/[^\/]+$/) && !url.endsWith('.git')) {
      setUrlWarning('💡 建議在 GitHub URL 後加上 .git 後綴')
      setSuggestedUrl(`${url}.git`)
    }
  }

  const handleUrlChange = (value: string) => {
    setEditForm({ ...editForm, repo_url: value })
    validateAndFixUrl(value)
  }

  const handleUseSuggestedUrl = () => {
    if (suggestedUrl) {
      setEditForm({ ...editForm, repo_url: suggestedUrl })
      setUrlWarning('')
      setSuggestedUrl('')
    }
  }


  const handleProvision = async () => {
    try {
      setExecuting(true)
      await provisionProjectAPI(id!)
      await loadProject()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Provision 失敗')
    } finally {
      setExecuting(false)
    }
  }

  const handleStop = async () => {
    if (!confirm('確定要停止此專案嗎？')) return

    try {
      await stopProjectAPI(id!)
      await loadProject()
    } catch (error: any) {
      alert(error.response?.data?.detail || '停止專案失敗')
    }
  }

  const handleDelete = async () => {
    if (!confirm('確定要刪除此專案嗎？此操作無法復原！')) return

    try {
      await deleteProjectAPI(id!)
      window.location.href = '/projects'
    } catch (error: any) {
      alert(error.response?.data?.detail || '刪除專案失敗')
    }
  }

  const handleEdit = () => {
    if (project) {
      setEditForm({
        repo_url: project.repo_url,
        branch: project.branch,
        init_prompt: project.init_prompt,
      })
      setIsEditing(true)
    }
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
  }

  const handleSaveEdit = async () => {
    try {
      setExecuting(true)
      const updated = await updateProjectAPI(id!, editForm)
      setProject(updated)
      setIsEditing(false)
    } catch (error: any) {
      alert(error.response?.data?.detail || '更新專案失敗')
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">載入中...</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">專案不存在</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <Link to="/projects">
            <Button variant="ghost" size="sm">
              ← 返回專案列表
            </Button>
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto p-8">
        {/* 專案資訊 */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>
                  {project.repo_url.split('/').pop()?.replace('.git', '') || project.repo_url}
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">{project.repo_url}</p>
              </div>
              <Badge variant={statusColors[project.status]}>{project.status}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {!isEditing ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <strong className="text-sm">分支：</strong>
                    <span className="text-sm ml-2">{project.branch}</span>
                  </div>
                  <div>
                    <strong className="text-sm">容器 ID：</strong>
                    <span className="text-sm ml-2 font-mono">
                      {project.container_id || '尚未建立'}
                    </span>
                  </div>
                  <div className="md:col-span-2">
                    <strong className="text-sm">初始提示：</strong>
                    <p className="text-sm mt-1 text-gray-700">{project.init_prompt}</p>
                  </div>
                  {project.last_error && (
                    <div className="md:col-span-2">
                      <strong className="text-sm text-red-600">錯誤訊息：</strong>
                      <p className="text-sm mt-1 text-red-600 bg-red-50 p-2 rounded">
                        {project.last_error}
                      </p>
                    </div>
                  )}
                </div>

                {/* 操作按鈕 */}
                <div className="flex gap-2 flex-wrap">
                  {project.status === 'CREATED' && (
                    <Button onClick={handleProvision} disabled={executing}>
                      {executing ? 'Provisioning...' : 'Provision 專案'}
                    </Button>
                  )}
                  {project.status === 'READY' && (
                    <Button onClick={handleStop} variant="outline">
                      停止專案
                    </Button>
                  )}
                  <Button onClick={handleEdit} variant="outline" size="sm">
                    編輯專案
                  </Button>
                  <Button onClick={loadProject} variant="outline" size="sm">
                    重新整理
                  </Button>
                  <Button onClick={handleDelete} variant="destructive" size="sm">
                    刪除專案
                  </Button>
                </div>
              </>
            ) : (
              <>
                {/* 編輯表單 */}
                <div className="space-y-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Repository URL
                      {project.status !== 'CREATED' && (
                        <span className="text-xs text-gray-500 ml-2">
                          (已 Provision，無法修改)
                        </span>
                      )}
                    </label>
                    <Input
                      placeholder="https://github.com/user/repo.git"
                      value={editForm.repo_url}
                      onChange={(e) => handleUrlChange(e.target.value)}
                      disabled={project.status !== 'CREATED'}
                      className={urlWarning ? 'border-yellow-500' : ''}
                    />

                    {/* URL 警告和建議 */}
                    {urlWarning && project.status === 'CREATED' && (
                      <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                        <p className="text-yellow-800 mb-2">{urlWarning}</p>
                        {suggestedUrl && (
                          <div className="space-y-2">
                            <p className="font-mono text-xs text-yellow-900 bg-yellow-100 p-2 rounded">
                              建議使用：{suggestedUrl}
                            </p>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={handleUseSuggestedUrl}
                              className="text-yellow-700 border-yellow-300 hover:bg-yellow-100"
                            >
                              使用建議的 URL
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">分支</label>
                    <Input
                      placeholder="main"
                      value={editForm.branch}
                      onChange={(e) => setEditForm({ ...editForm, branch: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">初始提示</label>
                    <Textarea
                      placeholder="描述你想要 AI 執行的重構任務..."
                      value={editForm.init_prompt}
                      onChange={(e) => setEditForm({ ...editForm, init_prompt: e.target.value })}
                      rows={5}
                    />
                  </div>
                </div>

                {/* 編輯操作按鈕 */}
                <div className="flex gap-2">
                  <Button onClick={handleSaveEdit} disabled={executing}>
                    {executing ? '儲存中...' : '儲存'}
                  </Button>
                  <Button onClick={handleCancelEdit} variant="outline" disabled={executing}>
                    取消
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* AI 自動重構 */}
        {project.status === 'READY' && (
          <RefactorControl
            projectId={id!}
            projectStatus={project.status}
            onProjectUpdate={loadProject}
          />
        )}
      </div>
    </div>
  )
}
