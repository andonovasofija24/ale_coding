import { useEffect, useState } from 'react'
import { ChevronDown, Keyboard, Loader2, Play, TerminalSquare, X } from 'lucide-react'
import { sessionsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'

const key = (taskId: string) => `ale-stdin:${taskId}`
const PRE = 'font-mono text-[12.5px] leading-5 whitespace-pre-wrap break-words'

/** Languages whose programs can read keyboard input (not web pages, SQL or diagrams). */
export const canRunWithInput = (lang: string, web?: boolean, diagram?: unknown) =>
  !web && !diagram && lang !== 'sql' && lang !== 'postgresql'

/**
 * "Run with my input": what the program reads (cin / input() / Scanner…) is typed here, all at once; the program
 * is run once and its output is shown next to it. No tests — just trying the program out.
 */
export default function RunConsole({ taskId, code, functionTask, onClose }: {
  taskId: string; code: string; functionTask: boolean; onClose: () => void
}) {
  const { t, tError } = useLanguage()
  const [stdin, setStdin] = useState(() => { try { return localStorage.getItem(key(taskId)) ?? '' } catch { return '' } })
  const [res, setRes] = useState<{ output: string; error: string | null } | null>(null)
  const [running, setRunning] = useState(false)
  const [failed, setFailed] = useState('')
  useEffect(() => { try { localStorage.setItem(key(taskId), stdin) } catch { /* ignore */ } }, [taskId, stdin])

  const run = async () => {
    setRunning(true); setFailed('')
    try { setRes(await sessionsApi.freeRun(taskId, code, stdin)) } catch (err: any) {
      setFailed(tError(err.response?.data?.detail, 'run.failed'))
    } finally { setRunning(false) }
  }
  const noMain = res?.error && /COMPILE ERROR[\s\S]*(main|_start|entry point)/i.test(res.error)

  return (
    <div className="border-t-2 border-marker/70 bg-paper/50 shrink-0" role="region" aria-label={t('run.title')}>
      <div className="h-9 px-3 flex items-center gap-2 border-b border-line-soft">
        <TerminalSquare size={15} className="text-marker-deep" />
        <span className="text-[13px] font-bold whitespace-nowrap shrink-0">{t('run.title')}</span>
        <span className="text-[12px] text-ink-muted hidden md:inline truncate">{t('run.hint')}</span>
        <span className="flex-1" />
        <button className="btn-primary btn-sm h-7" onClick={run} disabled={running} title="Ctrl+Enter">
          {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} {t('run.run')}
        </button>
        <button className="btn-ghost btn-sm h-7 px-1.5" onClick={onClose} aria-label={t('run.close')} title={t('run.close')}><ChevronDown size={15} /></button>
      </div>
      <div className="grid sm:grid-cols-2 h-44">
        <label className="flex flex-col min-h-0 border-b sm:border-b-0 sm:border-r border-line-soft">
          <span className="px-3 pt-2 text-[11px] font-bold uppercase tracking-wide text-ink-muted flex items-center gap-1.5"><Keyboard size={12} /> {t('run.input')}</span>
          <textarea className={`flex-1 min-h-0 resize-none bg-transparent px-3 py-1.5 focus:outline-none ${PRE}`} value={stdin} spellCheck={false}
            placeholder={t('run.inputPh')} onChange={(e) => setStdin(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run() } }} />
        </label>
        <div className="flex flex-col min-h-0">
          <span className="px-3 pt-2 text-[11px] font-bold uppercase tracking-wide text-ink-muted flex items-center gap-2">
            {t('run.output')}
            {res && !running && (res.error ? <span className="normal-case tracking-normal text-bad">· {t('run.withError')}</span> : <span className="normal-case tracking-normal text-ok">· {t('run.ok')}</span>)}
            {res && <button className="ml-auto text-ink-faint hover:text-ink" onClick={() => setRes(null)} aria-label={t('run.clear')}><X size={12} /></button>}
          </span>
          <div className="flex-1 min-h-0 overflow-auto px-3 py-1.5" aria-live="polite">
            {failed ? <p role="alert" className="text-bad text-[13px]">{failed}</p>
              : !res ? <p className="text-[12.5px] text-ink-faint">{running ? t('run.running') : t('run.empty')}</p>
              : <>
                {(noMain || (functionTask && !res.output && (!res.error || res.error.startsWith('COMPILE')))) && (
                  <p className="mb-1.5 rounded-md bg-marker-soft px-2 py-1 text-[12px] text-ink-soft">{t('run.functionHint')}</p>
                )}
                {res.output && <pre className={PRE}>{res.output}</pre>}
                {!res.output && !res.error && <p className="text-[12.5px] text-ink-muted italic">{t('run.noOutput')}</p>}
                {res.error && <pre className={`${PRE} text-bad mt-1`}>{res.error}</pre>}
              </>}
          </div>
        </div>
      </div>
    </div>
  )
}
