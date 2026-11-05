/**
 * An SQL result written as text — a header line, then one line per row, cells separated by "|" —
 * drawn as a small table. Used for expected / actual results of SQL tests.
 */
export function parseResultTable(text: string): { columns: string[]; rows: string[][] } | null {
  const lines = text.split('\n').map((l) => l.trimEnd()).filter((l) => l.trim() !== '')
  if (lines.length === 0) return null
  const split = (l: string) => l.split('|').map((c) => c.trim())
  return { columns: split(lines[0]), rows: lines.slice(1).map(split) }
}

export default function ResultTable({
  text,
  tone = 'ink',
  emptyLabel,
  highlight = [],
}: {
  text: string
  tone?: 'ink' | 'ok' | 'bad'
  emptyLabel?: string
  highlight?: number[]
}) {
  const table = parseResultTable(text)
  if (!table) return <p className="text-xs text-ink-muted italic">{emptyLabel ?? '—'}</p>
  const toneClass = tone === 'ok' ? 'text-ok' : tone === 'bad' ? 'text-bad' : 'text-ink'
  return (
    <div className="overflow-x-auto rounded-md border border-line-soft bg-surface max-w-full">
      <table className="text-[12px] font-mono border-collapse">
        <thead>
          <tr className="bg-paper">
            {table.columns.map((c, i) => (
              <th key={i} className="px-2.5 py-1 text-left font-semibold text-ink-soft border-b border-line-soft whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className={highlight.includes(i) ? 'bg-marker-soft' : i % 2 ? 'bg-paper/40' : ''}>
              {r.map((c, j) => (
                <td key={j} className={`px-2.5 py-0.5 whitespace-nowrap ${c === 'NULL' ? 'text-ink-faint italic' : toneClass}`}>{c}</td>
              ))}
            </tr>
          ))}
          {table.rows.length === 0 && (
            <tr><td colSpan={table.columns.length} className="px-2.5 py-1 text-ink-faint italic">{emptyLabel ?? '—'}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
