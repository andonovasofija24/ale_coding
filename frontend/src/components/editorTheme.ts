import type { BeforeMount } from '@monaco-editor/react'

const MARKERS: Record<string, { soft: string; select: string; inactive: string }> = {
  cpp: { soft: '#FFF4C2', select: '#FFE58A', inactive: '#FFF0B3' },
  java: { soft: '#FFEBD6', select: '#FFCF9E', inactive: '#FFE3C4' },
  python: { soft: '#E6FAEA', select: '#B9F2C3', inactive: '#D3F6DA' },
  c: { soft: '#F3EFFF', select: '#DCD0FE', inactive: '#E9E2FF' },
  javascript: { soft: '#FFF0F5', select: '#FCCFDF', inactive: '#FFE1EC' },
  sql: { soft: '#E8FAFC', select: '#B5EEF5', inactive: '#D3F5F9' },
  postgresql: { soft: '#ECF6FF', select: '#C0E3FE', inactive: '#D8EDFE' },
  typescript: { soft: '#F0F3FF', select: '#CED7FF', inactive: '#E0E6FF' },
  php: { soft: '#E9FCF6', select: '#B9F4E2', inactive: '#D3F8ED' },
  bash: { soft: '#F8F9FA', select: '#E9ECEE', inactive: '#F1F3F5' },
  csharp: { soft: '#FBF1FE', select: '#F3D1FB', inactive: '#F8E2FD' },
  kotlin: { soft: '#FFEEEE', select: '#FFC9C9', inactive: '#FFDDDD' },
  prolog: { soft: '#F6FCEC', select: '#E3F6C1', inactive: '#EDF9D8' },
  lisp: { soft: '#FAF7F2', select: '#EDE4D6', inactive: '#F4EEE6' },
  asm: { soft: '#F1F3F6', select: '#D1D8E2', inactive: '#E2E7ED' },
  web: { soft: '#FFF1EC', select: '#FFCDBD', inactive: '#FFE2D8' },
  uml: { soft: '#FFF8DB', select: '#FFE8A1', inactive: '#FFF1C4' },
  er: { soft: '#EBFBEE', select: '#C3F0CC', inactive: '#D8F5DE' },
}

/** Monaco theme name for a task language (unknown languages use the C++ theme). */
export function editorTheme(lang: string): string {
  return `ale-${lang in MARKERS ? lang : 'cpp'}`
}

/**
 * Editor themes in the app's palette — one per language. The current line is highlighted with that
 * language's marker colour ("you are here").
 */
export const defineAleTheme: BeforeMount = (monaco) => {
  for (const [lang, m] of Object.entries(MARKERS)) defineOne(monaco, `ale-${lang}`, m)
  defineOne(monaco, 'ale', MARKERS.cpp) // backwards-compatible name
}

function defineOne(monaco: Parameters<BeforeMount>[0], name: string, m: { soft: string; select: string; inactive: string }) {
  monaco.editor.defineTheme(name, {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '8A93A6', fontStyle: 'italic' },
      { token: 'keyword', foreground: '2747C9', fontStyle: 'bold' },
      { token: 'string', foreground: '188A5A' },
      { token: 'number', foreground: 'B5521B' },
      { token: 'type', foreground: '6B3FC9' },
    ],
    colors: {
      'editor.background': '#FFFFFF',
      'editor.lineHighlightBackground': m.soft,
      'editor.lineHighlightBorder': m.soft,
      'editorLineNumber.foreground': '#B3BAC7',
      'editorLineNumber.activeForeground': '#1A2233',
      'editorCursor.foreground': '#1A2233',
      'editor.selectionBackground': m.select,
      'editor.inactiveSelectionBackground': m.inactive,
      'editorIndentGuide.background1': '#EEF1F5',
      'editorGutter.background': '#FFFFFF',
    },
  })
}
