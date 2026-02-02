export enum AgentPhase {
  PLAN = 'plan',
  TEST = 'test',
  EXEC = 'exec',
}

export enum AgentRunStatus {
  RUNNING = 'RUNNING',
  DONE = 'DONE',
  FAILED = 'FAILED',
  STOPPED = 'STOPPED',
}

export interface AgentRun {
  run_id: string
  project_id: string
  status: AgentRunStatus
  iteration_index: number
  phase: AgentPhase
  created_at: string
  message: string
}

export interface AgentRunDetail {
  id: string
  project_id: string
  iteration_index: number
  phase: AgentPhase
  status: AgentRunStatus
  artifacts_path?: string
  plan_json_path?: string
  plan_md_path?: string
  created_at: string
  updated_at: string
  finished_at?: string
  error_message?: string
}

export interface AgentRunListResponse {
  total: number
  runs: AgentRunDetail[]
}

export interface AgentLogEvent {
  timestamp?: string
  type: 'llm_response' | 'ai_content' | 'tool_call' | 'tool_calls' | 'tool_result' | 'tools_execution' |
        'thinking' | 'log' | 'status' | 'token_usage' | 'response_metadata' | 'event' | 'message'
  message?: string
  event_type?: string
  content?: any
  results?: any[]
  tool_calls?: any[]
  metadata?: any
}
