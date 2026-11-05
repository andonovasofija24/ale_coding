import { useMemo } from 'react'
import { SNIPPETS } from '../lib/snippets'
import { LANG_ORDER } from '../lib/languages'

/**
 * Decoration: columns of short code snippets drifting slowly upwards, each in the colour of its language.
 * Purely visual (aria-hidden, no pointer events), very low contrast, and still for people who ask their system
 * for reduced motion. Never used behind the editor — only on welcome screens, headers and empty states.
 */
export default function CodeBackdrop({ langs = LANG_ORDER, tone = 'dark', columns = 4, className = '' }: {
  langs?: readonly string[]; tone?: 'dark' | 'light'; columns?: number; className?: string
}) {
  const cols = useMemo(() => {
    const pool = langs.flatMap((l) => (SNIPPETS[l] ?? []).map((code) => ({ l, code })))
    if (!pool.length) return []
    return Array.from({ length: columns }, (_, c) => {
      // a fixed, different order per column (no Math.random: the same picture on every render)
      const items = Array.from({ length: 7 }, (_, i) => pool[(c * 5 + i * 3 + c * i) % pool.length])
      return { items, duration: 70 + c * 17, offset: c * -13 }
    })
  }, [langs, columns])

  return (
    <div aria-hidden className={`pointer-events-none absolute inset-0 overflow-hidden select-none ${className}`}>
      <div className="absolute inset-0 grid gap-6 px-6" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {cols.map((col, c) => (
          <div key={c} className="relative">
            <div className="animate-drift motion-reduce:animate-none" style={{ ['--drift-duration' as any]: `${col.duration}s`, animationDelay: `${col.offset}s` }}>
              {[0, 1].map((copy) => (
                <div key={copy}>
                  {col.items.map((s, i) => (
                    <pre key={i} className={`lang-${s.l} font-mono text-[12px] leading-relaxed whitespace-pre mb-10 ${
                      tone === 'dark' ? 'text-marker opacity-[0.22]' : 'text-marker-deep opacity-[0.16]'}`}>
                      {s.code}
                    </pre>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
