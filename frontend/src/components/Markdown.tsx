import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** Task descriptions: Markdown + GitHub extensions (tables, strikethrough) — Moodle imports often contain tables. */
export default function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
}
