import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createProjectAPI } from '@/services/project.service'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'

export default function CreateProjectPage() {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [initPrompt, setInitPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [urlWarning, setUrlWarning] = useState('')
  const [suggestedUrl, setSuggestedUrl] = useState('')

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
    setRepoUrl(value)
    validateAndFixUrl(value)
  }

  const handleUseSuggestedUrl = () => {
    if (suggestedUrl) {
      setRepoUrl(suggestedUrl)
      setUrlWarning('')
      setSuggestedUrl('')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError('')
      const project = await createProjectAPI({
        repo_url: repoUrl,
        branch,
        init_prompt: initPrompt,
      })
      navigate(`/projects/${project.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '建立專案失敗')
      console.error('建立專案失敗', err)
    } finally {
      setLoading(false)
    }
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
      <div className="container mx-auto p-8 max-w-2xl">
        <h1 className="text-3xl font-bold mb-8">建立新專案</h1>

        <Card>
          <CardHeader>
            <CardTitle>專案資訊</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Repository URL *
                </label>
                <Input
                  placeholder="https://github.com/username/repo.git"
                  value={repoUrl}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  required
                  className={urlWarning ? 'border-yellow-500' : ''}
                />
                <p className="text-xs text-gray-500 mt-1">
                  支援 HTTPS 和 SSH 格式的 Git repository URL
                </p>

                {/* URL 警告和建議 */}
                {urlWarning && (
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

                {/* 範例說明 */}
                <div className="mt-2 text-xs text-gray-600">
                  <p className="font-medium mb-1">正確格式範例：</p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li className="font-mono">https://github.com/username/repo.git</li>
                    <li className="font-mono">git@github.com:username/repo.git</li>
                  </ul>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  分支 *
                </label>
                <Input
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  預設為 main 分支
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  初始提示 *
                </label>
                <Textarea
                  placeholder="描述你想要 AI 執行的重構任務..."
                  value={initPrompt}
                  onChange={(e) => setInitPrompt(e.target.value)}
                  rows={6}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  例如：「重構所有的 API 路由，使用 async/await 語法」
                </p>
              </div>

              {error && (
                <div className="text-sm text-red-500 bg-red-50 p-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex gap-3">
                <Button type="submit" className="flex-1" disabled={loading}>
                  {loading ? '建立中...' : '建立專案'}
                </Button>
                <Link to="/projects" className="flex-1">
                  <Button type="button" variant="outline" className="w-full">
                    取消
                  </Button>
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
