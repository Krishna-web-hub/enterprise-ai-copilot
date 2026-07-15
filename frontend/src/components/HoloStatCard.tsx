/**
 * HoloStatCard Component
 *
 * A stat card that adapts between:
 * - Dark mode: holographic HUD-style with glow and scan effects
 * - Light mode: clean elevated card with colored accent and soft shadow
 */

import { useEffect, useState, useRef } from 'react';
import { motion, Variants } from 'framer-motion';
import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface HoloStatCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  color?: 'cyan' | 'purple' | 'green' | 'orange' | 'blue';
  onClick?: () => void;
  variants?: Variants;
  code?: string;
}

const darkColorMap = {
  cyan: { iconBg: 'bg-cyber-400/15', iconColor: 'text-neon-blue', border: 'border-cyber-400/20 hover:border-cyber-400/50', glow: 'rgba(0, 240, 255, 0.2)', gradient: 'from-cyber-400/10 via-transparent to-transparent', dotColor: 'bg-neon-blue' },
  purple: { iconBg: 'bg-purple-500/15', iconColor: 'text-neon-purple', border: 'border-purple-500/20 hover:border-purple-500/50', glow: 'rgba(191, 0, 255, 0.2)', gradient: 'from-purple-500/10 via-transparent to-transparent', dotColor: 'bg-neon-purple' },
  green: { iconBg: 'bg-emerald-400/15', iconColor: 'text-neon-green', border: 'border-emerald-400/20 hover:border-emerald-400/50', glow: 'rgba(0, 255, 136, 0.2)', gradient: 'from-emerald-400/10 via-transparent to-transparent', dotColor: 'bg-neon-green' },
  orange: { iconBg: 'bg-orange-400/15', iconColor: 'text-neon-orange', border: 'border-orange-400/20 hover:border-orange-400/50', glow: 'rgba(255, 107, 0, 0.2)', gradient: 'from-orange-400/10 via-transparent to-transparent', dotColor: 'bg-neon-orange' },
  blue: { iconBg: 'bg-blue-500/15', iconColor: 'text-blue-400', border: 'border-blue-500/20 hover:border-blue-500/50', glow: 'rgba(59, 130, 246, 0.2)', gradient: 'from-blue-500/10 via-transparent to-transparent', dotColor: 'bg-blue-400' },
};

const lightColorMap = {
  cyan: { iconBg: 'bg-cyan-50', iconColor: 'text-cyan-600', border: 'border-cyan-100 hover:border-cyan-300', shadow: '0 4px 20px rgba(6, 182, 212, 0.12)', accentLine: 'bg-gradient-to-r from-cyan-400 to-teal-400' },
  purple: { iconBg: 'bg-purple-50', iconColor: 'text-purple-600', border: 'border-purple-100 hover:border-purple-300', shadow: '0 4px 20px rgba(139, 92, 246, 0.12)', accentLine: 'bg-gradient-to-r from-purple-400 to-violet-400' },
  green: { iconBg: 'bg-emerald-50', iconColor: 'text-emerald-600', border: 'border-emerald-100 hover:border-emerald-300', shadow: '0 4px 20px rgba(16, 185, 129, 0.12)', accentLine: 'bg-gradient-to-r from-emerald-400 to-teal-400' },
  orange: { iconBg: 'bg-orange-50', iconColor: 'text-orange-600', border: 'border-orange-100 hover:border-orange-300', shadow: '0 4px 20px rgba(251, 146, 60, 0.12)', accentLine: 'bg-gradient-to-r from-orange-400 to-amber-400' },
  blue: { iconBg: 'bg-blue-50', iconColor: 'text-blue-600', border: 'border-blue-100 hover:border-blue-300', shadow: '0 4px 20px rgba(59, 130, 246, 0.12)', accentLine: 'bg-gradient-to-r from-blue-400 to-indigo-400' },
};

function useCountUp(target: number, duration: number = 1500): number {
  const [count, setCount] = useState(0);
  const startTime = useRef<number | null>(null);
  const rafId = useRef<number>(0);

  useEffect(() => {
    if (target === 0) { setCount(0); return; }
    startTime.current = null;

    function animate(timestamp: number) {
      if (!startTime.current) startTime.current = timestamp;
      const progress = Math.min((timestamp - startTime.current) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * target));
      if (progress < 1) rafId.current = requestAnimationFrame(animate);
    }

    rafId.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId.current);
  }, [target, duration]);

  return count;
}

export default function HoloStatCard({
  label,
  value,
  icon: Icon,
  color = 'cyan',
  onClick,
  variants,
  code,
}: HoloStatCardProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const darkColors = darkColorMap[color];
  const lightColors = lightColorMap[color];
  const displayCount = useCountUp(value);
  const [isHovered, setIsHovered] = useState(false);

  // ─── LIGHT MODE CARD ────────────────────────────────────────
  if (!isDark) {
    return (
      <motion.button
        variants={variants}
        onClick={onClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={clsx(
          'group relative overflow-hidden rounded-xl border p-5 text-left transition-all duration-300 bg-white',
          lightColors.border,
          onClick && 'cursor-pointer'
        )}
        style={{ boxShadow: isHovered ? lightColors.shadow : '0 1px 8px rgba(0,0,0,0.04)' }}
        whileHover={{ scale: 1.03, y: -4 }}
        whileTap={{ scale: 0.97 }}
      >
        {/* Top accent line */}
        <div className={clsx('absolute top-0 left-0 right-0 h-[3px] rounded-t-xl', lightColors.accentLine)} />

        {/* Module code */}
        {code && (
          <span className="absolute top-3 right-4 font-mono text-[8px] tracking-widest text-gray-400 uppercase">{code}</span>
        )}

        {/* Content */}
        <div className="relative z-10 flex items-start gap-4 pt-1">
          <div className={clsx('flex h-11 w-11 items-center justify-center rounded-xl transition-all duration-300', lightColors.iconBg, 'group-hover:scale-110')}>
            <Icon className={clsx('h-5 w-5', lightColors.iconColor)} />
          </div>
          <div className="flex-1">
            <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500 mb-1">{label}</p>
            <p className="font-mono text-2xl font-bold text-gray-900 tabular-nums">{displayCount}</p>
          </div>
        </div>
      </motion.button>
    );
  }

  // ─── DARK MODE CARD (original holographic style) ────────────
  return (
    <motion.button
      variants={variants}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={clsx(
        'group relative overflow-hidden rounded-xl border p-5 text-left transition-all duration-300',
        'bg-robot-panel/60 backdrop-blur-sm',
        darkColors.border,
        onClick && 'cursor-pointer'
      )}
      style={isHovered ? { boxShadow: `0 0 25px ${darkColors.glow}, inset 0 0 25px ${darkColors.glow.replace('0.2', '0.05')}` } : undefined}
      whileHover={{ scale: 1.03, y: -4 }}
      whileTap={{ scale: 0.97 }}
    >
      {/* Top gradient line */}
      <div className={clsx('absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r', darkColors.gradient)} />

      {/* Scan effect on hover */}
      {isHovered && (
        <motion.div
          className="absolute inset-0 opacity-30"
          style={{ background: `linear-gradient(180deg, transparent 0%, ${darkColors.glow} 50%, transparent 100%)`, height: '40px' }}
          animate={{ top: ['-40px', '100%'] }}
          transition={{ duration: 1, ease: 'linear' }}
        />
      )}

      {/* HUD corners */}
      <span className="absolute top-2 left-2 w-3 h-3">
        <span className={clsx('absolute top-0 left-0 w-full h-[1px]', darkColors.dotColor, 'opacity-40')} />
        <span className={clsx('absolute top-0 left-0 w-[1px] h-full', darkColors.dotColor, 'opacity-40')} />
      </span>
      <span className="absolute top-2 right-2 w-3 h-3">
        <span className={clsx('absolute top-0 right-0 w-full h-[1px]', darkColors.dotColor, 'opacity-40')} />
        <span className={clsx('absolute top-0 right-0 w-[1px] h-full', darkColors.dotColor, 'opacity-40')} />
      </span>
      <span className="absolute bottom-2 left-2 w-3 h-3">
        <span className={clsx('absolute bottom-0 left-0 w-full h-[1px]', darkColors.dotColor, 'opacity-40')} />
        <span className={clsx('absolute bottom-0 left-0 w-[1px] h-full', darkColors.dotColor, 'opacity-40')} />
      </span>
      <span className="absolute bottom-2 right-2 w-3 h-3">
        <span className={clsx('absolute bottom-0 right-0 w-full h-[1px]', darkColors.dotColor, 'opacity-40')} />
        <span className={clsx('absolute bottom-0 right-0 w-[1px] h-full', darkColors.dotColor, 'opacity-40')} />
      </span>

      {/* Module code */}
      {code && (
        <span className="absolute top-3 right-4 font-mono text-[8px] tracking-widest text-gray-600 uppercase">{code}</span>
      )}

      {/* Content */}
      <div className="relative z-10 flex items-start gap-4">
        <div className={clsx('flex h-11 w-11 items-center justify-center rounded-lg transition-all duration-300', darkColors.iconBg, 'group-hover:scale-110')}>
          <Icon className={clsx('h-5 w-5', darkColors.iconColor)} />
        </div>
        <div className="flex-1">
          <p className="font-mono text-[10px] uppercase tracking-widest text-gray-500 mb-1">{label}</p>
          <p className="font-mono text-2xl font-bold text-white tabular-nums">{displayCount}</p>
        </div>
      </div>

      {/* Bottom accent */}
      <div className={clsx('absolute bottom-0 left-4 right-4 h-[1px] transition-opacity duration-300', isHovered ? 'opacity-100' : 'opacity-0')}
        style={{ background: `linear-gradient(90deg, transparent, ${darkColors.glow}, transparent)` }} />
    </motion.button>
  );
}
