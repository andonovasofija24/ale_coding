import { useState } from 'react'
import { API_BASE } from '../services/api'

function initials(name?: string) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
}

// A calm colour per person (from the name), so initials avatars in a list are easy to tell apart.
const TONES = ['bg-ink', 'bg-cobalt', 'bg-obj', 'bg-ok', 'bg-[#8a5a00]', 'bg-[#a2355a]']
function tone(name?: string) {
  let h = 0
  for (const ch of name || '') h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return TONES[h % TONES.length]
}

/** Profile picture, or the person's initials when there is none (or it fails to load). */
export default function Avatar({ name, url, size = 32, className = '' }: { name?: string; url?: string | null; size?: number; className?: string }) {
  const [broken, setBroken] = useState(false)
  const style = { width: size, height: size, fontSize: Math.max(10, Math.round(size * 0.38)) }
  if (url && !broken) {
    return <img src={`${API_BASE}${url}`} alt="" style={style} onError={() => setBroken(true)}
      className={`rounded-full object-cover bg-line-soft shrink-0 ${className}`} />
  }
  return (
    <span aria-hidden style={style} className={`rounded-full text-white font-bold flex items-center justify-center shrink-0 ${tone(name)} ${className}`}>
      {initials(name)}
    </span>
  )
}
