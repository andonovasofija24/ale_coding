import { ReactNode } from 'react'
import Avatar from './Avatar'

/**
 * The person's "пропусница" to the lab: a dark card with an engraved pattern, a chip in the marker colour and the
 * name and role, like a faculty access card. Shown on the home page (filled in) and on the sign-in page (blank).
 */
export default function AccessCard({ name, role, serial, avatarUrl, lines = [], blank = false, className = '' }: {
  name: string; role: string; serial: string; avatarUrl?: string | null; lines?: ReactNode[]; blank?: boolean; className?: string
}) {
  return (
    <div className={`relative isolate overflow-hidden rounded-[22px] bg-ink text-white p-6 sm:p-7 shadow-[0_24px_48px_-24px_rgba(26,34,51,.7)] ${className}`}
      style={{ aspectRatio: '1.586 / 1' }} role="img" aria-label={`ALE · ${name} · ${role}`}>
      {/* engraving: fine diagonal lines and a soft arc, like the background of a printed card */}
      <span aria-hidden className="absolute inset-0 -z-10 opacity-[.09]"
        style={{ backgroundImage: 'repeating-linear-gradient(135deg, #fff 0 1px, transparent 1px 9px)' }} />
      <span aria-hidden className="absolute -right-24 -bottom-32 w-80 h-80 -z-10 rounded-full border-[28px] border-white/[.05]" />
      <span aria-hidden className="absolute -right-10 -bottom-16 w-48 h-48 -z-10 rounded-full border border-white/[.12]" />

      <div className="flex items-start justify-between">
        <div>
          <p className="font-extrabold text-[22px] tracking-tight leading-none">ALE<span className="text-marker">.</span></p>
          <p className="mt-1 text-[10.5px] tracking-[.18em] text-white/50">ФИНКИ · ЛАБОРАТОРИЈА</p>
        </div>
        {/* the chip */}
        <span aria-hidden className="w-12 h-9 rounded-md bg-marker relative shadow-[inset_0_0_0_1px_rgba(0,0,0,.25)]">
          <span className="absolute inset-x-2 top-1/2 h-px bg-black/30" />
          <span className="absolute inset-y-1.5 left-1/2 w-px bg-black/30" />
          <span className="absolute inset-y-2 left-3 right-3 border-x border-black/25 rounded-sm" />
        </span>
      </div>

      <div className="absolute left-6 right-6 sm:left-7 sm:right-7 bottom-6 sm:bottom-7 flex items-end gap-4">
        {!blank && <Avatar name={name} url={avatarUrl} size={52} className="ring-2 ring-white/20 shrink-0" />}
        <div className="min-w-0 flex-1">
          <p className={`font-extrabold text-[20px] sm:text-[23px] leading-tight truncate ${blank ? 'text-white/35' : ''}`}>{name}</p>
          <p className="mt-1 flex items-center gap-2 text-[12.5px]">
            <span className="rounded-full bg-marker text-ink font-bold px-2 py-px">{role}</span>
            {lines.map((l, i) => <span key={i} className="text-white/60 truncate">{l}</span>)}
          </p>
        </div>
        <p className="hidden sm:block font-mono text-[10.5px] text-white/40 tracking-wider shrink-0">{serial}</p>
      </div>
    </div>
  )
}
