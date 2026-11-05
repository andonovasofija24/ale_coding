import { useState } from 'react'
import { Copy, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

/** A saved API key: shown as a hint ("sk-…a1b2"); the eye shows the whole key (fetched only then, for its owner). */
export default function SavedKey({ hint, reveal }: { hint: string; reveal: () => Promise<string> }) {
  const { t } = useLanguage()
  const [full, setFull] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const toggle = async () => {
    if (full) { setFull(null); return }
    setBusy(true)
    try { setFull(await reveal()) } catch { setFull(null) } finally { setBusy(false) }
  }
  return (
    <span className="mt-0.5 inline-flex items-center gap-1.5 max-w-full">
      <span className={`font-mono text-[13.5px] ${full ? 'break-all select-all bg-marker-soft rounded px-1' : ''}`}>{full ?? hint}</span>
      <button type="button" onClick={toggle} className="btn-ghost btn-sm h-7 px-1.5 shrink-0" disabled={busy}
        aria-label={full ? t('ai.hideKey') : t('ai.showKey')} title={full ? t('ai.hideKey') : t('ai.showKey')} aria-pressed={!!full}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : full ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
      {full && (
        <button type="button" className="btn-ghost btn-sm h-7 px-1.5 shrink-0" title={t('ai.copyKey')} aria-label={t('ai.copyKey')}
          onClick={async () => { try { await navigator.clipboard.writeText(full); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* ignore */ } }}>
          <Copy size={13} /> {copied && <span className="text-[11px] text-ok">{t('ai.copied')}</span>}
        </button>
      )}
    </span>
  )
}
