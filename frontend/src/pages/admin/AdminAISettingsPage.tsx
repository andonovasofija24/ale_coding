import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, Loader2, PlugZap, Save, CheckCircle2, XCircle, AlertTriangle, KeyRound, RotateCcw, ShieldCheck } from 'lucide-react'
import { adminApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { AIProvider, AISettings, AITestResult } from '../../types'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import SavedKey from '../../components/SavedKey'
import { DEFAULT_MODEL, keyMismatch, SUGGESTIONS, URL_EXAMPLES } from '../../lib/aiProviders'

export default function AdminAISettingsPage() {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const { data: current, isLoading } = useQuery<AISettings>({ queryKey: ['ai-settings'], queryFn: adminApi.getAISettings })

  const [provider, setProvider] = useState<AIProvider>('openai')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [test, setTest] = useState<AITestResult | null>(null)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    if (current) {
      setProvider(current.provider)
      setModel(current.model)
      setBaseUrl(current.base_url)
    }
  }, [current])

  const changeProvider = (p: AIProvider) => {
    setProvider(p)
    setTest(null)
    if (p !== current?.provider) setModel(DEFAULT_MODEL[p])
    else setModel(current.model)
  }

  // An empty key field keeps the stored key, but only for the same provider.
  const keepsStoredKey = !apiKey && !!current?.has_key && provider === current.provider
  const payload = () => ({ provider, model, base_url: provider === 'openai_compatible' ? baseUrl : '', api_key: apiKey || null })
 const mismatch = apiKey ? keyMismatch(apiKey, provider, baseUrl) : null
  const switchTo = (k: NonNullable<typeof mismatch>) => {
    setProvider(k.provider)
    setModel(k.provider === current?.provider && current.model ? current.model : k.model)
    if (k.baseUrl) setBaseUrl(k.baseUrl)
    setTest(null)
  }
  const canSubmit = !!model.trim() && (provider !== 'openai_compatible' || !!baseUrl.trim()) && (!!apiKey || keepsStoredKey)

  const runTest = async () => {
    setTesting(true); setTest(null); setMessage(null)
    try {
      setTest(await adminApi.testAISettings(payload()))
    } catch (err: any) {
      setTest({ ok: false, latency_ms: 0, error: tError(err.response?.data?.detail, 'ai.testFailed') })
    } finally {
      setTesting(false)
    }
  }

  const save = async () => {
    setSaving(true); setMessage(null)
    try {
      const saved: AISettings = await adminApi.saveAISettings(payload())
      qc.setQueryData(['ai-settings'], saved)
      setApiKey('')
      setMessage({ ok: true, text: t('ai.saved', { model: saved.model }) })
    } catch (err: any) {
      setMessage({ ok: false, text: tError(err.response?.data?.detail, 'ai.saveFailed') })
    } finally {
      setSaving(false)
    }
  }

  const reset = async () => {
    if (!confirm(t('ai.resetConfirm'))) return
    const saved: AISettings = await adminApi.resetAISettings()
    qc.setQueryData(['ai-settings'], saved)
    setApiKey(''); setTest(null)
    setMessage({ ok: true, text: t('ai.resetDone') })
  }

  const providers: { id: AIProvider; name: string; hint: string }[] = [
    { id: 'openai', name: 'OpenAI', hint: t('ai.p.openai') },
    { id: 'anthropic', name: 'Anthropic', hint: t('ai.p.anthropic') },
    { id: 'openai_compatible', name: t('ai.p.compatibleName'), hint: t('ai.p.compatible') },
  ]

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('ai.title')}</h1>
        <p className="mt-2 text-ink-muted max-w-xl">{t('ai.intro')}</p>

        {/* What is active right now */}
        {current && (
          <section className="mt-8 card px-5 py-4 flex flex-wrap items-center gap-x-6 gap-y-3" aria-label={t('ai.activeNow')}>
            <div>
              <p className="text-xs text-ink-muted">{t('ai.activeNow')}</p>
              <p className="mt-0.5 font-semibold">
                {providers.find((p) => p.id === current.provider)?.name} · <span className="font-mono text-[14px]">{current.model}</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-ink-muted">{t('ai.keyLabel')}</p>
              {current.has_key ? <SavedKey hint={current.key_hint} reveal={adminApi.revealAIKey} /> : <p className="mt-0.5 font-mono text-[14px]">—</p>}
            </div>
            <span className={`sm:ml-auto inline-flex items-center gap-1.5 text-xs font-semibold rounded-full px-2.5 py-1 ${
              current.source === 'database' ? 'bg-ok-soft text-ok' : 'bg-paper text-ink-soft'
            }`}>
              {current.source === 'database' ? <ShieldCheck size={13} /> : <KeyRound size={13} />}
              {current.source === 'database' ? t('ai.sourceDb') : t('ai.sourceEnv')}
            </span>
            {current.key_unreadable && (
              <p role="alert" className="w-full flex gap-2 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {t('ai.keyUnreadable')}
              </p>
            )}
            {!current.has_key && !current.key_unreadable && (
              <p role="alert" className="w-full flex gap-2 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {t('ai.noKey')}
              </p>
            )}
          </section>
        )}

        {isLoading ? (
          <div className="mt-8 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : (
          <form className="mt-8 card p-5 sm:p-6 space-y-6" onSubmit={(e) => { e.preventDefault(); if (canSubmit) save() }}>
            <fieldset>
              <legend className="field-label">{t('ai.provider')}</legend>
              <div className="grid sm:grid-cols-3 gap-2">
                {providers.map((p) => {
                  const active = provider === p.id
                  return (
                    <label
                      key={p.id}
                      className={`cursor-pointer rounded-lg border px-3.5 py-3 transition-colors ${
                        active ? 'border-ink bg-paper/60 ring-1 ring-ink' : 'border-line hover:border-ink-faint'
                      }`}
                    >
                      <input type="radio" name="provider" value={p.id} checked={active} onChange={() => changeProvider(p.id)} className="sr-only" />
                      <span className="block font-semibold text-sm">{p.name}</span>
                      <span className="block mt-0.5 text-xs text-ink-muted leading-snug">{p.hint}</span>
                    </label>
                  )
                })}
              </div>
            </fieldset>

            {provider === 'openai_compatible' && (
              <div>
                <label htmlFor="base" className="field-label">{t('ai.baseUrl')}</label>
                <input id="base" className="input font-mono text-[13px]" value={baseUrl} onChange={(e) => { setBaseUrl(e.target.value); setTest(null) }}
                  placeholder="https://api.groq.com/openai/v1" list="url-examples" />
                <datalist id="url-examples">{URL_EXAMPLES.map((u) => <option key={u} value={u} />)}</datalist>
                <p className="field-hint">{t('ai.baseUrlHint')}</p>
              </div>
            )}

            <div>
              <label htmlFor="model" className="field-label">{t('ai.model')}</label>
              <input id="model" className="input font-mono text-[13px]" value={model} onChange={(e) => { setModel(e.target.value); setTest(null) }}
                list="model-suggestions" placeholder={SUGGESTIONS[provider][0]} required />
              <datalist id="model-suggestions">{SUGGESTIONS[provider].map((m) => <option key={m} value={m} />)}</datalist>
              <p className="field-hint">{t('ai.modelHint')}</p>
            </div>

            <div>
              <label htmlFor="key" className="field-label">{t('ai.apiKey')}</label>
              <div className="relative">
                <input
                  id="key"
                  type={showKey ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  className="input font-mono text-[13px] pr-10"
                  value={apiKey}
                  onChange={(e) => { setApiKey(e.target.value); setTest(null) }}
                  placeholder={keepsStoredKey ? t('ai.keyKeep', { hint: current!.key_hint }) : t('ai.keyPlaceholder')}
                />
                <button type="button" onClick={() => setShowKey((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 btn-ghost btn-sm px-1.5 h-7"
                  aria-label={showKey ? t('ai.hideKey') : t('ai.showKey')}>
                  {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <p className="field-hint flex items-center gap-1"><ShieldCheck size={12} /> {t('ai.keySafety')}</p>
              {mismatch && (
                <div role="alert" className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-bad-soft text-bad px-3 py-2 text-sm">
                  <AlertTriangle size={16} className="shrink-0" />
                  <span className="flex-1 min-w-[12rem]">{t('ai.keyMismatch', { name: mismatch.name })}</span>
                  <button type="button" onClick={() => switchTo(mismatch)} className="btn-secondary btn-sm">
                    {t('ai.switchTo', { name: mismatch.name })}
                  </button>
                </div>
              )}
            </div>

            {/* Test result */}
            {test && (
              <div role="status" className={`flex gap-2.5 rounded-lg px-3.5 py-3 text-sm ${test.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>
                {test.ok ? <CheckCircle2 size={17} className="shrink-0 mt-0.5" /> : <XCircle size={17} className="shrink-0 mt-0.5" />}
                <div className="min-w-0">
                  <p className="font-semibold">{test.ok ? t('ai.testOk', { ms: test.latency_ms }) : t('ai.testBad')}</p>
                  {test.ok
                    ? <p className="mt-0.5 text-ink-soft">{t('ai.testReply')} <span className="font-mono">{test.reply}</span></p>
                    : <p className="mt-1 font-mono text-[12px] break-words text-ink-soft">{test.error}</p>}
                </div>
              </div>
            )}
            {message && (
              <p role="status" className={`text-sm font-semibold rounded-lg px-3.5 py-2.5 ${message.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>
                {message.text}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button type="button" onClick={runTest} disabled={!canSubmit || testing} className="btn-secondary">
                {testing ? <Loader2 size={15} className="animate-spin" /> : <PlugZap size={15} />}
                {testing ? t('ai.testing') : t('ai.test')}
              </button>
              <button type="submit" disabled={!canSubmit || saving} className="btn-primary">
                {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
                {t('ai.save')}
              </button>
              {current?.source === 'database' && (
                <button type="button" onClick={reset} className="btn-ghost sm:ml-auto text-ink-muted">
                  <RotateCcw size={14} /> {t('ai.reset')}
                </button>
              )}
            </div>
          </form>
        )}

        <p className="mt-6 text-sm text-ink-muted leading-relaxed">{t('ai.costNote')}</p>
      </main>
    </div>
  )
}
