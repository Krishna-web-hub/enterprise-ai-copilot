/**
 * CyberGrid Component
 *
 * Renders an animated grid/circuit-line background with floating orbs.
 * Used as a page background layer to give depth and movement.
 * Features subtle animated gradient orbs and a perspective grid.
 */

import { motion } from 'framer-motion';

interface CyberGridProps {
  /** Show floating orbs */
  showOrbs?: boolean;
  /** Show the perspective grid lines */
  showGrid?: boolean;
  /** Number of floating orbs */
  orbCount?: number;
  /** Additional classes */
  className?: string;
}

export default function CyberGrid({
  showOrbs = true,
  showGrid = true,
  orbCount = 3,
  className = '',
}: CyberGridProps) {
  const orbs = Array.from({ length: orbCount }, (_, i) => ({
    id: i,
    size: 200 + Math.random() * 300,
    x: Math.random() * 100,
    y: Math.random() * 100,
    duration: 15 + Math.random() * 10,
    delay: i * 2,
    color: i % 2 === 0 ? 'rgba(0, 240, 255, 0.08)' : 'rgba(191, 0, 255, 0.06)',
  }));

  return (
    <div className={`pointer-events-none fixed inset-0 overflow-hidden ${className}`}>
      {/* Base grid pattern */}
      {showGrid && (
        <div className="absolute inset-0 bg-cyber-grid opacity-60" />
      )}

      {/* Radial gradient from center - gives a focal glow */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, rgba(0, 240, 255, 0.03) 0%, transparent 60%)',
        }}
      />

      {/* Floating gradient orbs */}
      {showOrbs &&
        orbs.map((orb) => (
          <motion.div
            key={orb.id}
            className="absolute rounded-full blur-3xl"
            style={{
              width: orb.size,
              height: orb.size,
              left: `${orb.x}%`,
              top: `${orb.y}%`,
              background: `radial-gradient(circle, ${orb.color} 0%, transparent 70%)`,
            }}
            animate={{
              x: [0, 50, -30, 20, 0],
              y: [0, -40, 20, -60, 0],
              scale: [1, 1.1, 0.9, 1.05, 1],
            }}
            transition={{
              duration: orb.duration,
              delay: orb.delay,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}

      {/* Horizontal scan line that slowly moves down */}
      <motion.div
        className="absolute left-0 right-0 h-[1px]"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(0, 240, 255, 0.3) 50%, transparent 100%)',
        }}
        animate={{ top: ['-5%', '105%'] }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'linear',
        }}
      />

      {/* Vertical accent lines at edges */}
      <div
        className="absolute top-0 left-[20%] bottom-0 w-[1px] opacity-20"
        style={{
          background: 'linear-gradient(180deg, transparent 0%, rgba(0, 240, 255, 0.3) 30%, rgba(0, 240, 255, 0.3) 70%, transparent 100%)',
        }}
      />
      <div
        className="absolute top-0 right-[20%] bottom-0 w-[1px] opacity-20"
        style={{
          background: 'linear-gradient(180deg, transparent 0%, rgba(191, 0, 255, 0.3) 30%, rgba(191, 0, 255, 0.3) 70%, transparent 100%)',
        }}
      />

      {/* Corner accent dots */}
      <div className="absolute top-8 left-8 w-1 h-1 rounded-full bg-neon-blue/40" />
      <div className="absolute top-8 right-8 w-1 h-1 rounded-full bg-neon-blue/40" />
      <div className="absolute bottom-8 left-8 w-1 h-1 rounded-full bg-neon-purple/40" />
      <div className="absolute bottom-8 right-8 w-1 h-1 rounded-full bg-neon-purple/40" />
    </div>
  );
}
