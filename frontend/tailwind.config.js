/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Onest', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // "Highlighter on a notebook": calm blue-grey paper, navy ink,
        // and one bold colour — the yellow marker — which always means "you are here".
        paper: '#EEF1F5',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#1A2233',
          soft: '#3A4458',
          muted: '#6B7488',
          faint: '#9AA2B2',
        },
        line: {
          DEFAULT: '#D3D9E3',
          soft: '#E4E8EF',
          strong: '#B9C2D0',
        },
        cobalt: {
          DEFAULT: '#2747C9',
          hover: '#1E39A6',
          soft: '#E8EDFC',
        },
        // The marker colour depends on the programming language (CSS variables set by .lang-* in index.css).
        marker: {
          DEFAULT: 'rgb(var(--marker) / <alpha-value>)',
          soft: 'rgb(var(--marker-soft) / <alpha-value>)',
          deep: 'rgb(var(--marker-deep) / <alpha-value>)',
        },
        ok: { DEFAULT: '#188A5A', soft: '#E3F5EC' },
        bad: { DEFAULT: '#C93C3C', soft: '#FBEAEA' },
        obj: { DEFAULT: '#6B3FC9', soft: '#F1ECFC' },
      },
      boxShadow: {
        lift: '0 1px 2px rgba(26,34,51,.06), 0 8px 24px -12px rgba(26,34,51,.18)',
        modal: '0 24px 64px -16px rgba(26,34,51,.35)',
        // a printed / stamped look for the surfaces that matter most (hard offset, no blur)
        stamp: '4px 4px 0 #1A2233',
        'stamp-sm': '2px 2px 0 #1A2233',
      },
      keyframes: {
        'marker-in': {
          '0%': { backgroundSize: '0% 100%' },
          '100%': { backgroundSize: '100% 100%' },
        },
        'node-pop': {
          '0%': { transform: 'scale(.6)', opacity: '0' },
          '70%': { transform: 'scale(1.12)', opacity: '1' },
          '100%': { transform: 'scale(1)' },
        },
        drift: {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(-50%)' },
        },
      },
      animation: {
        'marker-in': 'marker-in .6s cubic-bezier(.2,.7,.2,1) both',
        'node-pop': 'node-pop .45s cubic-bezier(.2,.7,.2,1) both',
        drift: 'drift var(--drift-duration, 80s) linear infinite',
      },
    },
  },
  plugins: [],
}
