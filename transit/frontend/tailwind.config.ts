import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    // We override everything by placing it directly in `theme`, not `theme.extend`.
    // This completely removes Tailwind's default colors, spacing, typography, etc.
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      surface: {
        dominant: '#0F172A',
        secondary: '#1E293B',
      },
      accent: '#F59E0B',
      status: {
        success: {
          bg: 'rgba(34, 197, 94, 0.15)',
          text: '#4ADE80',
        },
        warning: {
          bg: 'rgba(245, 158, 11, 0.18)',
          text: '#FCD34D',
        },
        error: {
          bg: 'rgba(239, 68, 68, 0.15)',
          text: '#FCA5A5',
        },
      },
      text: {
        primary: '#F1F5F9',
        secondary: '#94A3B8',
        muted: '#64748B',
      },
      border: {
        default: '#334155',
        hover: '#475569',
      },
      cat: {
        1: '#38BDF8',
        2: '#F59E0B',
        3: '#A78BFA',
        4: '#EC4899',
        5: '#10B981',
        6: '#F43F5E',
        7: '#8B5CF6',
        8: '#14B8A6',
      }
    },
    spacing: {
      0: '0px',
      1: '4px',
      2: '8px',
      3: '12px',
      4: '16px',
      6: '24px',
      8: '32px',
      12: '48px',
      16: '64px',
      24: '96px',
    },
    fontFamily: {
      sans: ['Inter', 'sans-serif'],
    },
    fontSize: {
      12: ['12px', '16px'],
      14: ['14px', '20px'],
      16: ['16px', '24px'],
      20: ['20px', '28px'],
      24: ['24px', '32px'],
      32: ['32px', '40px'],
      48: ['48px', '48px'],
    },
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    borderWidth: {
      0: '0px',
      1: '1px',
    },
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {},
  },
  plugins: [],
} satisfies Config
