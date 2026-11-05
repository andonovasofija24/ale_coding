import { RunTestsResponse, SubmitResult } from '../types'

/** The last test run of a task in this tab, shared between the editor and the full tests page. */
export interface StoredRun {
  code: string
  results: RunTestsResponse | null
  submit: SubmitResult | null
  at: number
}

const key = (taskId: string) => `ale-tests:${taskId}`

export function saveRun(taskId: string, run: StoredRun) {
  try { sessionStorage.setItem(key(taskId), JSON.stringify(run)) } catch { /* storage unavailable */ }
}

export function loadRun(taskId: string): StoredRun | null {
  try {
    const v = sessionStorage.getItem(key(taskId))
    return v ? (JSON.parse(v) as StoredRun) : null
  } catch {
    return null
  }
}
