/**
 * Theme Toggle Component - Robotic Style
 *
 * A segmented control that lets users switch between:
 * - Light mode (sun icon)
 * - Dark mode (moon icon)
 * - System/auto (monitor icon)
 *
 * Styled with neon accents and cyber borders.
 */

import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import clsx from 'clsx';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const options = [
    { value: 'light' as const, icon: Sun, label: 'Light' },
    { value: 'dark' as const, icon: Moon, label: 'Dark' },
    { value: 'system' as const, icon: Monitor, label: 'Auto' },
  ];

  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-robot-panel border border-robot-border/50 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          className={clsx(
            'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-mono font-medium transition-all duration-300',
            theme === opt.value
              ? 'bg-cyber-400/15 text-neon-blue border border-cyber-400/30 shadow-inner'
              : 'text-gray-500 border border-transparent hover:text-gray-300 hover:bg-white/5'
          )}
          aria-label={`Switch to ${opt.label} mode`}
          title={opt.label}
        >
          <opt.icon className={clsx(
            'h-3.5 w-3.5 transition-colors',
            theme === opt.value ? 'text-neon-blue' : ''
          )} />
          <span className="hidden sm:inline text-[10px] uppercase tracking-wider">{opt.label}</span>
        </button>
      ))}
    </div>
  );
}
