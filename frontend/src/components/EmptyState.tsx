import { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

/** A coloured square with an icon: marks what a section or an empty state is about. */
export function IconTile({ children, tone = 'cobalt', size = 'md' }: {
  children: ReactNode; tone?: 'cobalt' | 'marker' | 'ok' | 'obj' | 'bad' | 'ink'; size?: 'sm' | 'md' | 'lg'
}) {
  const tones = {
    cobalt: 'bg-cobalt text-white', marker: 'bg-marker text-ink', ok: 'bg-ok text-white', obj: 'bg-obj text-white',
    bad: 'bg-bad text-white', ink: 'bg-ink text-white',
  }
  const sizes = { sm: 'w-7 h-7 rounded-md', md: 'w-10 h-10 rounded-lg', lg: 'w-14 h-14 rounded-xl' }
  return (
    <span aria-hidden className={`${tones[tone]} ${sizes[size]} shrink-0 inline-flex items-center justify-center border-2 border-ink shadow-stamp-sm`}>
      {children}
    </span>
  )
}

/** A heading with its icon tile. */
export function SectionTitle({ icon, tone, children, hint, as: Tag = 'h2', right }: {
  icon: ReactNode; tone?: Parameters<typeof IconTile>[0]['tone']; children: ReactNode; hint?: ReactNode; as?: 'h1' | 'h2' | 'h3'; right?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <IconTile tone={tone} size="sm">{icon}</IconTile>
      <div className="min-w-0 flex-1">
        <Tag className="font-extrabold text-lg leading-tight">{children}</Tag>
        {hint && <p className="text-[13px] text-ink-muted mt-0.5">{hint}</p>}
      </div>
      {right}
    </div>
  )
}

/**
 * An empty place is a starting point, not a hole: a page of a notebook with an icon, what is (not yet) here, the
 * next step (optionally a few numbered steps of how things work) and the action that starts it.
 */
export default function EmptyState({ icon, tone = 'cobalt', title, text, steps, action, loading = false, compact = false }: {
  icon: ReactNode; tone?: Parameters<typeof IconTile>[0]['tone']; title: ReactNode; text?: ReactNode
  steps?: { icon: ReactNode; title: ReactNode; text?: ReactNode }[]; action?: ReactNode; loading?: boolean; compact?: boolean
}) {
  return (
    <div className={`notebook rounded-xl border-2 border-line ${compact ? 'pl-14 pr-5 py-6' : 'pl-14 pr-6 py-8'} text-left`}>
      <IconTile tone={tone} size={compact ? 'md' : 'lg'}>{loading ? <Loader2 size={22} className="animate-spin" /> : icon}</IconTile>
      <p className={`mt-3 font-extrabold ${compact ? 'text-[15px]' : 'text-lg'} leading-snug`}>{title}</p>
      {text && <p className="mt-1 text-[13.5px] text-ink-soft leading-[28px] max-w-md">{text}</p>}
      {steps && steps.length > 0 && (
        <ol className="mt-3 space-y-0">
          {steps.map((s, i) => (
            <li key={i} className="flex gap-3 min-h-[56px] items-start">
              <span className="mt-1 w-6 h-6 rounded-full bg-marker border-2 border-ink text-[12px] font-extrabold flex items-center justify-center shrink-0">{i + 1}</span>
              <span className="min-w-0">
                <span className="flex items-center gap-1.5 font-bold text-[14px] leading-[28px]">{s.icon} {s.title}</span>
                {s.text && <span className="block text-[13px] text-ink-muted leading-[28px] -mt-1">{s.text}</span>}
              </span>
            </li>
          ))}
        </ol>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
