export interface User {
  id: string
  email: string
  name: string
  role: 'student' | 'admin'
  created_at: string
}

export interface TestCase {
  id: string
  type: 'code_sample' | 'stdin_stdout'
  test_code: string
  stdin: string
  expected_output: string
  order: number
  is_hidden?: boolean
}

export interface Task {
  id: string
  title: string
  description: string
  starter_code: string
  language: string
  created_at: string
  test_cases: TestCase[]
  model_solution?: string
}

export interface TaskListItem {
  id: string
  title: string
  language: string
  created_at: string
}

export interface SessionStep {
  id: string
  step_number: number
  title: string
  description: string
  step_type: 'correctness' | 'optimization'
  status: 'pending' | 'active' | 'completed'
  agent_feedback: string
}

export interface Session {
  id: string
  task_id: string
  status: 'in_progress' | 'completed'
  current_step: number
  current_code: string
  steps: SessionStep[]
  created_at: string
  updated_at: string
}

export interface TestResult {
  test_number: number
  type: string
  test_code: string
  stdin: string
  expected_output: string
  actual_output: string
  passed: boolean
  error?: string
}

export interface RunTestsResponse {
  results: TestResult[]
  total: number
  passed: number
  failed: number
}

export interface CheckStepResponse {
  passed: boolean
  feedback: string
  step_completed: boolean
  all_steps_completed: boolean
}

export interface AgentMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}
