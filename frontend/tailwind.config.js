/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        cyber: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        neon: {
          blue: '#00f0ff',
          cyan: '#0ff',
          purple: '#bf00ff',
          pink: '#ff00e5',
          green: '#00ff88',
          orange: '#ff6b00',
        },
        // Dark mode robot palette
        robot: {
          dark: '#0a0e1a',
          darker: '#060810',
          panel: '#0d1225',
          border: '#1a2744',
          surface: '#111827',
          accent: '#00f0ff',
        },
        // Light mode equivalents
        'robot-light': {
          dark: '#f8fafc',
          darker: '#f1f5f9',
          panel: '#ffffff',
          border: '#e2e8f0',
          surface: '#f8fafc',
          accent: '#0891b2',
        },
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'border-glow': 'border-glow 3s ease-in-out infinite',
        'scan-line': 'scan-line 4s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'circuit-flow': 'circuit-flow 3s linear infinite',
        'text-glow': 'text-glow 2s ease-in-out infinite alternate',
        'hud-flicker': 'hud-flicker 0.15s infinite',
        'data-stream': 'data-stream 20s linear infinite',
        'rotate-slow': 'rotate-slow 20s linear infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1)' },
          '50%': { opacity: '0.8', filter: 'brightness(1.3)' },
        },
        'border-glow': {
          '0%, 100%': { borderColor: 'rgba(0, 240, 255, 0.3)' },
          '50%': { borderColor: 'rgba(0, 240, 255, 0.8)' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'circuit-flow': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '100% 100%' },
        },
        'text-glow': {
          '0%': { textShadow: '0 0 4px rgba(0, 240, 255, 0.5)' },
          '100%': { textShadow: '0 0 20px rgba(0, 240, 255, 0.9), 0 0 40px rgba(0, 240, 255, 0.4)' },
        },
        'hud-flicker': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.97' },
        },
        'data-stream': {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(-50%)' },
        },
        'rotate-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '80%, 100%': { transform: 'scale(2)', opacity: '0' },
        },
      },
      boxShadow: {
        'neon': '0 0 5px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3), 0 0 40px rgba(0, 240, 255, 0.1)',
        'neon-strong': '0 0 10px rgba(0, 240, 255, 0.7), 0 0 30px rgba(0, 240, 255, 0.5), 0 0 60px rgba(0, 240, 255, 0.2)',
        'neon-purple': '0 0 5px rgba(191, 0, 255, 0.5), 0 0 20px rgba(191, 0, 255, 0.3)',
        'inner-glow': 'inset 0 0 30px rgba(0, 240, 255, 0.1)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.36)',
        'neon-light': '0 0 5px rgba(8, 145, 178, 0.3), 0 0 15px rgba(8, 145, 178, 0.15)',
        'soft': '0 2px 15px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05)',
      },
      backgroundImage: {
        'circuit-pattern': `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%2300f0ff' stroke-width='0.5' opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/svg%3E")`,
        'grid-pattern': 'linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px)',
        'radial-glow': 'radial-gradient(ellipse at center, rgba(0, 240, 255, 0.15) 0%, transparent 70%)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
