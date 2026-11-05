import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Loader2, PlugZap, Save, ShieldCheck, Sparkles, Trash2, XCircle } from 'lucide-react'
import { ownKeyApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { AIProvider, AITestResult } from '../types'
import { DEFAULT_MODEL, keyMismatch, SUGGESTIONS, URL_EXAMPLES } from '../lib/aiProviders'
import PasswordInput from './PasswordInput'
import SavedKey from './SavedKey'
import { IconTile } from './EmptyState'

interface OwnKey { has_key: boolean; provider: AIProvider | ''; model: string; base_url: string; key_hint: string; key_unreadable: boolean }

/** Profile: a person's own AI provider + key. With it their AI help runs on their own key, without the
 *  platform's daily allowance. The key is stored encrypted; the eye shows it to its owner only. */
export default function OwnAIKeyCard() {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const { data: cur } = useQuery<OwnKey>({ queryKey: ['own-ai-key'], queryFn: ownKeyApi.get })
  const [provider, setProvider] = useState<AIProvider>('openai')
  const [model, setModel] = useState(DEFAULT_MODEL.openai)
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [busy, setBusy] = useState<'' | 'test' | 'save' | 'remove'>('')
  const [test, setTest] = useState<AITestResult | null>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    if (cur?.has_key && cur.provider) { setProvider(cur.provider); setModel(cur.model); setBaseUrl(cur.base_url) }
  }, [cur])

  const keeps = !apiKey && !!cur?.has_key && provider === cur.provider
  const canSubmit = !!model.trim() && (provider !== 'openai_compatible' || !!baseUrl.trim()) && (!!apiKey || keeps)
  const payload = () => ({ provider, model, base_url: provider === 'openai_compatible' ? baseUrl : '', api_key: apiKey || null })
  const mismatch = apiKey ? keyMismatch(apiKey, provider, baseUrl) : null
  const pick = (p: AIProvider) => { setProvider(p); setTest(null); setModel(p === cur?.provider ? cur.model : DEFAULT_MODEL[p]) }

  const run = async (what: 'test' | 'save' | 'remove') => {
    setBusy(what); setMsg(null); if (what !== 'test') setTest(null)
    try {
      if (what === 'test') setTest(await ownKeyApi.test(payload()))
      else if (what === 'save') {
        qc.setQueryData(['own-ai-key'], await ownKeyApi.save(payload()))
        setApiKey(''); setMsg({ ok: true, text: t('ownkey.saved') })
      } else {
        if (!confirm(t('ownkey.removeConfirm'))) return
        qc.setQueryData(['own-ai-key'], await ownKeyApi.remove())
        setApiKey(''); setMsg({ ok: true, text: t('ownkey.removed') })
      }
    } catch (err: any) {
      const text = tError(err.response?.data?.detail, 'ownkey.failed')
      if (what === 'test') setTest({ ok: false, latency_ms: 0, error: text }); else setMsg({ ok: false, text })
    } finally { setBusy('') }
  }

  const providers: { id: AIProvider; name: string }[] = [
    { id: 'openai', name: 'OpenAI' }, { id: 'anthropic', name: 'Anthropic' }, { id: 'openai_compatible', name: t('ai.p.compatibleName') },
  ]

  return (
    <section className="mt-5 card p-5 sm:p-6 space-y-4" aria-labelledby="own-key-title" data-tour="own-key">
      <div className="flex flex-wrap items-start gap-3">
        <IconTile tone="marker"><Sparkles size={19} /></IconTile>
        <div className="flex-1 min-w-[14rem]">
          <h2 id="own-key-title" className="font-bold">{t('ownkey.title')}</h2>
          <p className="text-[13px] text-ink-muted mt-0.5">{t('ownkey.intro')}</p>
        </div>
        {cur?.has_key && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold rounded-full px-2.5 py-1 bg-ok-soft text-ok"><ShieldCheck size={13} /> {t('ownkey.active')}</span>
        )}
      </div>

      {cur?.has_key && (
        <div className="rounded-lg border border-line bg-paper/50 px-3.5 py-2.5 flex flex-wrap items-center gap-x-6 gap-y-1">
          <div>
            <p className="text-xs text-ink-muted">{t('ai.activeNow')}</p>
            <p className="font-semibold text-sm">{providers.find((p) => p.id === cur.provider)?.name} · <span className="font-mono text-[13px]">{cur.model}</span></p>
          </div>
          <div className="min-w-0">
            <p className="text-xs text-ink-muted">{t('ai.keyLabel')}</p>
            <SavedKey hint={cur.key_hint} reveal={ownKeyApi.reveal} />
          </div>
          {cur.key_unreadable && <p role="alert" className="w-full text-[13px] text-bad flex gap-1.5"><AlertTriangle size={14} className="mt-0.5" /> {t('ai.keyUnreadable')}</p>}
        </div>
      )}

      <fieldset>
        <legend className="field-label">{t('ai.provider')}</legend>
        <div className="flex flex-wrap gap-2">
          {providers.map((p) => (
            <label key={p.id} className={`cursor-pointer rounded-lg border px-3 py-1.5 text-sm font-semibold ${provider === p.id ? 'border-ink ring-1 ring-ink bg-paper/60' : 'border-line hover:border-ink-faint'}`}>
              <input type="radio" name="own-provider" className="sr-only" checked={provider === p.id} onChange={() => pick(p.id)} /> {p.name}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label htmlFor="own-model" className="field-label">{t('ai.model')}</label>
          <input id="own-model" className="input font-mono text-[13px]" value={model} list="own-models" onChange={(e) => { setModel(e.target.value); setTest(null) }} />
          <datalist id="own-models">{SUGGESTIONS[provider].map((m) => <option key={m} value={m} />)}</datalist>
        </div>
        {provider === 'openai_compatible' && (
          <div>
            <label htmlFor="own-base" className="field-label">{t('ai.baseUrl')}</label>
            <input id="own-base" className="input font-mono text-[13px]" value={baseUrl} list="own-urls" placeholder="https://openrouter.ai/api/v1"
              onChange={(e) => { setBaseUrl(e.target.value); setTest(null) }} />
            <datalist id="own-urls">{URL_EXAMPLES.map((u) => <option key={u} value={u} />)}</datalist>
          </div>
        )}
      </div>
      <div>
        <label htmlFor="own-key" className="field-label">{t('ai.apiKey')}</label>
        <PasswordInput id="own-key" autoComplete="off" spellCheck={false} className="input font-mono text-[13px]" value={apiKey}
          onChange={(e) => { setApiKey(e.target.value); setTest(null) }}
          placeholder={keeps ? t('ai.keyKeep', { hint: cur!.key_hint }) : t('ai.keyPlaceholder')} />
        <p className="field-hint flex items-center gap-1"><ShieldCheck size={12} /> {t('ownkey.safety')}</p>
        {mismatch && (
          <p role="alert" className="mt-2 flex flex-wrap items-center gap-2 rounded-lg bg-bad-soft text-bad px-3 py-2 text-sm">
            <AlertTriangle size={15} /> {t('ai.keyMismatch', { name: mismatch.name })}
            <button type="button" className="btn-secondary btn-sm" onClick={() => { setProvider(mismatch.provider); setModel(mismatch.model); if (mismatch.baseUrl) setBaseUrl(mismatch.baseUrl) }}>
              {t('ai.switchTo', { name: mismatch.name })}
            </button>
          </p>
        )}
      </div>

      {test && (
        <div role="status" className={`flex gap-2 rounded-lg px-3 py-2.5 text-sm ${test.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>
          {test.ok ? <CheckCircle2 size={16} className="shrink-0 mt-0.5" /> : <XCircle size={16} className="shrink-0 mt-0.5" />}
          <span className="min-w-0">{test.ok ? t('ai.testOk', { ms: test.latency_ms }) : <>{t('ai.testBad')} <span className="font-mono text-[12px] break-words text-ink-soft">{test.error}</span></>}</span>
        </div>
      )}
      {msg && <p role="status" className={`text-sm font-semibold rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className="btn-secondary" disabled={!canSubmit || !!busy} onClick={() => run('test')}>
          {busy === 'test' ? <Loader2 size={15} className="animate-spin" /> : <PlugZap size={15} />} {t('ai.test')}
        </button>
        <button type="button" className="btn-primary" disabled={!canSubmit || !!busy} onClick={() => run('save')}>
          {busy === 'save' ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('ai.save')}
        </button>
        {cur?.has_key && (
          <button type="button" className="btn-ghost sm:ml-auto text-ink-muted hover:text-bad" disabled={!!busy} onClick={() => run('remove')}>
            <Trash2 size={14} /> {t('ownkey.remove')}
          </button>
        )}
      </div>
    </section>
  )
}
