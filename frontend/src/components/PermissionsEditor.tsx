import { Check } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import type { Permission, PermTemplate } from '../types'
import { cleanPerms, PERM_GROUPS, TEMPLATES, templateOf } from '../lib/perms'

type T = ReturnType<typeof useLanguage>['t']

/** A short name for a teacher's permissions: the template they match, or "own permissions". */
export function permLabel(template: PermTemplate | null | undefined, t: T, perms?: Permission[]) {
  if (template) return t(`perm.tpl.${template}` as any)
  if (perms && perms.length === 0) return t('perm.none')
  return t('perm.custom')
}

/** The admin ticks what one teacher may do in one subject. The templates only tick boxes — nothing is stored but
 *  the permissions themselves. */
export default function PermissionsEditor({ value, onChange, compact = false }: {
  value: Permission[]; onChange: (p: Permission[]) => void; compact?: boolean
}) {
  const { t } = useLanguage()
  const have = new Set(value)
  const current = templateOf(value)
  const toggle = (p: Permission) => {
    const next = new Set(have)
    if (next.has(p)) {
      next.delete(p)
      // without seeing them, you can't make or grade them either
      if (p.endsWith('.view')) {
        const g = p.split('.')[0]
        for (const x of [...next]) if (x.startsWith(g + '.')) next.delete(x)
        if (g === 'grades') { next.delete('grades.final'); next.delete('grades.rules') }
      }
      onChange(cleanPerms(next))
    } else {
      next.add(p)
      onChange(cleanPerms(next))
    }
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[12px] text-ink-muted mr-1">{t('perm.likeA')}</span>
        {(Object.keys(TEMPLATES) as PermTemplate[]).map((k) => (
          <button key={k} type="button" onClick={() => onChange([...TEMPLATES[k]])}
            className={`h-7 px-2.5 rounded-full text-[12px] font-semibold border transition-colors ${
              current === k ? 'bg-ink text-white border-ink' : 'border-line text-ink-muted hover:text-ink hover:border-ink/40'}`}>
            {t(`perm.tpl.${k}` as any)}
          </button>
        ))}
        <button type="button" onClick={() => onChange([])}
          className="h-7 px-2.5 rounded-full text-[12px] font-semibold text-ink-faint hover:text-bad">{t('perm.clear')}</button>
      </div>
      <div className={`grid gap-3 ${compact ? 'sm:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-4'}`}>
        {PERM_GROUPS.map((g) => (
          <fieldset key={g.key} className="rounded-lg border border-line-soft px-3 py-2.5">
            <legend className="px-1 text-[12px] font-bold text-ink">{t(`perm.group.${g.key}` as any)}</legend>
            <ul className="space-y-1">
              {g.perms.map((p) => (
                <li key={p}>
                  <label className="flex items-start gap-2 text-[13px] cursor-pointer py-0.5">
                    <input type="checkbox" className="peer sr-only" checked={have.has(p)} onChange={() => toggle(p)} />
                    <span className={`mt-0.5 w-4 h-4 shrink-0 rounded border inline-flex items-center justify-center peer-focus-visible:ring-2 peer-focus-visible:ring-cobalt/40 ${
                      have.has(p) ? 'bg-cobalt border-cobalt text-white' : 'border-line bg-white'}`}>
                      {have.has(p) && <Check size={12} strokeWidth={3} />}
                    </span>
                    <span>{t(`perm.${p}` as any)}</span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        ))}
      </div>
    </div>
  )
}
