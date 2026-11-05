import { useState } from 'react'
import { Alternative, SessionStep } from '../types'
import { Check, Zap, Flag, HelpCircle, Lightbulb, GitBranch, Loader2, ChevronDown } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

interface Props {
  steps: SessionStep[]
  currentStep: number
  sessionCompleted: boolean
  /** several solutions of one task */
  solutionNo?: number
  approach?: string
  alternatives?: Alternative[]
  onAlternative?: (a: Alternative) => void
  startingAlternative?: string | null
}

/**
 * The adaptive steps drawn as a route: solid line + filled nodes for completed steps,
 * a marker-yellow node for the current one, and a dashed continuation for the step that
 * hasn't been decided yet (it is generated from the student's code after this one passes).
 */
export default function StepsPanel({ steps, sessionCompleted, solutionNo = 1, approach = '', alternatives = [], onAlternative, startingAlternative }: Props) {
  const { t } = useLanguage()
  const [open, setOpen] = useState<string | null>(null)
  const ordered = [...steps].sort((a, b) => a.step_number - b.step_number)
  const visible = ordered.filter((s) => s.status !== 'pending') // legacy sessions may still carry pending steps
  const doneCount = ordered.filter((s) => s.status === 'completed').length

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5">
        <h3 className="panel-title">{t('steps.routeTitle')}</h3>
        <span className="text-xs text-ink-muted">{t('steps.doneCount', { n: doneCount })}</span>
      </div>

      {approach && (
        <div className="mb-5 rounded-lg border-2 border-cobalt/25 bg-cobalt-soft/60 px-3 py-2.5 text-[13px]">
          <p className="font-bold text-cobalt flex items-center gap-1.5"><GitBranch size={14} /> {t('alt.solutionN', { n: solutionNo })}</p>
          <p className="mt-0.5 text-ink-soft">{approach}</p>
        </div>
      )}
      <ol className="relative">
        {visible.map((step, i) => {
          const isDone = step.status === 'completed'
          const isActive = step.status === 'active'
          const isLast = i === visible.length - 1
          const showConnector = !isLast || !sessionCompleted

          return (
            <li key={step.id} className="relative pl-10 pb-6">
              {/* connector to the next node */}
              {showConnector && (
                <span
                  aria-hidden
                  className={`absolute left-[13px] top-8 bottom-0 ${
                    isDone && !isLast ? 'w-0.5 bg-ink' : 'w-0 border-l-2 border-dashed border-ink-faint/60'
                  }`}
                />
              )}

              {/* node */}
              <span
                aria-hidden
                className={`absolute left-0 top-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  isDone
                    ? 'bg-ink text-white'
                    : isActive
                      ? 'bg-marker text-ink ring-4 ring-marker/30 animate-node-pop'
                      : 'bg-surface border-2 border-line text-ink-muted'
                }`}
              >
                {isDone ? <Check size={14} strokeWidth={3} /> : step.step_number + 1}
              </span>

              <div className="flex items-center gap-2 text-xs text-ink-muted">
                <span>{t('steps.step', { n: step.step_number + 1 })}</span>
                {step.step_type === 'optimization' && (
                  <span className="inline-flex items-center gap-0.5 font-semibold text-marker-deep">
                    <Zap size={11} /> {t('steps.optimize')}
                  </span>
                )}
                {isActive && <span className="font-semibold text-ink">{t('steps.current')}</span>}
              </div>

              {isActive ? (
                <div className="mt-1">
                  <p className="font-bold text-[15px] leading-snug text-ink">
                    <span className="marker">{step.title}</span>
                  </p>
                  {step.description && (
                    <p className="mt-2 text-sm leading-relaxed text-ink-soft">{step.description}</p>
                  )}
                  <Why step={step} />
                </div>
              ) : (
                <div className="mt-0.5">
                  <p className={`text-sm font-semibold leading-snug ${isDone ? 'text-ink-soft' : 'text-ink-muted'}`}>
                    {step.title}
                  </p>
                  {isDone && step.agent_feedback && (
                    <p className="mt-1 text-[13px] leading-relaxed text-ink-muted line-clamp-3">{step.agent_feedback}</p>
                  )}
                  {isDone && (step.why || step.tip) && (
                    <>
                      <button className="mt-1 text-[12px] font-semibold text-cobalt inline-flex items-center gap-1"
                        onClick={() => setOpen(open === step.id ? null : step.id)} aria-expanded={open === step.id}>
                        <ChevronDown size={12} className={open === step.id ? 'rotate-180' : ''} /> {t('steps.whyShow')}
                      </button>
                      {open === step.id && <Why step={step} />}
                    </>
                  )}
                </div>
              )}
            </li>
          )
        })}

        {/* What comes next */}
        {sessionCompleted ? (
          <li className="relative pl-10">
            <span className="absolute left-0 top-0 w-7 h-7 rounded-full bg-ok text-white flex items-center justify-center animate-node-pop">
              <Flag size={13} strokeWidth={2.5} />
            </span>
            <p className="font-bold text-ok">{t('steps.allDone')}</p>
            <p className="mt-1 text-sm text-ink-muted">{t('steps.allDoneHint')}</p>
            {alternatives.length > 0 ? (
              <div className="mt-4 rounded-xl border-2 border-marker/60 bg-marker-soft/50 p-3">
                <p className="font-bold text-[14px] flex items-center gap-1.5"><GitBranch size={15} className="text-marker-deep" /> {t('alt.title', { n: alternatives.length })}</p>
                <p className="mt-0.5 text-[12.5px] text-ink-soft">{t('alt.hint')}</p>
                <ul className="mt-2.5 space-y-2">
                  {alternatives.map((a) => (
                    <li key={a.title} className="rounded-lg bg-surface border border-line px-3 py-2">
                      <p className="font-semibold text-[13.5px]">{a.title}</p>
                      {a.idea && <p className="text-[12.5px] text-ink-muted mt-0.5">{a.idea}</p>}
                      {onAlternative && (
                        <button className="btn-secondary btn-sm mt-2" disabled={!!startingAlternative} onClick={() => onAlternative(a)}>
                          {startingAlternative === a.title ? <Loader2 size={13} className="animate-spin" /> : <GitBranch size={13} />} {t('alt.start')}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="mt-3 text-[12.5px] text-ink-muted">{solutionNo > 1 ? t('alt.noneMore') : t('alt.none')}</p>
            )}
          </li>
        ) : visible.length > 0 ? (
          <li className="relative pl-10">
            <span className="absolute left-[6px] top-1 w-3.5 h-3.5 rounded-full border-2 border-dashed border-ink-faint" />
            <p className="text-[13px] leading-relaxed text-ink-muted">{t('steps.nextHint')}</p>
          </li>
        ) : null}
      </ol>
    </div>
  )
}

/** "Why?" and "Did you know?" of a step. */
function Why({ step }: { step: SessionStep }) {
  const { t } = useLanguage()
  if (!step.why && !step.tip) return null
  return (
    <div className="mt-2.5 space-y-2">
      {step.why && (
        <div className="rounded-lg border-l-4 border-cobalt bg-cobalt-soft/60 px-3 py-2">
          <p className="text-[11px] font-bold uppercase tracking-wide text-cobalt flex items-center gap-1"><HelpCircle size={12} /> {t('steps.why')}</p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-ink">{step.why}</p>
        </div>
      )}
      {step.tip && (
        <div className="rounded-lg border-l-4 border-marker bg-marker-soft/60 px-3 py-2">
          <p className="text-[11px] font-bold uppercase tracking-wide text-marker-deep flex items-center gap-1"><Lightbulb size={12} /> {t('steps.tip')}</p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-ink">{step.tip}</p>
        </div>
      )}
    </div>
  )
}
