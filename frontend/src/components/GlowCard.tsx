/**
 * GlowCard Component
 *
 * A reusable glassmorphism card with animated glowing border effect.
 * Features HUD-style corner brackets and cursor-responsive glow.
 * Designed for the robotic AI aesthetic.
 */

import { useRef, useState, ReactNode } from 'react';
import { motion, Variants } from 'framer-motion';
import clsx from 'clsx';

interface GlowCardProps {
  children: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show HUD corner brackets */
  hudCorners?: boolean;
  /** Glow color variant */
  glowColor?: 'cyan' | 'purple' | 'green' | 'orange';
  /** Whether the card has hover glow effect */
  hoverGlow?: boolean;
  /** Whether to enable cursor-tracking gradient */
  cursorGlow?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Framer motion variants for stagger animations */
  variants?: Variants;
}

const glowColorMap = {
  cyan: {
    border: 'border-cyber-400/20 hover:border-cyber-400/50',
    shadow: 'rgba(0, 240, 255, 0.15)',
    gradient: 'from-cyber-400/10 to-transparent',
    corner: 'bg-neon-blue',
  },
  purple: {
    border: 'border-purple-500/20 hover:border-purple-500/50',
    shadow: 'rgba(191, 0, 255, 0.15)',
    gradient: 'from-purple-500/10 to-transparent',
    corner: 'bg-neon-purple',
  },
  green: {
    border: 'border-emerald-400/20 hover:border-emerald-400/50',
    shadow: 'rgba(0, 255, 136, 0.15)',
    gradient: 'from-emerald-400/10 to-transparent',
    corner: 'bg-neon-green',
  },
  orange: {
    border: 'border-orange-400/20 hover:border-orange-400/50',
    shadow: 'rgba(255, 107, 0, 0.15)',
    gradient: 'from-orange-400/10 to-transparent',
    corner: 'bg-neon-orange',
  },
};

export default function GlowCard({
  children,
  className = '',
  hudCorners = false,
  glowColor = 'cyan',
  hoverGlow = true,
  cursorGlow = true,
  onClick,
  variants,
}: GlowCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const colors = glowColorMap[glowColor];

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!cursorGlow || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  }

  return (
    <motion.div
      ref={cardRef}
      variants={variants}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      className={clsx(
        'relative overflow-hidden rounded-xl border transition-all duration-300',
        'bg-robot-panel/80 backdrop-blur-md',
        colors.border,
        hoverGlow && 'hover:shadow-lg',
        onClick && 'cursor-pointer',
        className
      )}
      style={
        hoverGlow && isHovered
          ? { boxShadow: `0 0 20px ${colors.shadow}, inset 0 0 20px ${colors.shadow.replace('0.15', '0.05')}` }
          : undefined
      }
      whileHover={onClick ? { scale: 1.02, y: -2 } : undefined}
      whileTap={onClick ? { scale: 0.98 } : undefined}
    >
      {/* Cursor-following radial glow */}
      {cursorGlow && isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-xl opacity-60 transition-opacity duration-300"
          style={{
            background: `radial-gradient(300px circle at ${mousePos.x}px ${mousePos.y}px, ${colors.shadow}, transparent 60%)`,
          }}
        />
      )}

      {/* Top gradient accent line */}
      <div className={clsx('absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r', colors.gradient)} />

      {/* HUD corner brackets */}
      {hudCorners && (
        <>
          <span className={clsx('hud-corner hud-corner--tl top-2 left-2', `before:${colors.corner} after:${colors.corner}`)}>
            <span className={clsx('absolute top-0 left-0 w-full h-[1px]', colors.corner)} />
            <span className={clsx('absolute top-0 left-0 w-[1px] h-full', colors.corner)} />
          </span>
          <span className="hud-corner hud-corner--tr top-2 right-2">
            <span className={clsx('absolute top-0 right-0 w-full h-[1px]', colors.corner)} />
            <span className={clsx('absolute top-0 right-0 w-[1px] h-full', colors.corner)} />
          </span>
          <span className="hud-corner hud-corner--bl bottom-2 left-2">
            <span className={clsx('absolute bottom-0 left-0 w-full h-[1px]', colors.corner)} />
            <span className={clsx('absolute bottom-0 left-0 w-[1px] h-full', colors.corner)} />
          </span>
          <span className="hud-corner hud-corner--br bottom-2 right-2">
            <span className={clsx('absolute bottom-0 right-0 w-full h-[1px]', colors.corner)} />
            <span className={clsx('absolute bottom-0 right-0 w-[1px] h-full', colors.corner)} />
          </span>
        </>
      )}

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
