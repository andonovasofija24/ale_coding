/** AI providers: model suggestions, example URLs and recognising which provider issued a key. */
import { AIProvider } from '../types'

/** Model name suggestions only — any model id the provider accepts can be typed. */
export const SUGGESTIONS: Record<AIProvider, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini'],
  anthropic: ['claude-sonnet-5-5', 'claude-haiku-5-5', 'claude-opus-5-5'],
  openai_compatible: ['llama-3.3-70b-versatile', 'meta-llama/llama-3.3-70b-instruct', 'qwen2.5-coder:7b'],
}
export const DEFAULT_MODEL: Record<AIProvider, string> = { openai: 'gpt-4o', anthropic: 'claude-sonnet-5-5', openai_compatible: '' }
export const URL_EXAMPLES = [
  'https://api.groq.com/openai/v1',
  'https://openrouter.ai/api/v1',
  'https://generativelanguage.googleapis.com/v1beta/openai/',
  'https://api.mistral.ai/v1',
  'https://api.deepseek.com/v1',
  'http://host.docker.internal:11434/v1',
]

/** Key formats that identify a provider. A key only works with the provider that issued it. */
export const KEY_KINDS: { name: string; test: (k: string) => boolean; provider: AIProvider; baseUrl?: string; model: string }[] = [
  { name: 'Anthropic', test: (k) => k.startsWith('sk-ant-'), provider: 'anthropic', model: 'claude-sonnet-5-5' },
  { name: 'OpenRouter', test: (k) => k.startsWith('sk-or-'), provider: 'openai_compatible', baseUrl: 'https://openrouter.ai/api/v1', model: 'meta-llama/llama-3.3-70b-instruct' },
  { name: 'Groq', test: (k) => k.startsWith('gsk_'), provider: 'openai_compatible', baseUrl: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile' },
  { name: 'Google Gemini', test: (k) => k.startsWith('AIza'), provider: 'openai_compatible', baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/', model: 'gemini-2.5-flash' },
  { name: 'OpenAI', test: (k) => k.startsWith('sk-proj-') || k.startsWith('sk-svcacct-') || k.startsWith('sk-admin-'), provider: 'openai', model: 'gpt-4o' },
]

/** If the typed key clearly belongs to a different provider than the one selected, say which one. */
export function keyMismatch(key: string, provider: AIProvider, baseUrl: string) {
  const kind = KEY_KINDS.find((k) => k.test(key.trim()))
  if (!kind) return null
  if (kind.provider !== provider) return kind
  if (kind.baseUrl && !baseUrl.includes(new URL(kind.baseUrl).host)) return kind
  return null
}

