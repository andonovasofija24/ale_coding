import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowDown, ArrowLeftRight, ArrowUp, Cable, Maximize, Plus, Trash2, User, X, ZoomIn, ZoomOut } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { DEdge, Diagram, DNode, dumpDiagram, EdgeKind, KIND_SPEC, newId, NodeType, parseDiagram } from '../lib/diagram'

const INK = '#1A2233', MUTED = '#6B7488', ACCENT = '#2747C9'
const TOP = 40          // where the lifeline heads are
const HEAD_H = 46       // height of an object's head box
const STEP = 50         // default distance between messages
const CHAR = 7.4
type Sel = { type: 'node' | 'edge'; id: string } | null

const headW = (n: DNode) => n.type === 'actor' ? Math.max(80, n.name.length * CHAR + 16) : Math.max(120, n.name.length * CHAR + 32)
const centre = (n: DNode) => n.x + headW(n) / 2

/**
 * Sequence diagram editor: lifelines (objects / actors) side by side, each with its dashed line of life going down,
 * and the messages between them as horizontal arrows — the higher an arrow, the earlier it happens. Drag a lifeline
 * sideways, drag a message up or down to change the order (or use the arrows on the right). Kept as JSON in `code`
 * (the same format as the other diagrams; each message has its "y").
 */
export default function SequenceEditor({ code, onChange, readOnly = false }: {
  code: string; onChange?: (v: string) => void; readOnly?: boolean
}) {
  const { t } = useLanguage()
  const d = useMemo(() => parseDiagram(code, 'sequence'), [code])
  const [sel, setSel] = useState<Sel>(null)
  const [connect, setConnect] = useState<{ kind: EdgeKind; from?: string } | null>(null)
  const [view, setView] = useState({ x: 0, y: 0, k: 1 })
  const [drag, setDrag] = useState<{ type: 'node' | 'edge'; id: string; start: number; orig: number; now: number } | null>(null)
  const pan = useRef<{ sx: number; sy: number; vx: number; vy: number } | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const fitted = useRef(false)

  const commit = (next: Diagram) => onChange?.(dumpDiagram(next))
  const nodeX = (n: DNode) => (drag?.type === 'node' && drag.id === n.id ? drag.now : n.x)
  const edgeY = (e: DEdge) => (drag?.type === 'edge' && drag.id === e.id ? drag.now : e.y ?? 0)
  const ordered = useMemo(() => [...d.edges].sort((a, b) => (a.y ?? 0) - (b.y ?? 0)), [d])
  const bottom = Math.max(TOP + HEAD_H + 140, ...d.edges.map((e) => (e.y ?? 0) + (e.from === e.to ? 70 : 60)))

  const fit = () => {
    const el = svg.current
    if (!el || !d.nodes.length) { setView({ x: 0, y: 0, k: 1 }); return }
    const minX = Math.min(...d.nodes.map((n) => n.x)) - 30, maxX = Math.max(...d.nodes.map((n) => n.x + headW(n))) + 60
    const k = Math.min(1.2, el.clientWidth / (maxX - minX), el.clientHeight / (bottom + 30))
    setView({ k, x: -minX * k + (el.clientWidth - (maxX - minX) * k) / 2, y: 6 })
  }
  useEffect(() => { if (!fitted.current && d.nodes.length) { fitted.current = true; fit() } }) // eslint-disable-line react-hooks/exhaustive-deps

  const updNode = (id: string, p: Partial<DNode>) => commit({ ...d, nodes: d.nodes.map((n) => (n.id === id ? { ...n, ...p } : n)) })
  const updEdge = (id: string, p: Partial<DEdge>) => commit({ ...d, edges: d.edges.map((e) => (e.id === id ? { ...e, ...p } : e)) })
  const addNode = (type: NodeType) => {
    const id = newId('n')
    const x = d.nodes.length ? Math.max(...d.nodes.map((n) => n.x + headW(n))) + 60 : 40
    commit({ ...d, nodes: [...d.nodes, { id, name: type === 'actor' ? t('dg.ntype.actor') : `:${t('seq.newObject')}`, type, x, y: TOP, attributes: [], methods: [] }] })
    setSel({ type: 'node', id })
  }
  const remove = () => {
    if (!sel) return
    if (sel.type === 'node') commit({ ...d, nodes: d.nodes.filter((n) => n.id !== sel.id), edges: d.edges.filter((e) => e.from !== sel.id && e.to !== sel.id) })
    else commit({ ...d, edges: d.edges.filter((e) => e.id !== sel.id) })
    setSel(null)
  }
  const clickNode = (id: string) => {
    if (readOnly || !connect) { setSel({ type: 'node', id }); return }
    if (!connect.from) { setConnect({ ...connect, from: id }); return }
    const y = d.edges.length ? Math.max(...d.edges.map((e) => e.y ?? 0)) + STEP : TOP + HEAD_H + 50
    const e: DEdge = { id: newId('e'), from: connect.from, to: id, kind: connect.kind, fromMult: '', toMult: '', label: '', y }
    commit({ ...d, edges: [...d.edges, e] })
    setSel({ type: 'edge', id: e.id })
    setConnect(null)
  }
  // move a message one place up / down in time (swap with its neighbour)
  const shift = (id: string, dir: -1 | 1) => {
    const i = ordered.findIndex((e) => e.id === id), j = i + dir
    if (j < 0 || j >= ordered.length) return
    const a = ordered[i], b = ordered[j]
    commit({ ...d, edges: d.edges.map((e) => (e.id === a.id ? { ...e, y: b.y } : e.id === b.id ? { ...e, y: a.y } : e)) })
  }

  useEffect(() => {
    if (readOnly) return
    const key = (ev: KeyboardEvent) => {
      const tag = (ev.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if ((ev.key === 'Delete' || ev.key === 'Backspace') && sel) { ev.preventDefault(); remove() }
      if (ev.key === 'Escape') { setConnect(null); setSel(null) }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  })

  const down = (ev: React.PointerEvent, type: 'node' | 'edge', id: string, orig: number) => {
    ev.stopPropagation()
    if (type === 'edge') setSel({ type: 'edge', id })
    if (readOnly || connect) return
    setDrag({ type, id, start: type === 'node' ? ev.clientX : ev.clientY, orig, now: orig })
    ;(ev.target as Element).setPointerCapture?.(ev.pointerId)
  }
  const onMove = (ev: React.PointerEvent) => {
    if (drag) {
      const delta = ((drag.type === 'node' ? ev.clientX : ev.clientY) - drag.start) / view.k
      const v = Math.round((drag.orig + delta) / 5) * 5
      setDrag({ ...drag, now: drag.type === 'edge' ? Math.max(TOP + HEAD_H + 20, v) : v })
    } else if (pan.current) {
      setView((w) => ({ ...w, x: pan.current!.vx + ev.clientX - pan.current!.sx, y: pan.current!.vy + ev.clientY - pan.current!.sy }))
    }
  }
  const onUp = () => {
    if (drag && drag.now !== drag.orig) {
      if (drag.type === 'node') updNode(drag.id, { x: drag.now })
      else updEdge(drag.id, { y: drag.now })
    }
    setDrag(null)
    pan.current = null
  }
  const zoom = (f: number) => setView((v) => {
    const el = svg.current
    const cx = (el?.clientWidth ?? 600) / 2, cy = (el?.clientHeight ?? 400) / 2
    const k = Math.max(0.3, Math.min(2.5, v.k * f))
    return { k, x: cx - ((cx - v.x) / v.k) * k, y: cy - ((cy - v.y) / v.k) * k }
  })

  const selNode = sel?.type === 'node' ? d.nodes.find((n) => n.id === sel.id) : undefined
  const selEdge = sel?.type === 'edge' ? d.edges.find((e) => e.id === sel.id) : undefined
  const byId = new Map(d.nodes.map((n) => [n.id, n]))
  const kinds = KIND_SPEC.sequence.edges

  return (
    <div className="flex flex-col h-full min-h-0 bg-surface">
      <div className="flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-line-soft shrink-0">
        {!readOnly && <>
          <button className="btn-secondary btn-sm" onClick={() => addNode('lifeline')}><Plus size={14} /> {t('seq.object')}</button>
          <button className="btn-secondary btn-sm" onClick={() => addNode('actor')}><User size={14} /> {t('dg.ntype.actor')}</button>
          <span className="inline-flex items-center gap-1 rounded-md border border-line pl-2 h-8">
            <Cable size={14} className="text-ink-muted" />
            <select className="bg-transparent text-[13px] font-semibold h-full pr-1 focus:outline-none" aria-label={t('seq.message')}
              value={connect?.kind ?? ''} onChange={(e) => setConnect(e.target.value ? { kind: e.target.value as EdgeKind } : null)}>
              <option value="">{t('seq.addMessage')}</option>
              {kinds.map((k) => <option key={k} value={k}>{t(`dg.kind.${k}` as any)}</option>)}
            </select>
          </span>
          {sel && <button className="btn-ghost btn-sm text-bad hover:bg-bad-soft hover:text-bad" onClick={remove}><Trash2 size={14} /> {t('dg.delete')}</button>}
        </>}
        <span className="flex-1" />
        <button className="btn-ghost btn-sm px-2" onClick={() => zoom(1 / 1.2)} aria-label={t('dg.zoomOut')} title={t('dg.zoomOut')}><ZoomOut size={15} /></button>
        <span className="text-[12px] text-ink-muted tabular-nums w-10 text-center">{Math.round(view.k * 100)}%</span>
        <button className="btn-ghost btn-sm px-2" onClick={() => zoom(1.2)} aria-label={t('dg.zoomIn')} title={t('dg.zoomIn')}><ZoomIn size={15} /></button>
        <button className="btn-ghost btn-sm px-2" onClick={fit} aria-label={t('dg.fit')} title={t('dg.fit')}><Maximize size={14} /></button>
      </div>
      {connect && (
        <p className="px-3 py-1.5 text-[12.5px] bg-cobalt-soft text-cobalt font-medium shrink-0 flex items-center gap-2">
          {connect.from ? t('seq.pickReceiver') : t('seq.pickSender')} <span className="text-cobalt/70">({t(`dg.kind.${connect.kind}` as any)})</span>
          <button className="ml-auto" onClick={() => setConnect(null)} aria-label={t('dg.cancel')}><X size={14} /></button>
        </p>
      )}

      <div className="flex-1 min-h-0 flex">
        <svg ref={svg} className={`flex-1 min-w-0 h-full select-none touch-none bg-paper/40 ${connect ? 'cursor-crosshair' : 'cursor-grab'}`}
          role="application" aria-label={t('dg.canvas')}
          onPointerDown={(ev) => { if (ev.target === svg.current || (ev.target as Element).getAttribute('data-bg')) { setSel(null); pan.current = { sx: ev.clientX, sy: ev.clientY, vx: view.x, vy: view.y } } }}
          onPointerMove={onMove} onPointerUp={onUp} onPointerLeave={onUp}
          onWheel={(ev) => { if (ev.ctrlKey || ev.metaKey) { ev.preventDefault(); zoom(ev.deltaY < 0 ? 1.1 : 1 / 1.1) } else setView((v) => ({ ...v, x: v.x - ev.deltaX, y: v.y - ev.deltaY })) }}>
          <defs>
            <pattern id="sq-grid" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#D9DEE7" /></pattern>
            <marker id="sq-fill" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto" markerUnits="userSpaceOnUse">
              <path d="M1,1.5 L11,6 L1,10.5 z" fill={INK} /></marker>
            <marker id="sq-open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto" markerUnits="userSpaceOnUse">
              <path d="M1,1 L11,6 L1,11" fill="none" stroke={INK} strokeWidth="1.4" /></marker>
          </defs>
          <rect data-bg="1" x="-5000" y="-5000" width="10000" height="10000" fill="url(#sq-grid)" transform={`translate(${view.x % (24 * view.k)},${view.y % (24 * view.k)})`} />
          <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
            {/* lifelines */}
            {d.nodes.map((n) => {
              const x = nodeX(n), w = headW(n), cx = x + w / 2
              const on = (sel?.type === 'node' && sel.id === n.id) || connect?.from === n.id
              const stroke = on ? ACCENT : INK
              return (
                <g key={n.id} onPointerDown={(ev) => down(ev, 'node', n.id, n.x)} onClick={(ev) => { ev.stopPropagation(); clickNode(n.id) }}
                  className={readOnly ? '' : connect ? 'cursor-crosshair' : 'cursor-ew-resize'}>
                  <line x1={cx} x2={cx} y1={TOP + HEAD_H} y2={bottom} stroke="transparent" strokeWidth="16" />
                  <line x1={cx} x2={cx} y1={TOP + HEAD_H} y2={bottom} stroke={on ? ACCENT : MUTED} strokeWidth="1.4" strokeDasharray="6 5" />
                  {n.type === 'actor' ? (
                    <g stroke={stroke} strokeWidth={on ? 2.2 : 1.6} fill="none" transform={`translate(${cx},${TOP - 26})`}>
                      <circle cy={8} r={8} fill="#fff" /><line y1={16} y2={38} /><line x1={-14} x2={14} y1={24} y2={24} />
                      <line y1={38} x2={-12} y2={54} /><line y1={38} x2={12} y2={54} />
                      <text y={70} textAnchor="middle" fontSize="13" fontWeight="700" fill={INK} stroke="none">{n.name}</text>
                    </g>
                  ) : (
                    <>
                      <rect x={x} y={TOP} width={w} height={HEAD_H} rx={4} fill="#fff" stroke={stroke} strokeWidth={on ? 2.4 : 1.5}
                        filter="drop-shadow(0 1px 1.5px rgba(26,34,51,.12))" />
                      <text x={cx} y={TOP + HEAD_H / 2 + 5} textAnchor="middle" fontSize="13" fontWeight="700" fill={INK} textDecoration="underline">{n.name}</text>
                    </>
                  )}
                </g>
              )
            })}
            {/* messages */}
            {ordered.map((e, i) => {
              const a = byId.get(e.from), b = byId.get(e.to)
              if (!a || !b) return null
              const y = edgeY(e)
              const x1 = nodeX(a) + headW(a) / 2, x2 = nodeX(b) + headW(b) / 2
              const on = sel?.type === 'edge' && sel.id === e.id
              const self = a.id === b.id
              const dashed = e.kind === 'reply' || e.kind === 'create'
              const marker = e.kind === 'sync' ? 'url(#sq-fill)' : 'url(#sq-open)'
              const path = self ? `M${x1},${y} h44 v26 h-40` : `M${x1},${y} L${x2 + (x2 > x1 ? -2 : 2)},${y}`
              const text = (e.kind === 'create' ? '«create» ' : '') + e.label
              const lx = self ? x1 + 50 : (x1 + x2) / 2
              return (
                <g key={e.id} onPointerDown={(ev) => down(ev, 'edge', e.id, e.y ?? 0)} className={readOnly ? 'cursor-pointer' : 'cursor-ns-resize'}>
                  <path d={path} stroke="transparent" strokeWidth="14" fill="none" />
                  <path d={path} stroke={on ? ACCENT : INK} strokeWidth={on ? 2.4 : 1.5} fill="none" strokeDasharray={dashed ? '6 4' : undefined} markerEnd={marker} />
                  <text x={lx} y={self ? y + 17 : y - 7} textAnchor={self ? 'start' : 'middle'} fontSize="12" fill={INK}
                    stroke="#fff" strokeWidth={4} paintOrder="stroke" strokeLinejoin="round">
                    <tspan fill={MUTED} fontSize="10.5">{i + 1}. </tspan>{text}
                  </text>
                </g>
              )
            })}
          </g>
          {d.nodes.length === 0 && <text x="50%" y="45%" textAnchor="middle" fontSize="14" fill={MUTED}>{readOnly ? t('dg.emptyRo') : t('seq.empty')}</text>}
        </svg>

        {(selNode || selEdge) && !readOnly && (
          <aside className="w-[17rem] shrink-0 border-l border-line-soft overflow-y-auto p-3 space-y-3 text-[13px]" aria-label={t('dg.properties')}>
            {selNode && <>
              <div>
                <label className="field-label" htmlFor="sq-name">{t('dg.name')}</label>
                <input id="sq-name" className="input h-8" value={selNode.name} autoFocus onChange={(e) => updNode(selNode.id, { name: e.target.value })} />
                {selNode.type === 'lifeline' && <p className="mt-1 text-[11.5px] text-ink-muted">{t('seq.nameHint')}</p>}
              </div>
              <div>
                <label className="field-label" htmlFor="sq-type">{t('dg.type')}</label>
                <select id="sq-type" className="input h-8" value={selNode.type} onChange={(e) => updNode(selNode.id, { type: e.target.value as NodeType })}>
                  {KIND_SPEC.sequence.nodes.map((x) => <option key={x} value={x}>{t(`dg.ntype.${x}` as any)}</option>)}
                </select>
              </div>
            </>}
            {selEdge && <>
              <p className="font-semibold">{byId.get(selEdge.from)?.name} <span className="text-ink-muted">→</span> {byId.get(selEdge.to)?.name}</p>
              <div>
                <label className="field-label" htmlFor="sq-kind">{t('seq.message')}</label>
                <select id="sq-kind" className="input h-8" value={selEdge.kind} onChange={(e) => updEdge(selEdge.id, { kind: e.target.value as EdgeKind })}>
                  {kinds.map((k) => <option key={k} value={k}>{t(`dg.kind.${k}` as any)}</option>)}
                </select>
                <p className="mt-1 text-[11.5px] text-ink-muted">{t(`dg.kindHint.${selEdge.kind}` as any)}</p>
              </div>
              <div>
                <label className="field-label" htmlFor="sq-label">{selEdge.kind === 'reply' ? t('seq.returns') : t('seq.operation')}</label>
                <input id="sq-label" className="input h-8 font-mono text-[12.5px]" value={selEdge.label} autoFocus
                  placeholder={selEdge.kind === 'reply' ? 'корисник' : 'најди(id)'} onChange={(e) => updEdge(selEdge.id, { label: e.target.value })} />
              </div>
              <div>
                <p className="field-label">{t('seq.order', { n: ordered.findIndex((x) => x.id === selEdge.id) + 1, total: ordered.length })}</p>
                <div className="flex gap-1.5">
                  <button className="btn-secondary btn-sm" onClick={() => shift(selEdge.id, -1)}><ArrowUp size={13} /> {t('seq.earlier')}</button>
                  <button className="btn-secondary btn-sm" onClick={() => shift(selEdge.id, 1)}><ArrowDown size={13} /> {t('seq.later')}</button>
                </div>
              </div>
              <button className="btn-ghost btn-sm" onClick={() => updEdge(selEdge.id, { from: selEdge.to, to: selEdge.from })}>
                <ArrowLeftRight size={13} /> {t('dg.swap')}
              </button>
            </>}
          </aside>
        )}
      </div>
    </div>
  )
}
