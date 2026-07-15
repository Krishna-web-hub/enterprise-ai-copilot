/**
 * Theme Toggle Button - Robotic Style
 *
 * A single button that cycles through Light → Dark → System.
 * Shows in the HUD header for easy access.
 * Styled with neon glow accents.
 */

import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import clsx from 'clsx';

export default function ThemeToggleButton() {
  const { theme, setTheme } = useTheme();

  function cycleTheme() {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  }

  const Icon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor;
  const label = theme === 'dark' ? 'Dark' : theme === 'light' ? 'Light' : 'Auto';

  return (
    <button
      onClick={cycleTheme}
      className={clsx(
        'flex items-center gap-2 rounded-md px-2.5 py-1.5',
        'bg-robot-panel/50 border border-robot-border/40',
        'font-mono text-[10px] uppercase tracking-wider',
        'text-gray-400 hover:text-neon-blue hover:border-cyber-400/40',
        'transition-all duration-300',
        'hover:shadow-[0_0_8px_rgba(0,240,255,0.15)]'
      )}
      aria-label={`Current theme: ${label}. Click to switch.`}
      title={`Theme: ${label} (click to cycle)`}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
    </button>
  );
}
