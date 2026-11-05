import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeftRight, Cable, Key, Link2, Maximize, Minus, Plus, Trash2, X, ZoomIn, ZoomOut } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import SequenceEditor from './SequenceEditor'
import {
  borderPoint, CONTAINERS, DAttr, DEdge, Diagram, DiagramKind, displayName, DNode, dumpDiagram, EdgeKind, hasMethods,
  KIND_SPEC, memberMode, memberText, methodText, newId, nodeSize, NodeType, parseDiagram, PSEUDO, ROW, Size, stereotype,
} from '../lib/diagram'

type Sel = { type: 'node' | 'edge'; id: string } | null
type Drag = { id: string; dx: number; dy: number; x: number; y: number; ox: number; oy: number; inside: string[] }
type Resize = { id: string; sx: number; sy: number; w0: number; h0: number; w: number; h: number }
const INK = '#1A2233', MUTED = '#6B7488', ACCENT = '#2747C9', SOFT = '#F1F3F7', MONO = "'JetBrains Mono', ui-monospace, monospace"

/** How each kind of line is drawn: dashed or not, the arrow heads, and a «stereotype» written on it. */
const EDGE_STYLE: Record<EdgeKind, { dash?: boolean; end?: string; start?: string; stereo?: string }> = {
  association: {}, relationship: {},
  aggregation: { start: 'dg-dia' }, composition: { start: 'dg-dia-f' },
  inheritance: { end: 'dg-tri' }, realization: { dash: true, end: 'dg-tri' }, dependency: { dash: true, end: 'dg-open' },
  include: { dash: true, end: 'dg-open', stereo: '«include»' }, extend: { dash: true, end: 'dg-open', stereo: '«extend»' },
  import: { dash: true, end: 'dg-open', stereo: '«import»' }, merge: { dash: true, end: 'dg-open', stereo: '«merge»' },
  deploy: { dash: true, end: 'dg-open', stereo: '«deploy»' },
  transition: { end: 'dg-arrow' }, flow: { end: 'dg-arrow' }, foreign_key: { end: 'dg-open' },
  // (sequence diagrams have their own editor; these are only for completeness)
  sync: { end: 'dg-arrow' }, async: { end: 'dg-open' }, reply: { dash: true, end: 'dg-open' }, create: { dash: true, end: 'dg-open', stereo: '«create»' },
}
const SELF_LOOPS = new Set<EdgeKind>(['association', 'transition', 'flow', 'relationship'])
const CONTAINER_SIZE: Partial<Record<NodeType, [number, number]>> = {
  system: [360, 300], swimlane: [260, 420], package: [240, 140], node: [220, 120], device: [220, 120],
}

/**
 * Diagram editor for every diagram kind (lib/diagram.ts KIND_SPEC): boxes, use cases, actors, states, actions,
 * decisions, fork bars, components, packages, nodes, tables… and the lines between them. Drag things around (a
 * system / swimlane / package / node box takes what is inside it along), drag the corner of a selected box to resize
 * it, drag the background to move around, select something to edit it on the right. Kept as JSON in `code`.
 */
export default function DiagramEditor(props: { code: string; onChange?: (v: string) => void; kind: DiagramKind; readOnly?: boolean }) {
  // a sequence diagram has its own editor: lifelines and messages ordered in time
  return props.kind === 'sequence' ? <SequenceEditor code={props.code} onChange={props.onChange} readOnly={props.readOnly} /> : <GraphEditor {...props} />
}

function GraphEditor({ code, onChange, kind, readOnly = false }: {
  code: string; onChange?: (v: string) => void; kind: DiagramKind; readOnly?: boolean
}) {
  const { t } = useLanguage()
  const spec = KIND_SPEC[kind] ?? KIND_SPEC.uml
  const d = useMemo(() => parseDiagram(code, kind), [code, kind])
  const [sel, setSel] = useState<Sel>(null)
  const [connect, setConnect] = useState<{ kind: EdgeKind; from?: string } | null>(null)
  const [view, setView] = useState({ x: 0, y: 0, k: 1 })
  const [drag, setDrag] = useState<Drag | null>(null)
  const [resize, setResize] = useState<Resize | null>(null)
  const pan = useRef<{ sx: number; sy: number; vx: number; vy: number } | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const fitted = useRef(false)

  const commit = (next: Diagram) => onChange?.(dumpDiagram(next))
  const pos = (n: DNode) => {
    if (!drag) return { x: n.x, y: n.y }
    if (drag.id === n.id) return { x: drag.x, y: drag.y }
    if (drag.inside.includes(n.id)) return { x: n.x + drag.x - drag.ox, y: n.y + drag.y - drag.oy }
    return { x: n.x, y: n.y }
  }
  const sizes = useMemo(() => new Map<string, Size>(d.nodes.map((n) => [n.id,
    nodeSize(kind, resize && resize.id === n.id ? { ...n, w: resize.w, h: resize.h } : n)])), [d, kind, resize])
  // boxes that hold others are drawn first (biggest at the back)
  const order = useMemo(() => [...d.nodes].sort((a, b) => {
    const ca = CONTAINERS.has(a.type), cb = CONTAINERS.has(b.type)
    if (ca !== cb) return ca ? -1 : 1
    if (!ca) return 0
    const sa = sizes.get(a.id)!, sb = sizes.get(b.id)!
    return sb.w * sb.h - sa.w * sa.h
  }), [d, sizes])

  // show the whole diagram the first time (e.g. a teacher's diagram or one read from a picture)
  const fit = () => {
    const el = svg.current
    if (!el || d.nodes.length === 0) { setView({ x: 0, y: 0, k: 1 }); return }
    const xs = d.nodes.flatMap((n) => [n.x, n.x + (sizes.get(n.id)?.w ?? 0)])
    const ys = d.nodes.flatMap((n) => [n.y, n.y + (sizes.get(n.id)?.h ?? 0)])
    const minX = Math.min(...xs) - 30, minY = Math.min(...ys) - 30, maxX = Math.max(...xs) + 30, maxY = Math.max(...ys) + 30
    const k = Math.min(1.2, el.clientWidth / (maxX - minX), el.clientHeight / (maxY - minY))
    setView({ k, x: -minX * k + (el.clientWidth - (maxX - minX) * k) / 2, y: -minY * k + 10 })
  }
  useEffect(() => { if (!fitted.current && d.nodes.length) { fitted.current = true; fit() } }) // eslint-disable-line react-hooks/exhaustive-deps

  const toWorld = (cx: number, cy: number) => {
    const r = svg.current!.getBoundingClientRect()
    return { x: (cx - r.left - view.x) / view.k, y: (cy - r.top - view.y) / view.k }
  }

  // ---- editing ---------------------------------------------------------------------------------------------
  const updNode = (id: string, patch: Partial<DNode>) => commit({ ...d, nodes: d.nodes.map((n) => (n.id === id ? { ...n, ...patch } : n)) })
  const updEdge = (id: string, patch: Partial<DEdge>) => commit({ ...d, edges: d.edges.map((e) => (e.id === id ? { ...e, ...patch } : e)) })
  const defaultName = (type: NodeType) => PSEUDO.has(type) ? ''
    : kind === 'uml' ? t('dg.newClass') : kind === 'er' ? t('dg.newEntity') : t(`dg.ntype.${type}` as any)
  const addNode = (type: NodeType) => {
    const el = svg.current
    const c = el ? toWorld(el.getBoundingClientRect().left + el.clientWidth / 2 - 80, el.getBoundingClientRect().top + 60) : { x: 40, y: 40 }
    const id = newId('n')
    const n: DNode = { id, name: defaultName(type), type, x: Math.round(c.x + (d.nodes.length % 4) * 24), y: Math.round(c.y + (d.nodes.length % 4) * 24),
      attributes: [], methods: [] }
    const cs = CONTAINER_SIZE[type]
    if (cs) { n.w = cs[0]; n.h = cs[1] }
    commit({ ...d, nodes: [...d.nodes, n] })
    setSel({ type: 'node', id })
  }
  const remove = () => {
    if (!sel) return
    if (sel.type === 'node') commit({ ...d, nodes: d.nodes.filter((n) => n.id !== sel.id), edges: d.edges.filter((e) => e.from !== sel.id && e.to !== sel.id) })
    else commit({ ...d, edges: d.edges.filter((e) => e.id !== sel.id) })
    setSel(null)
  }
  const clickNode = (id: string) => {
    if (readOnly) { setSel({ type: 'node', id }); return }
    if (connect) {
      if (!connect.from) { setConnect({ ...connect, from: id }); return }
      if (connect.from !== id || SELF_LOOPS.has(connect.kind)) {
        const e: DEdge = { id: newId('e'), from: connect.from, to: id, kind: connect.kind, fromMult: '', toMult: '', label: '' }
        commit({ ...d, edges: [...d.edges, e] })
        setSel({ type: 'edge', id: e.id })
      }
      setConnect(null)
      return
    }
    setSel({ type: 'node', id })
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

  // ---- pointer: drag a box (with what is inside it), resize a box, or move around ------------------------------
  const insideOf = (c: DNode) => {
    if (!CONTAINERS.has(c.type)) return []
    const sc = sizes.get(c.id)!
    return d.nodes.filter((n) => {
      if (n.id === c.id) return false
      const s = sizes.get(n.id)!
      const cx = n.x + s.w / 2, cy = n.y + s.h / 2
      return cx > c.x && cx < c.x + sc.w && cy > c.y && cy < c.y + sc.h && s.w * s.h < sc.w * sc.h
    }).map((n) => n.id)
  }
  const onNodeDown = (ev: React.PointerEvent, n: DNode) => {
    ev.stopPropagation()
    if (readOnly || connect) return
    const w = toWorld(ev.clientX, ev.clientY)
    setDrag({ id: n.id, dx: w.x - n.x, dy: w.y - n.y, x: n.x, y: n.y, ox: n.x, oy: n.y, inside: insideOf(n) })
    ;(ev.target as Element).setPointerCapture?.(ev.pointerId)
  }
  const onResizeDown = (ev: React.PointerEvent, n: DNode) => {
    ev.stopPropagation()
    const s = sizes.get(n.id)!
    setResize({ id: n.id, sx: ev.clientX, sy: ev.clientY, w0: s.w, h0: s.h, w: s.w, h: s.h })
    ;(ev.target as Element).setPointerCapture?.(ev.pointerId)
  }
  const onMove = (ev: React.PointerEvent) => {
    if (resize) {
      setResize({ ...resize, w: Math.max(120, Math.round(resize.w0 + (ev.clientX - resize.sx) / view.k)), h: Math.max(80, Math.round(resize.h0 + (ev.clientY - resize.sy) / view.k)) })
    } else if (drag) {
      const w = toWorld(ev.clientX, ev.clientY)
      setDrag({ ...drag, x: Math.round(w.x - drag.dx), y: Math.round(w.y - drag.dy) })
    } else if (pan.current) {
      setView((v) => ({ ...v, x: pan.current!.vx + ev.clientX - pan.current!.sx, y: pan.current!.vy + ev.clientY - pan.current!.sy }))
    }
  }
  const onUp = () => {
    if (resize) {
      if (resize.w !== resize.w0 || resize.h !== resize.h0) updNode(resize.id, { w: resize.w, h: resize.h })
      setResize(null)
    }
    if (drag) {
      const ddx = drag.x - drag.ox, ddy = drag.y - drag.oy
      if (ddx || ddy) {
        commit({ ...d, nodes: d.nodes.map((n) => n.id === drag.id ? { ...n, x: drag.x, y: drag.y }
          : drag.inside.includes(n.id) ? { ...n, x: n.x + ddx, y: n.y + ddy } : n) })
      }
      setDrag(null)
    }
    pan.current = null
  }
  const zoom = (f: number) => setView((v) => {
    const el = svg.current
    const cx = (el?.clientWidth ?? 600) / 2, cy = (el?.clientHeight ?? 400) / 2
    const k = Math.max(0.25, Math.min(2.5, v.k * f))
    return { k, x: cx - ((cx - v.x) / v.k) * k, y: cy - ((cy - v.y) / v.k) * k }
  })

  const selNode = sel?.type === 'node' ? d.nodes.find((n) => n.id === sel.id) : undefined
  const selEdge = sel?.type === 'edge' ? d.edges.find((e) => e.id === sel.id) : undefined
  const edgeKinds = spec.edges
  const [mainType, ...otherTypes] = spec.nodes
  const addLabel = kind === 'uml' ? t('dg.addClass') : kind === 'er' ? t('dg.addEntity') : t(`dg.ntype.${mainType}` as any)

  return (
    <div className="flex flex-col h-full min-h-0 bg-surface">
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-line-soft shrink-0">
        {!readOnly && <>
          <button className="btn-secondary btn-sm" onClick={() => addNode(mainType)}><Plus size={14} /> {addLabel}</button>
          {otherTypes.length > 0 && (
            <select className="input h-8 w-auto text-[13px] font-semibold py-0" aria-label={t('dg.addOther')} value=""
              onChange={(e) => { if (e.target.value) addNode(e.target.value as NodeType) }}>
              <option value="">{t('dg.addOther')}</option>
              {otherTypes.map((x) => <option key={x} value={x}>{t(`dg.ntype.${x}` as any)}</option>)}
            </select>
          )}
          <span className="inline-flex items-center gap-1 rounded-md border border-line pl-2 h-8">
            <Cable size={14} className="text-ink-muted" />
            {edgeKinds.length > 1 ? (
              <select className="bg-transparent text-[13px] font-semibold h-full pr-1 focus:outline-none" aria-label={t('dg.relationKind')}
                value={connect?.kind ?? ''} onChange={(e) => setConnect(e.target.value ? { kind: e.target.value as EdgeKind } : null)}>
                <option value="">{t('dg.connect')}</option>
                {edgeKinds.map((k) => <option key={k} value={k}>{t(`dg.kind.${k}` as any)}</option>)}
              </select>
            ) : (
              <button className={`text-[13px] font-semibold pr-2 h-full ${connect ? 'text-cobalt' : ''}`}
                onClick={() => setConnect(connect ? null : { kind: edgeKinds[0] })}>{t('dg.connect')}</button>
            )}
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
          {connect.from ? t('dg.pickTarget') : t('dg.pickSource')} <span className="text-cobalt/70">({t(`dg.kind.${connect.kind}` as any)})</span>
          <button className="ml-auto" onClick={() => setConnect(null)} aria-label={t('dg.cancel')}><X size={14} /></button>
        </p>
      )}

      <div className="flex-1 min-h-0 flex">
        {/* canvas */}
        <svg ref={svg} className={`flex-1 min-w-0 h-full select-none touch-none bg-paper/40 ${connect ? 'cursor-crosshair' : pan.current ? 'cursor-grabbing' : 'cursor-grab'}`}
          role="application" aria-label={t('dg.canvas')}
          onPointerDown={(ev) => { if (ev.target === svg.current || (ev.target as Element).getAttribute('data-bg')) { setSel(null); pan.current = { sx: ev.clientX, sy: ev.clientY, vx: view.x, vy: view.y } } }}
          onPointerMove={onMove} onPointerUp={onUp} onPointerLeave={onUp}
          onWheel={(ev) => { if (ev.ctrlKey || ev.metaKey) { ev.preventDefault(); zoom(ev.deltaY < 0 ? 1.1 : 1 / 1.1) } else setView((v) => ({ ...v, x: v.x - ev.deltaX, y: v.y - ev.deltaY })) }}>
          <defs>
            <pattern id="dg-grid" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#D9DEE7" /></pattern>
            <marker id="dg-tri" viewBox="0 0 14 14" refX="13" refY="7" markerWidth="14" markerHeight="14" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
              <path d="M1,1 L13,7 L1,13 z" fill="#fff" stroke={INK} strokeWidth="1.4" /></marker>
            <marker id="dg-open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
              <path d="M1,1 L11,6 L1,11" fill="none" stroke={INK} strokeWidth="1.4" /></marker>
            <marker id="dg-arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
              <path d="M1,1.5 L11,6 L1,10.5 z" fill={INK} /></marker>
            <marker id="dg-dia" viewBox="0 0 20 12" refX="1" refY="6" markerWidth="20" markerHeight="12" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
              <path d="M1,6 L10,1 L19,6 L10,11 z" fill="#fff" stroke={INK} strokeWidth="1.4" /></marker>
            <marker id="dg-dia-f" viewBox="0 0 20 12" refX="1" refY="6" markerWidth="20" markerHeight="12" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
              <path d="M1,6 L10,1 L19,6 L10,11 z" fill={INK} stroke={INK} strokeWidth="1.4" /></marker>
          </defs>
          <rect data-bg="1" x="-5000" y="-5000" width="10000" height="10000" fill="url(#dg-grid)" transform={`translate(${view.x % (24 * view.k)},${view.y % (24 * view.k)})`} />
          <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
            {order.filter((n) => CONTAINERS.has(n.type)).map((n) => renderNode(n))}
            {d.edges.map((e) => {
              const a = d.nodes.find((n) => n.id === e.from)!, b = d.nodes.find((n) => n.id === e.to)!
              const pa = pos(a), pb = pos(b)
              const ga = anchorBox(a, pa, sizes.get(a.id)!), gb = anchorBox(b, pb, sizes.get(b.id)!)
              const ca = { x: ga.x + ga.w / 2, y: ga.y + ga.h / 2 }, cb = { x: gb.x + gb.w / 2, y: gb.y + gb.h / 2 }
              // two lines between the same boxes (e.g. there and back) are drawn side by side, not on top of each other
              const twins = d.edges.filter((x) => (x.from === e.from && x.to === e.to) || (x.from === e.to && x.to === e.from))
              const shift = a.id === b.id || twins.length < 2 ? 0 : (twins.indexOf(e) - (twins.length - 1) / 2) * 18
              const [lo, hi] = e.from < e.to ? [ca, cb] : [cb, ca]
              const dl = Math.hypot(hi.x - lo.x, hi.y - lo.y) || 1
              const nx = -(hi.y - lo.y) / dl * shift, ny = (hi.x - lo.x) / dl * shift
              let p1 = borderPoint(ga.x, ga.y, ga.w, ga.h, cb.x + nx, cb.y + ny, ga.shape, nx, ny)
              let p2 = borderPoint(gb.x, gb.y, gb.w, gb.h, ca.x + nx, ca.y + ny, gb.shape, nx, ny)
              if (a.id === b.id) { p1 = { x: ga.x + ga.w, y: ga.y + Math.min(20, ga.h / 2) }; p2 = { x: ga.x + ga.w - Math.min(30, ga.w / 2), y: ga.y } }
              let st = EDGE_STYLE[e.kind] ?? {}
              // a component realizes a provided interface ("lollipop"): drawn as a plain line
              if (kind === 'component' && e.kind === 'realization' && b.type === 'interface') st = {}
              const len = Math.hypot(p2.x - p1.x, p2.y - p1.y) || 1
              const ux = (p2.x - p1.x) / len, uy = (p2.y - p1.y) / len
              const mid = a.id === b.id ? { x: ga.x + ga.w + 18, y: ga.y - 18 } : { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 }
              const lab = (p: { x: number; y: number }, s: number) => ({ x: p.x + ux * 22 * s - uy * 11, y: p.y + uy * 22 * s + ux * 11 })
              const m1 = lab(p1, 1), m2 = lab(p2, -1)
              const selected = sel?.type === 'edge' && sel.id === e.id
              const path = a.id === b.id ? `M${p1.x},${p1.y} C${p1.x + 50},${p1.y} ${p2.x},${p2.y - 50} ${p2.x},${p2.y}` : `M${p1.x},${p1.y} L${p2.x},${p2.y}`
              const text = [st.stereo, e.label].filter(Boolean).join(' ')
              const halo = { stroke: '#fff', strokeWidth: 4, paintOrder: 'stroke' as const, strokeLinejoin: 'round' as const }
              return (
                <g key={e.id} onPointerDown={(ev) => { ev.stopPropagation(); setSel({ type: 'edge', id: e.id }) }} className="cursor-pointer">
                  <path d={path} stroke="transparent" strokeWidth="14" fill="none" />
                  <path d={path} stroke={selected ? ACCENT : INK} strokeWidth={selected ? 2.4 : 1.5} fill="none"
                    strokeDasharray={st.dash ? '6 4' : undefined} markerEnd={st.end ? `url(#${st.end})` : undefined} markerStart={st.start ? `url(#${st.start})` : undefined} />
                  {spec.mults && e.fromMult && <text x={m1.x} y={m1.y} fontSize="12" fill={INK} textAnchor="middle" dominantBaseline="middle" {...halo}>{e.fromMult}</text>}
                  {spec.mults && e.toMult && <text x={m2.x} y={m2.y} fontSize="12" fill={INK} textAnchor="middle" dominantBaseline="middle" {...halo}>{e.toMult}</text>}
                  {e.kind === 'relationship' ? (
                    <g transform={`translate(${mid.x},${mid.y})`}>
                      <path d={`M${-Math.max(34, e.label.length * 4 + 16)},0 L0,-17 L${Math.max(34, e.label.length * 4 + 16)},0 L0,17 z`} fill="#fff" stroke={selected ? ACCENT : INK} strokeWidth="1.4" />
                      <text fontSize="11.5" fill={INK} textAnchor="middle" dominantBaseline="middle">{e.label}</text>
                    </g>
                  ) : text ? (() => {
                    let qx = -uy, qy = ux
                    if (qy > 0.01 || (Math.abs(qy) <= 0.01 && qx < 0)) { qx = -qx; qy = -qy }
                    const side = Math.abs(qx) > 0.7
                    return <text x={mid.x + qx * (side ? 7 : 8)} y={mid.y + qy * 8 + (side ? 4 : -1)} fontSize="11.5"
                      fill={e.label && !st.stereo && !spec.flow ? MUTED : INK} fontStyle={spec.flow || st.stereo ? undefined : 'italic'}
                      textAnchor={side ? 'start' : 'middle'} {...halo}>{text}</text>
                  })() : null}
                </g>
              )
            })}
            {order.filter((n) => !CONTAINERS.has(n.type)).map((n) => renderNode(n))}
          </g>
          {d.nodes.length === 0 && (
            <text x="50%" y="45%" textAnchor="middle" fontSize="14" fill={MUTED}>{readOnly ? t('dg.emptyRo') : t('dg.empty')}</text>
          )}
        </svg>

        {/* properties */}
        {(selNode || selEdge) && !readOnly && (
          <aside className="w-[17rem] shrink-0 border-l border-line-soft overflow-y-auto p-3 space-y-3 text-[13px]" aria-label={t('dg.properties')}>
            {selNode && <NodePanel key={selNode.id} n={selNode} kind={kind} size={sizes.get(selNode.id)!} onChange={(p) => updNode(selNode.id, p)} />}
            {selEdge && <EdgePanel e={selEdge} d={d} kinds={edgeKinds} onChange={(p) => updEdge(selEdge.id, p)} />}
          </aside>
        )}
      </div>
    </div>
  )

  // ---- one box ---------------------------------------------------------------------------------------------------
  function renderNode(n: DNode) {
    const size = sizes.get(n.id)!
    const { w, h } = size
    const p = pos(n)
    const selected = sel?.type === 'node' && sel.id === n.id
    const hot = selected || connect?.from === n.id
    const stroke = hot ? ACCENT : INK, sw = hot ? 2.4 : 1.5
    const container = CONTAINERS.has(n.type)
    return (
      <g key={n.id} transform={`translate(${p.x},${p.y})`} onPointerDown={(ev) => onNodeDown(ev, n)} data-node={n.type}
        onClick={(ev) => { ev.stopPropagation(); clickNode(n.id) }} className={readOnly ? '' : connect ? 'cursor-crosshair' : 'cursor-move'}>
        <NodeShape n={n} kind={kind} size={size} stroke={stroke} sw={sw} />
        {container && selected && !readOnly && (
          <rect x={w - 7} y={h - 7} width={12} height={12} rx={2} fill="#fff" stroke={ACCENT} strokeWidth="1.6" className="cursor-nwse-resize"
            onPointerDown={(ev) => onResizeDown(ev, n)} onClick={(ev) => ev.stopPropagation()}>
            <title>{t('dg.resize')}</title>
          </rect>
        )}
      </g>
    )
  }
}

/** The part of a node lines attach to: the whole box, or just the circle of a provided interface ("lollipop"). */
function anchorBox(n: DNode, p: { x: number; y: number }, s: Size): { x: number; y: number; w: number; h: number; shape: Size['shape'] } {
  if (n.type === 'interface' && s.head === -1) return { x: p.x + 1, y: p.y + 1, w: 24, h: 24, shape: 'circle' }
  return { x: p.x, y: p.y, w: s.w, h: s.h, shape: s.shape }
}

/** The drawing of one node, in its own coordinates (0,0 = top left). */
function NodeShape({ n, kind, size, stroke, sw }: { n: DNode; kind: DiagramKind; size: Size; stroke: string; sw: number }) {
  const { w, h, head } = size
  const shadow = 'drop-shadow(0 1px 1.5px rgba(26,34,51,.12))'
  const name = (y: number, extra: React.SVGProps<SVGTextElement> = {}) => (
    <text x={w / 2} y={y} fontSize="13.5" fontWeight="700" fill={INK} textAnchor="middle" {...extra}>{n.name}</text>
  )
  const lines = (top: number, x = 10) => n.attributes.map((a, i) => (
    <text key={i} x={x} y={top + i * ROW + 13} fontSize="12" fill={INK}>{a.name}</text>
  ))
  switch (n.type) {
    case 'actor':
      return <>
        <rect width={w} height={h} fill="transparent" />
        <g stroke={stroke} strokeWidth={sw} fill="none" transform={`translate(${w / 2},0)`}>
          <circle cy={12} r={11} fill="#fff" /><line y1={23} y2={56} /><line x1={-20} x2={20} y1={34} y2={34} />
          <line y1={56} x2={-17} y2={80} /><line y1={56} x2={17} y2={80} />
        </g>
        {name(98, { fontSize: 13 })}
      </>
    case 'usecase':
      return <>
        <ellipse cx={w / 2} cy={h / 2} rx={w / 2} ry={h / 2} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        {name(h / 2 + 5, { fontWeight: 600, fontSize: 13 })}
      </>
    case 'initial':
      return <circle cx={w / 2} cy={h / 2} r={w / 2} fill={stroke} />
    case 'final':
      return <><circle cx={w / 2} cy={h / 2} r={w / 2 - 1} fill="#fff" stroke={stroke} strokeWidth={sw} /><circle cx={w / 2} cy={h / 2} r={w / 2 - 6} fill={stroke} /></>
    case 'flow_final': {
      const r = w / 2 - 1, q = r * 0.7
      return <g stroke={stroke} strokeWidth={sw}>
        <circle cx={w / 2} cy={h / 2} r={r} fill="#fff" />
        <line x1={w / 2 - q} y1={h / 2 - q} x2={w / 2 + q} y2={h / 2 + q} /><line x1={w / 2 + q} y1={h / 2 - q} x2={w / 2 - q} y2={h / 2 + q} />
      </g>
    }
    case 'decision': case 'merge': case 'choice':
      return <>
        <path d={`M${w / 2},0 L${w},${h / 2} L${w / 2},${h} L0,${h / 2} z`} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        {n.name && <text x={w / 2} y={h / 2 + 4} fontSize="11.5" fontWeight="600" fill={INK} textAnchor="middle">{n.name}</text>}
      </>
    case 'fork': case 'join':
      return <><rect y={-4} width={w} height={h + 8} fill="transparent" /><rect width={w} height={h} rx={2} fill={stroke} /></>
    case 'action':
      return <>
        <rect width={w} height={h} rx={16} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        {name(h / 2 + 5, { fontWeight: 600, fontSize: 13 })}
      </>
    case 'state':
      return <>
        <rect width={w} height={h} rx={14} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        {name(n.attributes.length ? 24 : h / 2 + 5)}
        {n.attributes.length > 0 && <><line x1={0} x2={w} y1={head} y2={head} stroke={INK} strokeWidth="1" />{lines(head + 4, 12)}</>}
      </>
    case 'artifact':
      return <>
        <rect width={w} height={h} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        <path d={`M${w - 26},8 h10 l6,6 v14 h-16 z M${w - 16},8 v6 h6`} fill="none" stroke={MUTED} strokeWidth="1.2" />
        <text x={w / 2} y={20} fontSize="11" fill={MUTED} textAnchor="middle">«artifact»</text>
        {name(40, { fontSize: 13 })}
      </>
    case 'system':
      return <>
        <rect width={w} height={h} fill="#fff" fillOpacity={0.7} stroke={stroke} strokeWidth={sw} />
        {name(22)}
      </>
    case 'swimlane':
      return <>
        <rect width={w} height={h} fill="#FAFBFD" stroke={stroke} strokeWidth={sw} />
        <rect width={w} height={head} fill={SOFT} stroke={stroke} strokeWidth={sw} />
        {name(head - 10)}
      </>
    case 'package': {
      const tab = Math.min(w - 20, Math.max(80, n.name.length * 7.6 + 24))
      return <>
        <rect width={tab} height={24} fill={SOFT} stroke={stroke} strokeWidth={sw} />
        <rect y={23} width={w} height={h - 23} fill="#fff" fillOpacity={0.85} stroke={stroke} strokeWidth={sw} filter={shadow} />
        <text x={12} y={17} fontSize="13" fontWeight="700" fill={INK}>{n.name}</text>
        {lines(head)}
      </>
    }
    case 'node': case 'device': {
      const dd = 12
      return <>
        <path d={`M0,${dd} L${dd},0 L${w},0 L${w - dd},${dd} z`} fill="#E3E7EF" stroke={stroke} strokeWidth={sw} strokeLinejoin="round" />
        <path d={`M${w - dd},${dd} L${w},0 L${w},${h - dd} L${w - dd},${h} z`} fill="#D3D9E4" stroke={stroke} strokeWidth={sw} strokeLinejoin="round" />
        <rect y={dd} width={w - dd} height={h - dd} fill="#F7F8FB" stroke={stroke} strokeWidth={sw} />
        {n.type === 'device' && <text x={(w - dd) / 2} y={dd + 15} fontSize="11" fill={MUTED} textAnchor="middle">«device»</text>}
        <text x={(w - dd) / 2} y={dd + (n.type === 'device' ? 31 : 20)} fontSize="13.5" fontWeight="700" fill={INK} textAnchor="middle">{n.name}</text>
        {lines(head + 2, 12)}
      </>
    }
    case 'component':
      return <>
        <rect width={w} height={h} rx={2} fill="#fff" stroke={stroke} strokeWidth={sw} filter={shadow} />
        <g transform={`translate(${w - 28},9)`} fill="#fff" stroke={MUTED} strokeWidth="1.2">
          <rect x={4} width={16} height={20} /><rect y={4} width={8} height={4} /><rect y={12} width={8} height={4} />
        </g>
        <text x={w / 2} y={20} fontSize="11" fill={MUTED} textAnchor="middle">«component»</text>
        {name(40)}
        {n.attributes.length > 0 && <><line x1={0} x2={w} y1={head} y2={head} stroke={INK} strokeWidth="1" />{lines(head + 4)}</>}
      </>
    case 'interface':
      if (kind === 'component') return <>
        <rect width={w} height={h} fill="transparent" />
        <circle cx={13} cy={13} r={11} fill="#fff" stroke={stroke} strokeWidth={sw} />
        <text x={30} y={17.5} fontSize="12.5" fontWeight="600" fill={INK} {...{ stroke: '#fff', strokeWidth: 4, paintOrder: 'stroke' }}>{n.name}</text>
      </>
  }
  return <ClassBox n={n} kind={kind} size={size} stroke={stroke} sw={sw} />
}

/** UML class / interface / enum, ER entity, table: name, then attributes (columns), then methods. */
function ClassBox({ n, kind, size, stroke, sw }: { n: DNode; kind: DiagramKind; size: Size; stroke: string; sw: number }) {
  const { w, h, head } = size
  const st = stereotype(n, kind)
  const attrTop = head + 4
  const methTop = attrTop + Math.max(1, n.attributes.length) * ROW + 8
  const db = kind === 'er' || kind === 'relational'
  const keys = kind === 'relational' && n.attributes.some((a) => a.pk || a.fk)
  return <>
    <rect width={w} height={h} rx={db ? 4 : 2} fill="#fff" stroke={stroke} strokeWidth={sw} filter="drop-shadow(0 1px 1.5px rgba(26,34,51,.12))" />
    {n.type === 'weak' && <rect x={4} y={4} width={w - 8} height={h - 8} rx={3} fill="none" stroke={INK} strokeWidth="1.2" />}
    <rect width={w} height={head} rx={db ? 4 : 2} fill={db ? '#E8EDFC' : SOFT} />
    <line x1={0} x2={w} y1={head} y2={head} stroke={INK} strokeWidth="1.2" />
    {st && <text x={w / 2} y={14} fontSize="11" fill={MUTED} textAnchor="middle">{st}</text>}
    <text x={w / 2} y={head - 10} fontSize="13.5" fontWeight="700" fill={INK} textAnchor="middle"
      fontStyle={n.type === 'abstract' ? 'italic' : undefined}>{n.name}</text>
    {n.attributes.map((a, i) => (
      <g key={i}>
        {keys && (a.pk || a.fk) && (
          <text x={8} y={attrTop + i * ROW + 13} fontSize="9.5" fontWeight="700" fill={a.pk ? '#8C5A00' : ACCENT}>{a.pk && a.fk ? 'PK FK' : a.pk ? 'PK' : 'FK'}</text>
        )}
        <text x={keys ? (n.attributes.some((x) => x.pk && x.fk) ? 44 : 30) : 10} y={attrTop + i * ROW + 13} fontSize="12" fill={INK} fontFamily={MONO}
          textDecoration={db && a.pk ? 'underline' : undefined} fontWeight={a.pk ? 700 : 400} fontStyle={a.fk && !a.pk ? 'italic' : undefined}>
          {kind === 'er' && a.pk ? '🔑 ' : ''}{memberText(kind, a)}
        </text>
      </g>
    ))}
    {hasMethods(kind, n.type) && <>
      <line x1={0} x2={w} y1={methTop - 4} y2={methTop - 4} stroke={INK} strokeWidth="1" />
      {n.methods.map((m, i) => (
        <text key={i} x={10} y={methTop + i * ROW + 13} fontSize="12" fill={INK} fontFamily={MONO}>{methodText(m)}</text>
      ))}
    </>}
  </>
}

function NodePanel({ n, kind, size, onChange }: { n: DNode; kind: DiagramKind; size: Size; onChange: (p: Partial<DNode>) => void }) {
  const { t } = useLanguage()
  const types = KIND_SPEC[kind].nodes
  const mode = memberMode(kind, n.type)
  const methods = hasMethods(kind, n.type)
  const vis = mode === 'attr' && kind !== 'er'
  const setAttr = (i: number, p: Partial<DAttr>) => onChange({ attributes: n.attributes.map((a, j) => (j === i ? { ...a, ...p } : a)) })
  const setMeth = (i: number, p: Partial<DNode['methods'][number]>) => onChange({ methods: n.methods.map((m, j) => (j === i ? { ...m, ...p } : m)) })
  const membersTitle = mode === 'column' ? t('dg.columns') : mode === 'line' ? t(n.type === 'state' ? 'dg.activities' : 'dg.contents') : t('dg.attributes')
  const changeType = (type: NodeType) => {
    const p: Partial<DNode> = { type }
    if (CONTAINERS.has(type) && !n.w) { const cs = CONTAINER_SIZE[type]!; p.w = cs[0]; p.h = cs[1] }
    onChange(p)
  }
  const toggle = (on: boolean, label: string, icon: React.ReactNode, click: () => void) => (
    <button className={`h-7 w-7 rounded inline-flex items-center justify-center shrink-0 ${on ? 'bg-marker-soft text-marker-deep' : 'text-ink-faint hover:text-ink'}`}
      onClick={click} title={label} aria-label={label} aria-pressed={on}>{icon}</button>
  )
  return (
    <>
      <div>
        <label className="field-label" htmlFor="dg-name">{t('dg.name')}</label>
        <input id="dg-name" className="input h-8" value={n.name} placeholder={PSEUDO.has(n.type) ? t('dg.optional') : undefined}
          onChange={(e) => onChange({ name: e.target.value })} autoFocus />
      </div>
      {types.length > 1 && (
        <div>
          <label className="field-label" htmlFor="dg-type">{t('dg.type')}</label>
          <select id="dg-type" className="input h-8" value={n.type} onChange={(e) => changeType(e.target.value as NodeType)}>
            {types.map((x) => <option key={x} value={x}>{t(`dg.ntype.${x}` as any)}</option>)}
          </select>
        </div>
      )}
      {CONTAINERS.has(n.type) && (
        <div className="grid grid-cols-2 gap-2">
          {(['w', 'h'] as const).map((k) => (
            <div key={k}>
              <label className="field-label" htmlFor={`dg-${k}`}>{t(k === 'w' ? 'dg.width' : 'dg.height')}</label>
              <input id={`dg-${k}`} type="number" min={k === 'w' ? 120 : 80} step={10} className="input h-8" value={Math.round(size[k])}
                onChange={(e) => onChange({ [k]: Math.max(k === 'w' ? 120 : 80, Number(e.target.value) || 0) })} />
            </div>
          ))}
          <p className="col-span-2 -mt-1 text-[11.5px] text-ink-muted">{t('dg.containerHint')}</p>
        </div>
      )}
      {mode && (
        <div>
          <p className="field-label">{membersTitle}</p>
          <ul className="space-y-1.5">
            {n.attributes.map((a, i) => (
              <li key={i} className="flex items-center gap-1">
                {vis && (
                  <select className="input h-7 w-11 px-1 text-[12px]" value={a.visibility} onChange={(e) => setAttr(i, { visibility: e.target.value })} aria-label={t('dg.visibility')}>
                    {['', '-', '+', '#', '~'].map((v) => <option key={v} value={v}>{v || '·'}</option>)}
                  </select>
                )}
                <input className="input h-7 px-1.5 text-[12px] min-w-0 flex-1" value={a.name}
                  placeholder={mode === 'line' ? t(n.type === 'state' ? 'dg.activityPh' : 'dg.contentPh') : t('dg.attrName')}
                  onChange={(e) => setAttr(i, { name: e.target.value })} />
                {mode !== 'line' && <input className="input h-7 px-1.5 text-[12px] w-16" value={a.type} placeholder={t('dg.attrType')} onChange={(e) => setAttr(i, { type: e.target.value })} />}
                {(kind === 'er' || mode === 'column') && toggle(a.pk, t('dg.pk'), <Key size={13} />, () => setAttr(i, { pk: !a.pk }))}
                {mode === 'column' && toggle(a.fk, t('dg.fk'), <Link2 size={13} />, () => setAttr(i, { fk: !a.fk }))}
                <button className="h-7 w-6 shrink-0 text-ink-faint hover:text-bad" onClick={() => onChange({ attributes: n.attributes.filter((_, j) => j !== i) })} aria-label={t('dg.remove')}><Minus size={13} /></button>
              </li>
            ))}
          </ul>
          <button className="btn-ghost btn-sm mt-1 h-7" onClick={() => onChange({ attributes: [...n.attributes, { name: '', type: '', visibility: vis ? '-' : '', pk: false, fk: false }] })}>
            <Plus size={13} /> {mode === 'column' ? t('dg.addColumn') : mode === 'line' ? t('dg.addLine') : t('dg.addAttr')}
          </button>
        </div>
      )}
      {methods && (
        <div>
          <p className="field-label">{t('dg.methods')}</p>
          <ul className="space-y-1.5">
            {n.methods.map((m, i) => (
              <li key={i} className="flex items-center gap-1">
                <select className="input h-7 w-11 px-1 text-[12px]" value={m.visibility} onChange={(e) => setMeth(i, { visibility: e.target.value })} aria-label={t('dg.visibility')}>
                  {['', '+', '-', '#', '~'].map((v) => <option key={v} value={v}>{v || '·'}</option>)}
                </select>
                <input className="input h-7 px-1.5 text-[12px] min-w-0 flex-1" value={m.name} placeholder={t('dg.methodName')} onChange={(e) => setMeth(i, { name: e.target.value })} />
                <input className="input h-7 px-1.5 text-[12px] w-16" value={m.returns} placeholder={t('dg.returns')} onChange={(e) => setMeth(i, { returns: e.target.value })} />
                <button className="h-7 w-6 text-ink-faint hover:text-bad" onClick={() => onChange({ methods: n.methods.filter((_, j) => j !== i) })} aria-label={t('dg.remove')}><Minus size={13} /></button>
              </li>
            ))}
          </ul>
          <button className="btn-ghost btn-sm mt-1 h-7" onClick={() => onChange({ methods: [...n.methods, { name: '', params: '', returns: '', visibility: '+' }] })}>
            <Plus size={13} /> {t('dg.addMethod')}
          </button>
        </div>
      )}
    </>
  )
}

function EdgePanel({ e, d, kinds, onChange }: { e: DEdge; d: Diagram; kinds: EdgeKind[]; onChange: (p: Partial<DEdge>) => void }) {
  const { t } = useLanguage()
  const node = (id: string) => d.nodes.find((n) => n.id === id)
  const name = (id: string) => { const n = node(id); return n ? displayName(n, t) : '?' }
  const spec = KIND_SPEC[d.kind]
  const multOptions = d.kind === 'uml' ? ['1', '0..1', '0..*', '1..*', '*'] : ['1', 'N', 'M', '0..1', '1..N']
  const labelText = d.kind === 'er' ? t('dg.relName') : e.kind === 'transition' ? t('dg.trigger') : e.kind === 'flow' ? t('dg.guard')
    : d.kind === 'deployment' && e.kind === 'association' ? t('dg.protocol') : e.kind === 'foreign_key' ? t('dg.fkLabel') : t('dg.label')
  return (
    <>
      <p className="font-semibold">{name(e.from)} <span className="text-ink-muted">→</span> {name(e.to)}</p>
      <div>
        {kinds.length > 1 && <>
          <label className="field-label" htmlFor="dg-kind">{t('dg.relationKind')}</label>
          <select id="dg-kind" className="input h-8" value={e.kind} onChange={(ev) => onChange({ kind: ev.target.value as EdgeKind })}>
            {kinds.map((k) => <option key={k} value={k}>{t(`dg.kind.${k}` as any)}</option>)}
          </select>
        </>}
        <p className="mt-1 text-[11.5px] text-ink-muted">{t(`dg.kindHint.${e.kind}` as any)}</p>
      </div>
      <div>
        <label className="field-label" htmlFor="dg-label">{labelText}</label>
        <input id="dg-label" className="input h-8" value={e.label} onChange={(ev) => onChange({ label: ev.target.value })} />
      </div>
      {spec.mults && (
        <div className="grid grid-cols-2 gap-2">
          {(['fromMult', 'toMult'] as const).map((k) => (
            <div key={k}>
              <label className="field-label truncate" htmlFor={`dg-${k}`} title={name(k === 'fromMult' ? e.from : e.to)}>{t('dg.multAt', { name: name(k === 'fromMult' ? e.from : e.to) })}</label>
              <input id={`dg-${k}`} list={`dg-${k}-list`} className="input h-8" value={e[k]} onChange={(ev) => onChange({ [k]: ev.target.value })} />
              <datalist id={`dg-${k}-list`}>{multOptions.map((m) => <option key={m} value={m} />)}</datalist>
            </div>
          ))}
        </div>
      )}
      <button className="btn-ghost btn-sm" onClick={() => onChange({ from: e.to, to: e.from, fromMult: e.toMult, toMult: e.fromMult })}>
        <ArrowLeftRight size={13} /> {t('dg.swap')}
      </button>
    </>
  )
}
