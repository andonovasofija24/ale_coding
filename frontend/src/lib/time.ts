import { useEffect, useState } from 'react'
import { LOCALES, Lang } from '../i18n/translations'

// Macedonian is formatted by hand: many browsers ship without Macedonian date data and would fall back to English.
const MK_DAYS = ['нед', 'пон', 'вто', 'сре', 'чет', 'пет', 'саб']
const MK_MONTHS = ['јан', 'фев', 'мар', 'апр', 'мај', 'јун', 'јул', 'авг', 'сеп', 'окт', 'ное', 'дек']
const pad2 = (n: number) => String(n).padStart(2, '0')

/** "пет, 24 окт., 23:59" in the UI language (the browser's time zone). */
export function formatDateTime(iso: string, lang: Lang): string {
  const d = new Date(iso)
  if (lang === 'mk') return `${MK_DAYS[d.getDay()]}, ${d.getDate()} ${MK_MONTHS[d.getMonth()]}., ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
  return d.toLocaleString(LOCALES[lang], { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** "20.10.2026" / "20/10/2026" */
export function formatDate(iso: string, lang: Lang): string {
  const d = new Date(iso)
  if (lang === 'mk') return `${d.getDate()}.${d.getMonth() + 1}.${d.getFullYear()}`
  return d.toLocaleDateString(LOCALES[lang])
}

/** "за 2 часа" / "пред 3 дена" — relative to now. */
export function relative(iso: string, lang: Lang, now = Date.now()): string {
  const diff = new Date(iso).getTime() - now
  const abs = Math.abs(diff)
  const min = 60_000, hour = 60 * min, day = 24 * hour
  const [n, unit] = abs < hour ? [Math.round(diff / min), 'minute'] as const
    : abs < day ? [Math.round(diff / hour), 'hour'] as const : [Math.round(diff / day), 'day'] as const
  if (lang !== 'mk') return new Intl.RelativeTimeFormat(LOCALES[lang], { numeric: 'auto' }).format(n, unit)
  if (n === 0) return 'сега'
  const k = Math.abs(n)
  const word = unit === 'minute' ? (k === 1 ? 'минута' : 'минути') : unit === 'hour' ? (k === 1 ? 'час' : 'часа')
    : k === 1 ? 'ден' : 'дена'
  if (unit === 'day' && k === 1) return n > 0 ? 'утре' : 'вчера'
  return `${n > 0 ? 'за' : 'пред'} ${k} ${word}`
}

/** "1:23:45" left until `iso` (or null when it has passed). */
export function countdown(iso: string, now = Date.now()): string | null {
  const ms = new Date(iso).getTime() - now
  if (ms <= 0) return null
  const s = Math.floor(ms / 1000)
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return d > 0 ? `${d}d ${h}:${pad(m)}:${pad(sec)}` : `${h}:${pad(m)}:${pad(sec)}`
}

/** Re-render every `ms` (for countdowns). */
export function useNow(ms = 1000): number {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(id)
  }, [ms])
  return now
}

/** <input type="datetime-local"> value (local time) <-> ISO string (UTC). */
export function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function fromLocalInput(v: string): string | null {
  return v ? new Date(v).toISOString() : null
}

/** "24 окт." */
export function formatShortDate(iso: string, lang: Lang): string {
  const d = new Date(iso)
  if (lang === 'mk') return `${d.getDate()} ${MK_MONTHS[d.getMonth()]}.`
  return d.toLocaleDateString(LOCALES[lang], { day: 'numeric', month: 'short' })
}

/** Count with the right word form: plural(1, 'задача', 'задачи') -> "1 задача". */
export function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}
