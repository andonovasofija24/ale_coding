import {
  BookOpen, Boxes, Braces, Brain, Cpu, Database, DraftingCompass, GitFork, Globe, Infinity as InfinityIcon, Layers,
  MousePointerClick, Palette, Rocket, Server, Shapes, Smartphone, Terminal, Unlock,
  Sigma, Network, Shield, Bot, Briefcase, GraduationCap, GitBranch, Cloud, Container,
} from 'lucide-react'

const ICONS: Record<string, typeof BookOpen> = {
  braces: Braces, boxes: Boxes, cpu: Cpu, 'git-fork': GitFork, terminal: Terminal, 'drafting-compass': DraftingCompass,
  brain: Brain, database: Database, globe: Globe, rocket: Rocket, infinity: InfinityIcon, layers: Layers, palette: Palette,
  'mouse-pointer-click': MousePointerClick, server: Server, unlock: Unlock, smartphone: Smartphone, 'book-open': BookOpen, shapes: Shapes,
  sigma: Sigma, network: Network, shield: Shield, bot: Bot, briefcase: Briefcase, 'graduation-cap': GraduationCap,
  'git-branch': GitBranch, cloud: Cloud, container: Container,
}
export const SUBJECT_ICONS = Object.keys(ICONS)

/** A subject's icon on a tile in its own colour. */
export default function SubjectIcon({ icon, color, size = 44 }: { icon: string; color: string; size?: number }) {
  const Icon = ICONS[icon] ?? BookOpen
  return (
    <span className="shrink-0 rounded-xl flex items-center justify-center shadow-[inset_0_-2px_0_rgba(0,0,0,.12)]"
      style={{ width: size, height: size, background: color, color: '#fff' }} aria-hidden>
      <Icon size={Math.round(size * 0.5)} strokeWidth={2.2} />
    </span>
  )
}
