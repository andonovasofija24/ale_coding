import { useRef, useState, DragEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload, FileCode2, Loader2, ChevronDown, AlertTriangle, EyeOff, Eye, Download, RotateCcw } from 'lucide-react'
import { adminApi, subjectsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { ImportPreview, ImportQuestion, SubjectSummary } from '../../types'
import SubjectIcon from '../../components/SubjectIcon'
import AppHeader from '../../components/AppHeader'
import Markdown from '../../components/Markdown'
import LangChip from '../../components/LangChip'

export default function AdminImportPage() {
  const { t, tError } = useLanguage()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const [fileName, setFileName] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [reading, setReading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [open, setOpen] = useState<Set<number>>(new Set())
  const { data: subj } = useQuery<{ subjects: SubjectSummary[] }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const subjects = subj?.subjects ?? []
  const [subjectId, setSubjectId] = useState('')   // where the imported tasks go (required)

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setError('')
    setPreview(null)
    setFileName(file.name)
    setReading(true)
    try {
      const p: ImportPreview = await adminApi.importPreview(file)
      setPreview(p)
      // Pre-select everything except tasks that already exist with the same title.
      setSelected(new Set(p.questions.filter((q) => !q.duplicate).map((q) => q.index)))
      setOpen(new Set())
      setSubjectId(p.suggested_subject_id ?? '')
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'import.readFailed'))
    } finally {
      setReading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  const toggle = (set: Set<number>, i: number) => {
    const next = new Set(set)
    next.has(i) ? next.delete(i) : next.add(i)
    return next
  }

  const doImport = async () => {
    if (!preview) return
    const tasks = preview.questions
      .filter((q) => selected.has(q.index))
      .map(({ title, description, starter_code, model_solution, language, test_cases }) => ({
        title, description, starter_code, model_solution, language, test_cases,
      }))
    setImporting(true)
    setError('')
    try {
      const res = await adminApi.importCommit(tasks, subjectId)
      qc.invalidateQueries({ queryKey: ['admin-tasks'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
      navigate('/admin/tasks', { state: { imported: res.created } })
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'import.commitFailed'))
    } finally {
      setImporting(false)
    }
  }

  const allSelected = !!preview && preview.questions.length > 0 && selected.size === preview.questions.length

  return (
    <div className="min-h-screen bg-paper pb-28">
      <AppHeader showAdminLink={false}>
        <nav className="hidden sm:flex items-center gap-2 text-sm text-ink-muted ml-2 min-w-0">
          <Link to="/admin/tasks" className="hover:text-ink">{t('admin.manageTasks')}</Link>
          <span>/</span>
          <span className="font-semibold text-ink truncate">{t('import.title')}</span>
        </nav>
      </AppHeader>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('import.title')}</h1>
        <p className="mt-2 text-ink-muted max-w-xl">{t('import.intro')}</p>

        {/* Step 1 — choose file */}
        {!preview && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`mt-8 rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
              dragOver ? 'border-cobalt bg-cobalt-soft' : 'border-line bg-surface'
            }`}
          >
            {reading ? (
              <>
                <Loader2 size={28} className="mx-auto animate-spin text-cobalt" />
                <p className="mt-3 font-semibold">{t('import.reading', { name: fileName })}</p>
              </>
            ) : (
              <>
                <div className="mx-auto w-12 h-12 rounded-full bg-paper flex items-center justify-center">
                  <Upload size={22} className="text-ink-soft" />
                </div>
                <p className="mt-4 font-semibold">{t('import.drop')}</p>
                <p className="mt-1 text-sm text-ink-muted">{t('import.dropHint')}</p>
                <button onClick={() => inputRef.current?.click()} className="btn-primary mt-5">
                  <FileCode2 size={15} /> {t('import.choose')}
                </button>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".xml,text/xml,application/xml"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>
        )}

        {!preview && !reading && (
          <div className="mt-6 card px-5 py-4 text-sm text-ink-soft leading-relaxed">
            <p className="font-semibold text-ink flex items-center gap-1.5"><Download size={15} /> {t('import.howTitle')}</p>
            <ol className="mt-2 list-decimal pl-5 space-y-1">
              <li>{t('import.how1')}</li>
              <li>{t('import.how2')}</li>
              <li>{t('import.how3')}</li>
            </ol>
            <p className="mt-3 text-ink-muted">{t('import.supported')}</p>
          </div>
        )}

        {error && <p role="alert" className="mt-4 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}

        {/* Step 2 — review & select */}
        {preview && (
          <section className="mt-8">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-ink-soft">
                <span className="font-semibold text-ink">{fileName}</span>
                {' — '}
                {t('import.summary', { found: preview.questions.length, skipped: preview.skipped.length })}
              </p>
              <button onClick={() => { setPreview(null); setFileName('') }} className="btn-ghost btn-sm ml-auto">
                <RotateCcw size={14} /> {t('import.otherFile')}
              </button>
            </div>

            {preview.questions.length > 0 && (
              <div className="mt-4 card p-4 sm:p-5 flex flex-wrap items-center gap-3" style={{ borderLeft: `4px solid ${subjects.find((s) => s.id === subjectId)?.color ?? '#E03131'}` }}>
                {(() => { const s = subjects.find((x) => x.id === subjectId); return s ? <SubjectIcon icon={s.icon} color={s.color} size={36} /> : null })()}
                <div className="flex-1 min-w-[14rem]">
                  <label htmlFor="imp-subj" className="font-bold block">{t('import.subject')}</label>
                  <p className="text-[13px] text-ink-muted">{preview.suggested_subject_id && subjectId === preview.suggested_subject_id ? t('import.subjectSuggested') : t('import.subjectHint')}</p>
                </div>
                <select id="imp-subj" className="input w-full sm:w-80" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required>
                  <option value="">{t('import.subjectChoose')}</option>
                  {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}{s.semester ? ` · ${t('subj.semShort', { n: s.semester })}` : ''}</option>)}
                </select>
              </div>
            )}

            {preview.questions.length > 0 && (
              <div className="mt-4 card overflow-hidden">
                <label className="flex items-center gap-3 px-4 py-3 border-b border-line-soft bg-paper/50 text-sm font-semibold cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 accent-cobalt"
                    checked={allSelected}
                    onChange={() => setSelected(allSelected ? new Set() : new Set(preview.questions.map((q) => q.index)))}
                  />
                  {t('import.selectAll')}
                </label>
                <ul className="divide-y divide-line-soft">
                  {preview.questions.map((q) => (
                    <QuestionRow
                      key={q.index}
                      q={q}
                      checked={selected.has(q.index)}
                      expanded={open.has(q.index)}
                      onCheck={() => setSelected((s) => toggle(s, q.index))}
                      onExpand={() => setOpen((s) => toggle(s, q.index))}
                    />
                  ))}
                </ul>
              </div>
            )}

            {preview.skipped.length > 0 && (
              <details className="mt-6 card px-4 py-3 text-sm">
                <summary className="cursor-pointer font-semibold">{t('import.skippedTitle', { n: preview.skipped.length })}</summary>
                <ul className="mt-3 space-y-1.5">
                  {preview.skipped.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="font-medium text-ink truncate">{s.title}</span>
                      <span className="text-ink-muted">— {t(`import.skip.${s.reason}` as any, { detail: s.detail })}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
        )}
      </main>

      {/* Step 3 — confirm */}
      {preview && preview.questions.length > 0 && (
        <div className="fixed bottom-0 inset-x-0 bg-surface/95 backdrop-blur border-t border-line">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center gap-3">
            <p className="text-sm text-ink-soft">{t('import.selected', { n: selected.size, total: preview.questions.length })}</p>
            <Link to="/admin/tasks" className="btn-ghost ml-auto">{t('form.cancel')}</Link>
            {!subjectId && <span className="text-[13px] font-semibold text-bad">{t('import.subjectMissing')}</span>}
            <button onClick={doImport} disabled={importing || selected.size === 0 || !subjectId} className="btn-primary">
              {importing ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
              {t('import.importN', { n: selected.size })}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function QuestionRow({ q, checked, expanded, onCheck, onExpand }: {
  q: ImportQuestion; checked: boolean; expanded: boolean; onCheck: () => void; onExpand: () => void
}) {
  const { t } = useLanguage()
  const visible = q.test_cases.filter((tc) => !tc.is_hidden).length
  const hidden = q.test_cases.length - visible
  const isProgram = q.test_cases.every((tc) => tc.type === 'stdin_stdout')
  const warnings = [...(q.duplicate ? ['duplicate'] : []), ...q.warnings]

  return (
    <li className={checked ? '' : 'bg-paper/40'}>
      <div className="flex items-start gap-3 px-4 py-3.5">
        <input type="checkbox" checked={checked} onChange={onCheck} className="mt-1 w-4 h-4 accent-cobalt shrink-0" aria-label={q.title} />
        <button onClick={onExpand} className="min-w-0 flex-1 text-left" aria-expanded={expanded}>
          <span className="flex items-center gap-2">
            <span className={`font-semibold truncate ${checked ? 'text-ink' : 'text-ink-muted'}`}>{q.title}</span>
            <ChevronDown size={15} className={`shrink-0 text-ink-faint transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </span>
          <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <LangChip lang={q.language} />
            <span className="font-semibold text-ink-soft">{isProgram ? t('import.typeProgram') : t('import.typeFunction')}</span>
            <span className="inline-flex items-center gap-1"><Eye size={12} /> {t('import.visibleN', { n: visible })}</span>
            <span className="inline-flex items-center gap-1"><EyeOff size={12} /> {t('import.hiddenN', { n: hidden })}</span>
          </span>
          {warnings.length > 0 && (
            <span className="mt-2 flex flex-wrap gap-1.5">
              {warnings.map((w) => (
                <span
                  key={w}
                  className={`inline-flex items-center gap-1 text-[11.5px] font-semibold rounded-full px-2 py-0.5 ${
                    w === 'duplicate' ? 'bg-bad-soft text-bad' : 'bg-marker-soft text-marker-deep'
                  }`}
                >
                  <AlertTriangle size={11} /> {t(`import.warn.${w}` as any)}
                </span>
              ))}
            </span>
          )}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-5 pl-11 space-y-4">
          <div className="rounded-lg border border-line-soft bg-surface px-4 py-3 task-description">
            {q.description ? <Markdown>{q.description}</Markdown> : <p className="text-ink-faint">—</p>}
          </div>
          {q.starter_code && (
            <div>
              <p className="panel-title mb-1.5">{t('form.starterCode')}</p>
              <pre className="code-block">{q.starter_code}</pre>
            </div>
          )}
          <div>
            <p className="panel-title mb-1.5">{t('form.testCases')}</p>
            <ul className="space-y-2">
              {q.test_cases.map((tc, i) => (
                <li key={i} className="grid sm:grid-cols-[minmax(0,1fr)_10rem] gap-2 text-xs">
                  <div>
                    <p className="text-ink-muted mb-1 flex items-center gap-1">
                      {t('form.test', { n: i + 1 })}
                      {tc.is_hidden && <span className="inline-flex items-center gap-0.5 font-semibold"><EyeOff size={11} /> {t('form.hidden')}</span>}
                    </p>
                    <pre className="code-block">{tc.type === 'code_sample' ? tc.test_code : tc.stdin}</pre>
                  </div>
                  <div>
                    <p className="text-ink-muted mb-1">{t('form.expectedOutput')}</p>
                    <pre className="code-block text-ok">{tc.expected_output}</pre>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </li>
  )
}
