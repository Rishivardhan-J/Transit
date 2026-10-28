import type { Config } from 'tailwindcss'
import { catColors, colors } from './src/design-system/tokens'

// Everything sits directly in `theme` (not `theme.extend`), so Tailwind's defaults are removed and any value
// outside the 4px grid / PRD scale simply does not exist. Layout sizes that are not spacing steps are named.
const spacing = {
  0: '0px', px: '1px', 1: '4px', 2: '8px', 3: '12px', 4: '16px', 6: '24px', 8: '32px', 12: '48px', 16: '64px', 24: '96px',
}
const named = {
  icon: '16px', 'icon-lg': '20px', toggle: '36px', knob: '16px', 'toggle-h': '20px', rail: '64px', topbar: '64px',
  'panel-sm': '320px', 'panel-md': '400px', 'panel-lg': '480px', chart: '280px', 'chart-sm': '200px',
  'map-sm': '400px', 'map-md': '560px', 'map-lg': '720px', 'control-h': '40px',
}
const sizes = { ...spacing, ...named, full: '100%', screen: '100vh', auto: 'auto' }

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      surface: colors.surface,
      accent: colors.accent,
      status: {
        success: colors.status.success,
        warning: colors.status.warning,
        error: colors.status.error,
      },
      text: colors.text,
      border: colors.border,
      cat: Object.fromEntries(catColors.map((c, i) => [i + 1, c])),
    },
    spacing,
    width: { ...sizes, '1/2': '50%', '1/3': '33.333%', '2/3': '66.667%', '1/4': '25%', '3/4': '75%' },
    height: sizes,
    minHeight: { ...sizes, 0: '0px' },
    maxHeight: { ...sizes, none: 'none' },
    minWidth: { ...sizes, 0: '0px' },
    maxWidth: { ...sizes, container: '1536px', none: 'none' },
    inset: { ...spacing, auto: 'auto', full: '100%', '1/2': '50%' },
    fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    fontSize: {
      12: ['12px', '16px'], 14: ['14px', '20px'], 16: ['16px', '24px'], 20: ['20px', '28px'],
      24: ['24px', '32px'], 32: ['32px', '40px'], 48: ['48px', '48px'],
    },
    fontWeight: { normal: '400', medium: '500', semibold: '600', bold: '700' },
    letterSpacing: { normal: '0em', wide: '0.04em', widest: '0.12em' },
    borderWidth: { 0: '0px', 1: '1px', DEFAULT: '1px' },
    borderRadius: { none: '0px', sm: '4px', md: '8px', full: '9999px' },
    boxShadow: { none: 'none' },
    opacity: { 0: '0', 40: '0.4', 50: '0.5', 60: '0.6', 80: '0.8', 100: '1' },
    zIndex: { 0: '0', 10: '10', 20: '20', 30: '30', 40: '40', 50: '50' },
    transitionDuration: { 0: '0ms', DEFAULT: '150ms', 150: '150ms' },
    ringWidth: { 0: '0px', DEFAULT: '2px', 1: '1px', 2: '2px' },
    ringOffsetWidth: { 0: '0px', 2: '2px' },
    gridTemplateColumns: Object.fromEntries(Array.from({ length: 12 }, (_, i) => [i + 1, `repeat(${i + 1}, minmax(0, 1fr))`])),
    gridColumn: Object.fromEntries([
      ...Array.from({ length: 12 }, (_, i) => [`span-${i + 1}`, `span ${i + 1} / span ${i + 1}`]), ['auto', 'auto'],
    ]),
    screens: { sm: '640px', md: '768px', lg: '1024px', xl: '1280px', '2xl': '1536px' },
    extend: {},
  },
  plugins: [],
} satisfies Config
