import { Link } from 'react-router-dom'
import { CheckCircle2, ChevronRight, Lock, XCircle } from 'lucide-react'
import { RunTestsResponse } from '../types'
import { useLanguage } from '../i18n/LanguageContext'

/** Compact result of a test run beside the editor: score, one chip per test, the first failure, and a link to the
 *  full tests page (inputs, expected and actual output side by side). */
export default function TestsSummary({ r, to, onOpen }: { r: RunTestsResponse; to: string; onOpen?: () => void }) {
  const { t } = useLanguage()
  const all = r.passed === r.total
  const firstFail = r.results.find((x) => !x.passed)
  return (
    <div className={`rounded-lg border px-4 py-3.5 ${all ? 'bg-ok-soft border-ok/30' : 'bg-surface border-line'}`}>
      <p className="text-[13px] font-semibold text-ink-soft">{all ? t('tests.allPassed') : t('tests.someFailed')}</p>
      <p className="mt-0.5 text-2xl font-extrabold tabular-nums">
        <span className={all ? 'text-ok' : 'text-bad'}>{r.passed}</span>
        <span className="text-ink-muted text-base font-semibold"> / {r.total}</span>
      </p>
      <ul className="mt-2.5 flex flex-wrap gap-1.5" aria-label={t('tests.perTest')}>
        {r.results.map((x) => (
          <li key={x.test_number} title={x.passed ? t('tests.passedN', { n: x.test_number }) : t('tests.failedN', { n: x.test_number })}
            className={`inline-flex items-center gap-1 text-[12px] font-semibold rounded-full px-2 py-0.5 tabular-nums ${
              x.passed ? 'bg-surface text-ok border border-ok/30' : 'bg-bad-soft text-bad'}`}>
            {x.passed ? <CheckCircle2 size={12} /> : <XCircle size={12} />} {x.test_number}
            {x.hidden && <Lock size={10} className="opacity-70" />}
          </li>
        ))}
      </ul>
      {firstFail && (
        <p className="mt-2.5 text-[13px] text-ink-soft">
          {t('tests.firstFail', { n: firstFail.test_number })}{' '}
          <span className="font-mono text-[12px] text-bad">{(firstFail.error || '').split('\n')[0] || t('tests.wrongOutput')}</span>
        </p>
      )}
      <Link to={to} onClick={onOpen} className="mt-3 btn-secondary w-full justify-between">
        {t('tests.openAll')} <ChevronRight size={15} />
      </Link>
    </div>
  )
}
