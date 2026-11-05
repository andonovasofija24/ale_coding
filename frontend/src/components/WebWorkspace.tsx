import { useEffect, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { FileCode2, Monitor, Paintbrush, RefreshCw, Smartphone, Braces } from 'lucide-react'
import { defineAleTheme, editorTheme } from './editorTheme'
import { useLanguage } from '../i18n/LanguageContext'
import { joinBundle, monacoLanguage, previewDocument, splitBundle, WebFile } from '../lib/web'

const EDITOR_OPTIONS = {
  fontSize: 14,
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  fontLigatures: true,
  lineHeight: 22,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  tabSize: 2,
  automaticLayout: true,
  padding: { top: 16, bottom: 16 },
  renderLineHighlight: 'all' as const,
  overviewRulerLanes: 0,
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
}

const icon = (name: string) =>
  name.endsWith('.css') ? <Paintbrush size={13} /> : name.endsWith('.js') ? <Braces size={13} /> : <FileCode2 size={13} />

/** HTML/CSS/JS editor: one tab per file; the files are kept together in `code` (see lib/web.ts). */
export function WebEditor({ code, onChange, readOnly = false, onMount, height }: {
  code: string; onChange?: (v: string) => void; readOnly?: boolean; onMount?: (editor: any, monaco: any) => void; height?: string
}) {
  const files = useMemo(() => splitBundle(code), [code])
  const [active, setActive] = useState('index.html')
  const current = files.find((f) => f.name === active) ?? files[0]

  const update = (content: string) => {
    if (!onChange) return
    const next: WebFile[] = files.map((f) => (f.name === current.name ? { ...f, content } : f))
    onChange(joinBundle(next))
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div role="tablist" className="flex items-end gap-0.5 px-2 pt-1.5 border-b border-line-soft bg-paper/50 shrink-0 overflow-x-auto">
        {files.map((f) => (
          <button key={f.name} role="tab" aria-selected={f.name === current.name} onClick={() => setActive(f.name)}
            className={`h-8 px-3 inline-flex items-center gap-1.5 font-mono text-[12.5px] rounded-t-md border border-b-0 -mb-px whitespace-nowrap ${
              f.name === current.name ? 'bg-surface border-line-soft text-ink font-semibold' : 'border-transparent text-ink-muted hover:text-ink'}`}>
            {icon(f.name)} {f.name}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0" style={height ? { height } : undefined}>
        <Editor
          path={`ale-web/${current.name}`}
          language={monacoLanguage(current.name)}
          value={current.content}
          onChange={(v) => update(v ?? '')}
          beforeMount={defineAleTheme}
          onMount={onMount}
          theme={editorTheme('web')}
          options={{ ...EDITOR_OPTIONS, readOnly }}
        />
      </div>
    </div>
  )
}

/** Live preview of the page in a sandboxed frame (scripts run, but the page can't reach the app or the network). */
export function WebPreview({ code, initialMode = 'fit', hint = true }: { code: string; initialMode?: 'fit' | 'phone' | 'desktop'; hint?: boolean }) {
  const { t } = useLanguage()
  const [doc, setDoc] = useState(() => previewDocument(splitBundle(code)))
  const [mode, setMode] = useState<'fit' | 'phone' | 'desktop'>(initialMode)
  const [nonce, setNonce] = useState(0)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // The page is laid out at a real screen width (1280 px or a 375 px phone) and scaled down to fit the panel,
  // so media queries work as on a real screen.
  const box = useRef<HTMLDivElement>(null)
  const [boxSize, setBoxSize] = useState({ w: 360, h: 480 })
  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(() => setBoxSize({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const target = mode === 'phone' ? 375 : mode === 'desktop' ? 1280 : boxSize.w
  const scale = Math.min(1, boxSize.w / target)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setDoc(previewDocument(splitBundle(code))), 500)
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [code])

  return (
    <div className="flex flex-col h-full min-h-[22rem]">
      <div className="flex items-center gap-1 pb-2">
        <div className="inline-flex rounded-md border border-line p-0.5" role="radiogroup" aria-label={t('web.size')}>
          {(['fit', 'phone', 'desktop'] as const).map((m) => (
            <button key={m} role="radio" aria-checked={mode === m} onClick={() => setMode(m)} title={t(`web.mode.${m}` as any)}
              className={`h-7 px-2 rounded inline-flex items-center gap-1 text-[12px] font-semibold ${mode === m ? 'bg-ink text-white' : 'text-ink-muted hover:text-ink'}`}>
              {m === 'phone' ? <><Smartphone size={13} /> 375</> : m === 'desktop' ? <><Monitor size={13} /> 1280</> : t('web.fit')}
            </button>
          ))}
        </div>
        <span className="flex-1" />
        <button className="btn-ghost btn-sm h-7 px-2" onClick={() => setNonce((n) => n + 1)} title={t('web.reload')} aria-label={t('web.reload')}><RefreshCw size={13} /></button>
      </div>
      <div ref={box} className="flex-1 rounded-lg border border-line bg-paper overflow-hidden relative">
        <iframe key={nonce} title={t('web.preview')} srcDoc={doc} sandbox="allow-scripts allow-modals allow-forms"
          className="bg-white border-0 absolute top-0 origin-top-left"
          style={{ width: target, height: boxSize.h / scale, transform: `scale(${scale})`,
                   left: Math.max(0, (boxSize.w - target * scale) / 2) }} />
      </div>
      {hint && <p className="mt-2 text-[11.5px] text-ink-muted">{t('web.previewHint')}</p>}
    </div>
  )
}

/** Staff looking at a handed-in web page: the page itself (rendered, clickable) or its code. */
export function WebSubmissionView({ code, children, height = '30rem' }: { code: string; children: React.ReactNode; height?: string }) {
  const { t } = useLanguage()
  const [view, setView] = useState<'page' | 'code'>('page')
  return (
    <div>
      <div className="mb-2 inline-flex rounded-lg border border-line bg-surface p-0.5" role="radiogroup" aria-label={t('web.viewAs')}>
        {(['page', 'code'] as const).map((v) => (
          <button key={v} role="radio" aria-checked={view === v} onClick={() => setView(v)}
            className={`h-8 px-3 rounded-md inline-flex items-center gap-1.5 text-[13px] font-semibold ${view === v ? 'bg-ink text-white' : 'text-ink-muted hover:text-ink'}`}>
            {v === 'page' ? <><Monitor size={14} /> {t('web.viewPage')}</> : <><FileCode2 size={14} /> {t('web.viewCode')}</>}
          </button>
        ))}
      </div>
      {view === 'page' ? <div className="card p-3" style={{ height }}><WebPreview code={code} initialMode="desktop" hint={false} /></div> : children}
    </div>
  )
}
