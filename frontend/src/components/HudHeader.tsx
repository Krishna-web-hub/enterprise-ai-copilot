/**
 * HUD Header Component - Dual Mode
 *
 * Top bar with system status — adapts to light/dark mode.
 */

import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Activity, Shield, Clock, Zap } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import clsx from 'clsx';
import ThemeToggleButton from './ThemeToggleButton';

const routeLabels: Record<string, string> = {
  '/app': 'Dashboard',
  '/app/chat': 'Communication Hub',
  '/app/datasets': 'Data Repository',
  '/app/ask-data': 'Query Engine',
  '/app/documents': 'Document Vault',
  '/app/models': 'Model Registry',
  '/app/reports': 'Report Generator',
};

export default function HudHeader() {
  const location = useLocation();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const currentRoute = routeLabels[location.pathname] || 'System';

  const timeStr = time.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  const dateStr = time.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });

  return (
    <header className={clsx(
      'relative flex h-12 items-center justify-between border-b px-6',
      isDark ? 'border-robot-border/30 bg-robot-darker/80 backdrop-blur-sm' : 'border-gray-100 bg-white/60 backdrop-blur-xl shadow-sm'
    )}>
      {/* Left: breadcrumb */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Zap className={clsx('h-3.5 w-3.5', isDark ? 'text-neon-blue/70' : 'text-cyber-500')} />
          <span className={clsx('font-mono text-[10px] uppercase tracking-wider', isDark ? 'text-gray-500' : 'text-gray-400')}>SYS://</span>
          <span className={clsx('font-mono text-xs tracking-wide', isDark ? 'text-cyber-400' : 'text-cyber-700 font-medium')}>{currentRoute}</span>
        </div>

        <span className={clsx('w-1 h-1 rounded-full', isDark ? 'bg-robot-border' : 'bg-gray-300')} />

        <div className="flex items-center gap-1.5">
          <Activity className={clsx('h-3 w-3 animate-glow-pulse', isDark ? 'text-neon-green/60' : 'text-emerald-500/60')} />
          <span className={clsx('font-mono text-[9px] uppercase', isDark ? 'text-gray-600' : 'text-gray-500')}>Active</span>
        </div>
      </div>

      {/* Center accent line */}
      <div className={clsx(
        'absolute left-1/2 -translate-x-1/2 top-full w-32 h-[1px] bg-gradient-to-r from-transparent to-transparent',
        isDark ? 'via-cyber-400/20' : 'via-gray-200'
      )} />

      {/* Right: clock + status + theme */}
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-1.5">
          <Shield className={clsx('h-3 w-3', isDark ? 'text-cyber-400/50' : 'text-cyber-600/50')} />
          <span className={clsx('font-mono text-[9px] uppercase', isDark ? 'text-gray-600' : 'text-gray-500')}>Encrypted</span>
        </div>

        <div className={clsx(
          'flex items-center gap-2 rounded-md border px-2.5 py-1',
          isDark ? 'bg-robot-panel/50 border-robot-border/30' : 'bg-gray-50 border-gray-200'
        )}>
          <Clock className={clsx('h-3 w-3', isDark ? 'text-cyber-400/60' : 'text-cyber-600/50')} />
          <span className={clsx('font-mono text-[10px] tabular-nums', isDark ? 'text-gray-400' : 'text-gray-600')}>{timeStr}</span>
          <span className={clsx('hidden sm:inline font-mono text-[9px]', isDark ? 'text-gray-600' : 'text-gray-400')}>|</span>
          <span className={clsx('hidden sm:inline font-mono text-[9px]', isDark ? 'text-gray-600' : 'text-gray-400')}>{dateStr}</span>
        </div>

        <ThemeToggleButton />
      </div>
    </header>
  );
}
