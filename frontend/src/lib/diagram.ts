/**
 * Diagram tasks: UML class, use case, state, activity, component, package and deployment diagrams, ER diagrams and
 * relational schemas. The diagram is kept as JSON text, like code (the same format is read by the backend:
 * backend/app/services/diagrams.py — KIND_SPEC there and here must agree).
 */
export type DiagramKind = 'uml' | 'er' | 'usecase' | 'state' | 'activity' | 'component' | 'package' | 'deployment' | 'relational' | 'sequence'
export type NodeType =
  | 'class' | 'abstract' | 'interface' | 'enum' | 'entity' | 'weak'
  | 'actor' | 'usecase' | 'system'
  | 'state' | 'initial' | 'final' | 'choice'
  | 'action' | 'flow_final' | 'decision' | 'merge' | 'fork' | 'join' | 'swimlane'
  | 'component' | 'package' | 'node' | 'device' | 'artifact' | 'table' | 'lifeline'
export type EdgeKind =
  | 'association' | 'aggregation' | 'composition' | 'inheritance' | 'realization' | 'dependency' | 'relationship'
  | 'include' | 'extend' | 'transition' | 'flow' | 'import' | 'merge' | 'deploy' | 'foreign_key'
  | 'sync' | 'async' | 'reply' | 'create'

export interface DAttr { name: string; type: string; visibility: string; pk: boolean; fk: boolean; aliases?: string[] }
export interface DMethod { name: string; params: string; returns: string; visibility: string }
export interface DNode {
  id: string; name: string; type: NodeType; x: number; y: number; w?: number; h?: number
  attributes: DAttr[]; methods: DMethod[]; aliases?: string[]
}
/** y: sequence diagrams only — when the message happens (top to bottom). */
export interface DEdge { id: string; from: string; to: string; kind: EdgeKind; fromMult: string; toMult: string; label: string; y?: number }
export interface Diagram { kind: DiagramKind; nodes: DNode[]; edges: DEdge[] }

interface KindSpec { nodes: NodeType[]; edges: EdgeKind[]; mults?: boolean; flow?: boolean }
export const KIND_SPEC: Record<DiagramKind, KindSpec> = {
  uml: { nodes: ['class', 'abstract', 'interface', 'enum'], edges: ['association', 'aggregation', 'composition', 'inheritance', 'realization', 'dependency'], mults: true },
  er: { nodes: ['entity', 'weak'], edges: ['relationship'], mults: true },
  usecase: { nodes: ['actor', 'usecase', 'system'], edges: ['association', 'include', 'extend', 'inheritance'] },
  state: { nodes: ['state', 'initial', 'final', 'choice'], edges: ['transition'], flow: true },
  activity: { nodes: ['action', 'initial', 'final', 'flow_final', 'decision', 'merge', 'fork', 'join', 'swimlane'], edges: ['flow'], flow: true },
  component: { nodes: ['component', 'interface', 'class'], edges: ['dependency', 'realization', 'association'] },
  package: { nodes: ['package', 'class', 'interface'], edges: ['dependency', 'import', 'merge', 'inheritance'] },
  deployment: { nodes: ['node', 'device', 'artifact', 'component'], edges: ['association', 'deploy', 'dependency'] },
  relational: { nodes: ['table'], edges: ['foreign_key'], mults: true },
  sequence: { nodes: ['lifeline', 'actor'], edges: ['sync', 'async', 'reply', 'create'] },
}
export const DIAGRAM_KINDS = Object.keys(KIND_SPEC) as DiagramKind[]
export const PSEUDO = new Set<NodeType>(['initial', 'final', 'flow_final', 'decision', 'merge', 'fork', 'join', 'choice'])
/** Boxes drawn around other boxes: they have their own size (w / h) and are drawn behind everything else. */
export const CONTAINERS = new Set<NodeType>(['system', 'swimlane', 'package', 'node', 'device'])
/** Kept for older imports. */
export const UML_NODE_TYPES = KIND_SPEC.uml.nodes, ER_NODE_TYPES = KIND_SPEC.er.nodes
export const UML_EDGE_KINDS = KIND_SPEC.uml.edges, ER_EDGE_KINDS = KIND_SPEC.er.edges

/** What a box lists inside: class-like members (with types), table columns, or plain lines
 *  (internal activities of a state, the contents of a package / node). */
export type MemberMode = 'attr' | 'column' | 'line' | null
export function memberMode(kind: DiagramKind, type: NodeType): MemberMode {
  if (kind === 'sequence') return null
  if (kind === 'relational') return 'column'
  if (kind === 'uml' || kind === 'er') return 'attr'
  if (type === 'class' || type === 'interface') return 'attr'
  if (type === 'state' || type === 'package' || type === 'node' || type === 'device' || type === 'component') return 'line'
  return null
}
export const hasMethods = (kind: DiagramKind, type: NodeType) =>
  kind === 'uml' || ((kind === 'component' || kind === 'package') && (type === 'class' || type === 'interface'))
/** A class-like box with compartments (name / attributes / methods). */
export const isClassBox = (kind: DiagramKind, type: NodeType) =>
  kind === 'uml' || kind === 'er' || kind === 'relational' || ((kind === 'component' || kind === 'package') && (type === 'class' || (type === 'interface' && kind === 'package')))

const str = (v: unknown) => (typeof v === 'string' ? v : v == null ? '' : String(v))
const num = (v: unknown, d: number) => (Number.isFinite(Number(v)) && v !== '' && v != null ? Number(v) : d)

export function parseDiagram(text: string, kind: DiagramKind): Diagram {
  let d: any = {}
  try { d = JSON.parse(text || '{}') } catch { d = {} }
  if (!d || typeof d !== 'object') d = {}
  const spec = KIND_SPEC[kind] ?? KIND_SPEC.uml
  const nodes: DNode[] = (Array.isArray(d.nodes) ? d.nodes : []).map((n: any, i: number) => {
    if (!n || typeof n !== 'object') return null
    const type: NodeType = spec.nodes.includes(n.type) ? n.type : spec.nodes[0]
    if (!str(n.name).trim() && !PSEUDO.has(type)) return null
    const node: DNode = {
      id: str(n.id) || `n${i + 1}`,
      name: str(n.name),
      type,
      x: num(n.x, 40 + (i % 3) * 300), y: num(n.y, 40 + Math.floor(i / 3) * 260),
      attributes: (Array.isArray(n.attributes) ? n.attributes : []).map((a: any) => ({
        name: str(a?.name), type: str(a?.type), visibility: str(a?.visibility), pk: !!a?.pk, fk: !!a?.fk, ...(a?.aliases ? { aliases: a.aliases } : {}),
      })),
      methods: (Array.isArray(n.methods) ? n.methods : []).map((m: any) => ({
        name: str(m?.name), params: str(m?.params), returns: str(m?.returns), visibility: str(m?.visibility),
      })),
      ...(n.aliases ? { aliases: n.aliases } : {}),
    }
    if (CONTAINERS.has(type)) { node.w = Math.max(120, num(n.w, 360)); node.h = Math.max(80, num(n.h, 300)) }
    return node
  }).filter(Boolean) as DNode[]
  const ids = new Set(nodes.map((n) => n.id))
  const edges: DEdge[] = (Array.isArray(d.edges) ? d.edges : []).filter((e: any) => e && ids.has(e.from) && ids.has(e.to)).map((e: any, i: number) => ({
    id: str(e.id) || `e${i + 1}`, from: e.from, to: e.to,
    kind: spec.edges.includes(e.kind) ? e.kind : spec.edges[0],
    fromMult: str(e.fromMult), toMult: str(e.toMult), label: str(e.label),
    ...(kind === 'sequence' ? { y: num(e.y, 120 + i * 50) || 120 + i * 50 } : {}),
  }))
  return { kind, nodes, edges }
}

/** A submission's code that is a diagram (its kind), or null. */
export function diagramKindOf(code: string): DiagramKind | null {
  if (!code || code.trimStart()[0] !== '{' || !code.includes('"nodes"')) return null
  try { const k = JSON.parse(code).kind; return (DIAGRAM_KINDS as string[]).includes(k) ? k : null } catch { return null }
}

export const dumpDiagram = (d: Diagram) => JSON.stringify(d, null, 1)
export const emptyDiagram = (kind: DiagramKind) => dumpDiagram({ kind, nodes: [], edges: [] })
export const newId = (p: string) => p + Date.now().toString(36) + Math.random().toString(36).slice(2, 5)

// ---- geometry -------------------------------------------------------------------------------------------------

export const ROW = 18
export const HEAD = 30
const CHAR = 7.1
const textW = (s: string, min: number, pad = 28, max = 380) => Math.max(min, Math.min(max, s.length * CHAR + pad))

export function memberText(kind: DiagramKind, a: DAttr): string {
  if (kind === 'er' || kind === 'relational') return a.name + (a.type ? ` : ${a.type}` : '')
  return `${a.visibility || ''}${a.visibility ? ' ' : ''}${a.name}${a.type ? ' : ' + a.type : ''}`
}
export function methodText(m: DMethod): string {
  return `${m.visibility || ''}${m.visibility ? ' ' : ''}${m.name}(${m.params})${m.returns ? ' : ' + m.returns : ''}`
}
export function stereotype(n: DNode, kind: DiagramKind = 'uml'): string {
  switch (n.type) {
    case 'interface': return kind === 'component' ? '' : '«interface»'
    case 'enum': return '«enumeration»'
    case 'abstract': return '{abstract}'
    case 'component': return '«component»'
    case 'artifact': return '«artifact»'
    case 'device': return '«device»'
    case 'table': return '«table»'
    default: return ''
  }
}

export type Shape = 'box' | 'ellipse' | 'circle' | 'diamond' | 'bar'
export interface Size { w: number; h: number; head: number; shape: Shape }

export function nodeSize(kind: DiagramKind, n: DNode): Size {
  const lines = n.attributes.map((a) => a.name)
  switch (n.type) {
    case 'actor': return { w: textW(n.name, 80, 12, 200), h: 104, head: 0, shape: 'box' }
    case 'usecase': return { w: textW(n.name, 140, 44, 300), h: 60, head: 0, shape: 'ellipse' }
    case 'initial': return { w: 26, h: 26, head: 0, shape: 'circle' }
    case 'final': return { w: 30, h: 30, head: 0, shape: 'circle' }
    case 'flow_final': return { w: 28, h: 28, head: 0, shape: 'circle' }
    case 'decision': case 'merge': case 'choice': {
      const w = n.name ? textW(n.name, 64, 52, 260) : 44
      return { w, h: n.name ? 56 : 44, head: 0, shape: 'diamond' }
    }
    case 'fork': case 'join': return { w: 200, h: 8, head: 0, shape: 'bar' }
    case 'action': return { w: textW(n.name, 130, 36, 300), h: 46, head: 0, shape: 'box' }
    case 'state': {
      const w = Math.max(textW(n.name, 130, 36, 320), ...lines.map((l) => textW(l, 0, 24, 320)))
      return { w, h: lines.length ? 36 + lines.length * ROW + 8 : 46, head: 36, shape: 'box' }
    }
    case 'artifact': return { w: textW(n.name, 140, 48, 300), h: 56, head: 0, shape: 'box' }
    case 'interface':
      if (kind === 'component') return { w: 30 + textW(n.name, 40, 4, 220), h: 26, head: -1, shape: 'box' }  // head -1: a lollipop, name on the right
      break
    case 'component':
      if (!lines.length) return { w: textW(n.name, 160, 56, 320), h: 62, head: 0, shape: 'box' }
      return { w: Math.max(textW(n.name, 160, 56, 320), ...lines.map((l) => textW(l, 0, 24))), h: 50 + lines.length * ROW + 8, head: 50, shape: 'box' }
  }
  if (CONTAINERS.has(n.type)) {
    const head = n.type === 'package' ? 30 : n.type === 'device' ? 50 : 32
    const minW = Math.max(textW(n.name, 120, 40), ...lines.map((l) => textW(l, 0, 30)))
    const minH = head + lines.length * ROW + 16
    return { w: Math.max(n.w ?? 360, minW), h: Math.max(n.h ?? 300, minH), head, shape: 'box' }
  }
  // class-like box with compartments (UML classes, ER entities, tables)
  const st = stereotype(n, kind)
  const head = HEAD + (st ? 14 : 0)
  const methods = hasMethods(kind, n.type)
  const texts = [n.name, st, ...n.attributes.map((a) => memberText(kind, a) + (a.pk || a.fk ? '  PK FK' : '')), ...n.methods.map(methodText)]
  const w = Math.max(150, Math.min(380, Math.max(...texts.map((t) => t.length * CHAR)) + 28))
  const rows = Math.max(1, n.attributes.length) + (methods ? Math.max(1, n.methods.length) : 0)
  const h = head + rows * ROW + (methods ? 16 : 10)
  return { w, h, head, shape: 'box' }
}

/** Where the line from the centre of a box (x, y, w, h) towards point (px, py) leaves its outline. */
export function borderPoint(x: number, y: number, w: number, h: number, px: number, py: number, shape: Shape = 'box', ox = 0, oy = 0) {
  // (ox, oy): start from a point beside the centre (two lines between the same boxes)
  const cx = x + w / 2 + ox, cy = y + h / 2 + oy
  const dx = px - cx, dy = py - cy
  if (dx === 0 && dy === 0) return { x: cx, y: cy }
  let s: number
  if (shape === 'ellipse' || shape === 'circle') s = 1 / Math.sqrt((dx * dx) / ((w / 2) ** 2) + (dy * dy) / ((h / 2) ** 2))
  else if (shape === 'diamond') s = 1 / (Math.abs(dx) / (w / 2) + Math.abs(dy) / (h / 2))
  else s = Math.min(Math.abs((w / 2) / (dx || 1e-9)), Math.abs((h / 2) / (dy || 1e-9)))
  return { x: cx + dx * s, y: cy + dy * s }
}

/** The node's name as shown in lists (unnamed start / end / decision… get the name of their kind). */
export const displayName = (n: DNode, t: (k: any) => string) => n.name || t(`dg.ntype.${n.type}`)
