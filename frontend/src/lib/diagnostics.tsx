import { MutableRefObject, useEffect, useRef, useState } from 'react'
import { AlertTriangle, CircleX, Loader2 } from 'lucide-react'
import { tasksApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'

export interface Diagnostic { line: number; column: number; severity: 'error' | 'warning'; message: string }
export interface DiagnosticsState { items: Diagnostic[]; checking: boolean; checked: boolean }

const OWNER = 'ale-compiler'
const DELAY = 1200 // ms after the last key press

/**
 * Compiler errors and warnings while typing, like an IDE: after the student stops typing for a moment the code is
 * compiled on the server (never run) and the problems are underlined in the editor. Old answers are ignored, and
 * nothing happens when the check is turned off (e.g. an exam) or the server skips it (busy).
 */
export function useDiagnostics(taskId: string | undefined, code: string, enabled: boolean,
  editor: MutableRefObject<any>, monaco: MutableRefObject<any>): DiagnosticsState {
  const [state, setState] = useState<DiagnosticsState>({ items: [], checking: false, checked: false })
  const seq = useRef(0)
  const lastChecked = useRef<string | null>(null)

  useEffect(() => {
    const model = editor.current?.getModel?.()
    if (!enabled || !taskId) {
      if (model && monaco.current) monaco.current.editor.setModelMarkers(model, OWNER, [])
      setState({ items: [], checking: false, checked: false })
      return
    }
    if (code === lastChecked.current) return
    const id = ++seq.current
    const timer = setTimeout(async () => {
      setState((s) => ({ ...s, checking: true }))
      try {
        const r: { diagnostics: Diagnostic[]; skipped: boolean } = await tasksApi.check(taskId, code)
        if (id !== seq.current) return // the code changed meanwhile
        if (r.skipped) { setState((s) => ({ ...s, checking: false })); return }
        lastChecked.current = code
        const m = editor.current?.getModel?.()
        if (m && monaco.current) {
          const M = monaco.current
          M.editor.setModelMarkers(m, OWNER, r.diagnostics.map((x) => {
            const d = { ...x, line: Math.min(Math.max(1, x.line), m.getLineCount()) }
            const lineLen = m.getLineMaxColumn(d.line)
            const col = Math.min(d.column, lineLen)
            // underline the word at the column (or the rest of the line when there is none)
            const word = m.getWordAtPosition({ lineNumber: d.line, column: col })
            return {
              startLineNumber: d.line, endLineNumber: d.line,
              startColumn: word ? word.startColumn : col, endColumn: word ? word.endColumn : Math.max(col + 1, lineLen),
              message: d.message, source: 'compiler',
              severity: d.severity === 'error' ? M.MarkerSeverity.Error : M.MarkerSeverity.Warning,
            }
          }))
        }
        setState({ items: r.diagnostics, checking: false, checked: true })
      } catch {
        if (id === seq.current) setState((s) => ({ ...s, checking: false }))
      }
    }, DELAY)
    return () => clearTimeout(timer)
  }, [code, enabled, taskId, editor, monaco])

  return state
}

/** "2 errors · 1 warning" above the editor; a click jumps to the first problem. */
export function DiagnosticsBadge({ d, editor }: { d: DiagnosticsState; editor: MutableRefObject<any> }) {
  const { t } = useLanguage()
  const errors = d.items.filter((x) => x.severity === 'error')
  const warnings = d.items.length - errors.length
  if (d.checking && !d.checked) return <span className="inline-flex items-center gap-1"><Loader2 size={12} className="animate-spin" /> {t('diag.checking')}</span>
  if (!d.checked) return null
  const jump = () => {
    const first = errors[0] ?? d.items[0]
    if (!first || !editor.current) return
    editor.current.revealLineInCenter(first.line)
    editor.current.setPosition({ lineNumber: first.line, column: first.column })
    editor.current.focus()
  }
  if (d.items.length === 0) {
    return <span className="text-ok font-semibold" title={t('diag.cleanHint')}>✓ {t('diag.clean')}</span>
  }
  return (
    <button onClick={jump} className="inline-flex items-center gap-2 font-semibold hover:underline" title={t('diag.jump')}>
      {errors.length > 0 && <span className="inline-flex items-center gap-1 text-bad"><CircleX size={13} /> {errors.length === 1 ? t('diag.errorOne') : t('diag.errors', { n: errors.length })}</span>}
      {warnings > 0 && <span className="inline-flex items-center gap-1 text-[#9A6700]"><AlertTriangle size={13} /> {warnings === 1 ? t('diag.warningOne') : t('diag.warnings', { n: warnings })}</span>}
      {d.checking && <Loader2 size={12} className="animate-spin text-ink-muted" />}
    </button>
  )
}
