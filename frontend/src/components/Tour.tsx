import { createContext, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  BookOpen, ClipboardList, Code2, Compass, Eye, FileText, Flag, FlaskConical, GraduationCap, IdCard, KeyRound, Languages,
  Library, PanelsTopLeft, Play, Plus, Route, Settings2, Sparkles, TerminalSquare, User, Users, X,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { mainTour, markTourDone, tourDone, TOURS, TourStep } from '../lib/tours'

const ICONS: Record<string, typeof Compass> = {
  sparkles: Sparkles, cap: GraduationCap, key: KeyRound, library: Library, user: User, id: IdCard, languages: Languages,
  compass: Compass, flag: Flag, plus: Plus, book: BookOpen, settings: Settings2, file: FileText, eye: Eye, code: Code2,
  terminal: TerminalSquare, flask: FlaskConical, route: Route, play: Play, tabs: PanelsTopLeft, users: Users, clipboard: ClipboardList,
}

interface TourCtx {
  start: (id?: string) => void
  /** a page says which tour belongs to it (the "Водич" button plays it) and starts it the first time */
  setPageTour: (id: string | null, auto?: boolean) => void
  running: boolean
}
const Ctx = createContext<TourCtx>({ start: () => {}, setPageTour: () => {}, running: false })
export const useTour = () => useContext(Ctx)

/** In a page: this page has its own tour (started by itself the first time). */
export function usePageTour(id: string | null, ready = true) {
  const { setPageTour } = useTour()
  useEffect(() => {
    if (!ready) return
    setPageTour(id, true)
    return () => setPageTour(null)
  }, [id, ready]) // eslint-disable-line react-hooks/exhaustive-deps
}

type Rect = { top: number; left: number; width: number; height: number }

export function TourProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const [tour, setTour] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const pageTour = useRef<string | null>(null)

  const finish = useCallback(() => {
    if (tour && user) markTourDone(tour, user.id)
    setTour(null); setStep(0)
  }, [tour, user])

  const start = useCallback((id?: string) => {
    if (!user) return
    setTour(id ?? pageTour.current ?? mainTour(user.role)); setStep(0)
  }, [user])

  const setPageTour = useCallback((id: string | null, auto = false) => {
    pageTour.current = id
    if (auto && id && user && !tour && !window.location.pathname.startsWith('/lti') && !tourDone(id, user.id) && tourDone(mainTour(user.role), user.id)) {
      setTimeout(() => { setTour((cur) => cur ?? id); setStep(0) }, 900)
    }
  }, [user, tour])

  // the main tour of the role, the first time someone signs in (not over the courses.finki landing page)
  useEffect(() => {
    if (user && !tourDone(mainTour(user.role), user.id) && !pathname.startsWith('/lti')) {
      const id = setTimeout(() => setTour((cur) => cur ?? mainTour(user.role)), 700)
      return () => clearTimeout(id)
    }
  }, [user, pathname.startsWith('/lti')]) // eslint-disable-line react-hooks/exhaustive-deps

  const steps = tour ? TOURS[tour] ?? [] : []
  return (
    <Ctx.Provider value={{ start, setPageTour, running: !!tour }}>
      {children}
      {tour && steps[step] && (
        <TourStepView key={`${tour}-${step}`} step={steps[step]} n={step} total={steps.length}
          onBack={() => setStep((s) => Math.max(0, s - 1))}
          onNext={() => (step + 1 < steps.length ? setStep(step + 1) : finish())}
          onSkip={finish} />
      )}
    </Ctx.Provider>
  )
}

function TourStepView({ step, n, total, onBack, onNext, onSkip }: {
  step: TourStep; n: number; total: number; onBack: () => void; onNext: () => void; onSkip: () => void
}) {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const loc = useLocation()
  const [rect, setRect] = useState<Rect | null>(null)
  const [missing, setMissing] = useState(false)
  const card = useRef<HTMLDivElement>(null)
  const [cardH, setCardH] = useState(220)

  // go to the step's page, then find its element (it may appear a moment later)
  useEffect(() => {
    if (step.path && loc.pathname !== step.path) navigate(step.path)
  }, [step.path]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!step.target) { setRect(null); return }
    let tries = 0, scrolled = false
    const find = () => {
      const el = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`)
      if (!el || el.getBoundingClientRect().width === 0) {
        if (++tries > 25) setMissing(true)
        return
      }
      if (!scrolled) { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); scrolled = true }
      const r = el.getBoundingClientRect()
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
      setMissing(false)
    }
    find()
    const id = setInterval(find, 150)
    return () => clearInterval(id)
  }, [step.target, loc.pathname])
  // a step whose element isn't on this page (e.g. no "new course" button for this role) is skipped
  useEffect(() => { if (missing) onNext() }, [missing]) // eslint-disable-line react-hooks/exhaustive-deps
  useLayoutEffect(() => { if (card.current) setCardH(card.current.offsetHeight) })
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onSkip()
      if (e.key === 'ArrowRight' || e.key === 'Enter') onNext()
      if (e.key === 'ArrowLeft') onBack()
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onNext, onBack, onSkip])

  const Icon = ICONS[step.icon ?? 'compass'] ?? Compass
  const pad = 8, W = Math.min(360, window.innerWidth - 24)
  let pos: React.CSSProperties
  if (rect) {
    const gap = pad + 14
    const below = rect.top + rect.height + gap, above = rect.top - gap - cardH
    const clampTop = (y: number) => Math.min(Math.max(8, y), window.innerHeight - cardH - 8)
    const midLeft = Math.min(Math.max(12, rect.left + rect.width / 2 - W / 2), window.innerWidth - W - 12)
    if (below + cardH < window.innerHeight - 8) pos = { top: below, left: midLeft, width: W }
    else if (above >= 8) pos = { top: above, left: midLeft, width: W }
    // a tall element (the editor, a whole card): beside it if there is room, otherwise inside its lower corner
    else if (window.innerWidth - (rect.left + rect.width) - gap >= W + 12) pos = { top: clampTop(rect.top), left: rect.left + rect.width + gap, width: W }
    else if (rect.left - gap >= W + 12) pos = { top: clampTop(rect.top), left: rect.left - gap - W, width: W }
    else pos = { top: clampTop(Math.min(rect.top + rect.height, window.innerHeight) - cardH - 24), left: Math.min(rect.left + rect.width, window.innerWidth) - W - 24, width: W }
  } else {
    pos = { top: '50%', left: '50%', width: Math.min(440, window.innerWidth - 24), transform: 'translate(-50%, -50%)' }
  }
  const last = n + 1 === total
  return (
    <div className="fixed inset-0 z-[100]" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      {/* the dimmed page with a window around the element */}
      {rect ? (
        <div className="fixed rounded-xl border-[3px] border-[#FCC419] transition-all duration-300 pointer-events-none"
          style={{ top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2,
                   boxShadow: '0 0 0 9999px rgba(26,34,51,.58)' }} />
      ) : <div className="fixed inset-0 bg-ink/60" />}
      <div ref={card} className="fixed card-stamp p-5 transition-all duration-300" style={pos}>
        <div className="flex items-start gap-3">
          <span className="w-11 h-11 rounded-lg bg-[#FCC419] border-2 border-ink shadow-stamp-sm flex items-center justify-center shrink-0"><Icon size={21} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-bold text-ink-muted">{t('tour.stepOf', { n: n + 1, total })}</p>
            <h2 id="tour-title" className="font-extrabold text-[17px] leading-snug">{t(`tour.${step.key}.title` as any)}</h2>
          </div>
          <button onClick={onSkip} className="btn-ghost btn-sm px-1.5 -mr-1 -mt-1" aria-label={t('tour.skip')} title={t('tour.skip')}><X size={16} /></button>
        </div>
        <p className="mt-3 text-[14px] leading-relaxed text-ink-soft whitespace-pre-line">{t(`tour.${step.key}.body` as any)}</p>
        <div className="mt-4 flex items-center gap-2">
          <div className="flex gap-1 mr-auto" aria-hidden>
            {Array.from({ length: total }, (_, i) => <span key={i} className={`h-1.5 rounded-full ${i === n ? 'w-5 bg-ink' : i < n ? 'w-1.5 bg-ink/50' : 'w-1.5 bg-line-strong'}`} />)}
          </div>
          {n > 0 && <button className="btn-ghost btn-sm" onClick={onBack}>{t('tour.back')}</button>}
          {n === 0 && !last && <button className="btn-ghost btn-sm" onClick={onSkip}>{t('tour.skip')}</button>}
          <button className="btn-primary btn-sm" onClick={onNext} autoFocus>{last ? t('tour.finish') : t('tour.next')}</button>
        </div>
      </div>
    </div>
  )
}
