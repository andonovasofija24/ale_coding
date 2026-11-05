/**
 * Wordmark: "ALE" with a highlighter stroke — the yellow marker is the brand's one bold device
 * and means "you are here" everywhere else in the UI.
 */
export default function Logo({ size = 'md', onDark = false }: { size?: 'md' | 'lg'; onDark?: boolean }) {
  const text = size === 'lg' ? 'text-4xl' : 'text-xl'
  return (
    <span className={`relative inline-block font-extrabold tracking-tight leading-none ${text} ${onDark ? 'text-white' : 'text-ink'}`}>
      <span
        aria-hidden
        className={`absolute left-[-0.08em] right-[-0.08em] rounded-[2px] bg-marker ${
          onDark ? 'bottom-[-0.22em] h-[0.16em]' : 'bottom-[0.02em] h-[0.42em]'
        }`}
      />
      <span className="relative">ALE</span>
    </span>
  )
}
