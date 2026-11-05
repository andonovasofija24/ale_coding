/**
 * HTML/CSS/JS tasks keep several files in ONE text (saved, submitted and compared like any other code):
 *
 *   <!-- file: index.html -->
 *   ...
 *   <!-- file: style.css -->
 *   ...
 *   <!-- file: script.js -->
 *   ...
 *
 * Text before the first marker is index.html. The same format is read by the code runner (code-runner/app/web.py).
 */
export interface WebFile { name: string; content: string }

const MARKER = /^[ \t]*<!--\s*file:\s*([A-Za-z0-9_.-]+)\s*-->[ \t]*$/gm
const ALLOWED = /^[A-Za-z0-9_-]{1,40}\.(html|css|js)$/

export const DEFAULT_WEB_FILES: WebFile[] = [
  {
    name: 'index.html',
    content: '<!doctype html>\n<html lang="mk">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Страница</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n\n  <script src="script.js"></script>\n</body>\n</html>\n',
  },
  { name: 'style.css', content: 'body {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n}\n' },
  { name: 'script.js', content: '' },
]

export function splitBundle(code: string): WebFile[] {
  const files: WebFile[] = []
  const marks = [...code.matchAll(MARKER)]
  const head = marks.length ? code.slice(0, marks[0].index) : code
  if (head.trim() || marks.length === 0) files.push({ name: 'index.html', content: head.replace(/^\n+|\n+$/g, '') })
  marks.forEach((m, i) => {
    const start = (m.index ?? 0) + m[0].length
    const end = i + 1 < marks.length ? marks[i + 1].index ?? code.length : code.length
    const name = m[1]
    if (ALLOWED.test(name) && !files.some((f) => f.name === name)) {
      files.push({ name, content: code.slice(start, end).replace(/^\n/, '').replace(/\n+$/, '') + '\n' })
    }
  })
  if (!files.some((f) => f.name === 'index.html')) files.unshift({ name: 'index.html', content: '' })
  // index.html first, then CSS, then JS
  const rank = (n: string) => (n === 'index.html' ? 0 : n.endsWith('.html') ? 1 : n.endsWith('.css') ? 2 : 3)
  return files.sort((a, b) => rank(a.name) - rank(b.name))
}

export function joinBundle(files: WebFile[]): string {
  return files.map((f) => `<!-- file: ${f.name} -->\n${f.content.replace(/\n+$/, '')}\n`).join('')
}

export function monacoLanguage(name: string): string {
  return name.endsWith('.css') ? 'css' : name.endsWith('.js') ? 'javascript' : 'html'
}

const escapeScript = (s: string) => s.replace(/<\/script/gi, '<\\/script')

/**
 * One self-contained HTML document for the live preview: the page's own <link href="x.css"> and
 * <script src="x.js"> are replaced by the contents of those files (nothing is loaded from anywhere else).
 */
export function previewDocument(files: WebFile[], page = 'index.html'): string {
  const byName = new Map(files.map((f) => [f.name, f.content]))
  let html = byName.get(page) ?? ''
  html = html.replace(/<link\b[^>]*\bhref\s*=\s*["']?([^"' >]+)["']?[^>]*>/gi, (tag, href: string) => {
    const css = byName.get(href.replace(/^\.\//, ''))
    return css != null && /stylesheet/i.test(tag) ? `<style data-file="${href}">\n${css}\n</style>` : tag
  })
  html = html.replace(/<script\b([^>]*)\bsrc\s*=\s*["']?([^"' >]+)["']?([^>]*)>\s*<\/script>/gi, (tag, a: string, src: string, b: string) => {
    const js = byName.get(src.replace(/^\.\//, ''))
    return js != null ? `<script${a}${b} data-file="${src}">\n${escapeScript(js)}\n</script>` : tag
  })
  // links between the student's own pages stay inside the preview; everything else is blocked by the sandbox
  const guard = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:">`
  return /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (h) => `${h}\n${guard}`) : `${guard}\n${html}`
}
