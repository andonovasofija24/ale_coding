import { useEffect, useRef } from 'react'
import { AgentMessage } from '../types'
import { CheckCircle2, XCircle, Lightbulb, Route, Flag, AlertTriangle, CornerDownRight, Sparkles } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import Markdown from './Markdown'
import EmptyState from './EmptyState'

interface Props {
  messages: AgentMessage[]
  isLoading: boolean
}

const STYLES: Record<string, { bar: string; icon: JSX.Element; titleKey: string; tone: string }> = {
  pass: { bar: 'border-l-ok', icon: <CheckCircle2 size={15} className="text-ok" />, titleKey: 'chat.pass', tone: 'text-ok' },
  fail: { bar: 'border-l-bad', icon: <XCircle size={15} className="text-bad" />, titleKey: 'chat.fail', tone: 'text-bad' },
  hint: { bar: 'border-l-marker', icon: <Lightbulb size={15} className="text-marker-deep" />, titleKey: 'chat.hint', tone: 'text-marker-deep' },
  step: { bar: 'border-l-cobalt', icon: <Route size={15} className="text-cobalt" />, titleKey: 'chat.newStep', tone: 'text-cobalt' },
  done: { bar: 'border-l-ok', icon: <Flag size={15} className="text-ok" />, titleKey: 'chat.done', tone: 'text-ok' },
  error: { bar: 'border-l-bad', icon: <AlertTriangle size={15} className="text-bad" />, titleKey: 'chat.error', tone: 'text-bad' },
  note: { bar: 'border-l-ink-faint', icon: <Sparkles size={15} className="text-ink-muted" />, titleKey: 'chat.note', tone: 'text-ink-soft' },
}

/** Tutor feedback as a running log of notes, coloured by outcome. */
export default function AgentChat({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const { t } = useLanguage()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <EmptyState icon={<Lightbulb size={22} />} tone="marker" compact title={t('chat.emptyTitle')} text={t('chat.empty')} />
    )
  }

  return (
    <div className="flex flex-col gap-3 pb-2" aria-live="polite">
      {messages.map((msg, i) => {
        if (msg.role === 'user' || msg.kind === 'action') {
          return (
            <div key={i} className="flex items-center gap-1.5 text-xs text-ink-muted pt-1">
              <CornerDownRight size={13} />
              <span>{msg.content}</span>
              <span className="ml-auto tabular-nums text-ink-faint">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )
        }
        const st = STYLES[msg.kind ?? 'note'] ?? STYLES.note
        return (
          <article key={i} className={`bg-surface rounded-lg border border-line-soft border-l-[3px] ${st.bar} px-3.5 py-3`}>
            <header className={`flex items-center gap-1.5 text-[13px] font-bold ${st.tone}`}>
              {st.icon}
              {msg.title ?? t(st.titleKey as any)}
            </header>
            <div className="mt-1.5 note-md"><Markdown>{msg.content}</Markdown></div>
          </article>
        )
      })}

      {isLoading && (
        <div className="flex items-center gap-2 text-[13px] text-ink-muted px-1">
          <span className="flex gap-1">
            {[0, 150, 300].map((d) => (
              <span key={d} className="w-1.5 h-1.5 bg-ink-faint rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
            ))}
          </span>
          {t('chat.thinking')}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
