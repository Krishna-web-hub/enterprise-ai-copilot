/**
 * CursorGlow Component
 *
 * Custom cursor with trailing glow effect (dark mode only).
 * Features:
 * - Smooth following with spring physics (slight lag for elegance)
 * - Neon glow that expands on click
 * - Fades trail dots behind the cursor
 * - Only renders in dark mode
 */

import { useEffect, useState, useRef } from 'react';
import { motion, useSpring, useMotionValue } from 'framer-motion';
import { useTheme } from '../context/ThemeContext';

export default function CursorGlow() {
  const { resolvedTheme } = useTheme();
  const [isVisible, setIsVisible] = useState(false);
  const [isClicking, setIsClicking] = useState(false);
  const cursorX = useMotionValue(0);
  const cursorY = useMotionValue(0);

  // Spring-smoothed position (follows with delay)
  const springX = useSpring(cursorX, { stiffness: 300, damping: 28 });
  const springY = useSpring(cursorY, { stiffness: 300, damping: 28 });

  // Trail dots
  const [trail, setTrail] = useState<{ id: number; x: number; y: number }[]>([]);
  const trailId = useRef(0);

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      cursorX.set(e.clientX);
      cursorY.set(e.clientY);
      setIsVisible(true);

      // Add trail dot every few pixels of movement
      const id = trailId.current++;
      setTrail(prev => [...prev.slice(-5), { id, x: e.clientX, y: e.clientY }]);
    }

    function handleMouseDown() { setIsClicking(true); }
    function handleMouseUp() { setIsClicking(false); }
    function handleMouseLeave() { setIsVisible(false); }
    function handleMouseEnter() { setIsVisible(true); }

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [cursorX, cursorY]);

  // Remove old trail dots
  useEffect(() => {
    if (trail.length === 0) return;
    const timer = setTimeout(() => {
      setTrail(prev => prev.slice(1));
    }, 100);
    return () => clearTimeout(timer);
  }, [trail]);

  // Don't render if hidden
  const isDark = resolvedTheme === 'dark';
  const glowColor = isDark ? 'rgba(0, 240, 255, 0.4)' : 'rgba(8, 145, 178, 0.3)';
  const dotColor = isDark ? 'bg-neon-blue/60' : 'bg-cyber-500/50';
  const trailColor = isDark ? 'bg-neon-blue/30' : 'bg-cyber-500/20';

  return (
    <div className="pointer-events-none fixed inset-0 z-[9990]" style={{ display: isVisible ? 'block' : 'none' }}>
      {/* Trail dots */}
      {trail.map((dot, idx) => (
        <div
          key={dot.id}
          className={`absolute w-1 h-1 rounded-full ${trailColor}`}
          style={{
            left: dot.x - 2,
            top: dot.y - 2,
            opacity: (idx + 1) / trail.length * 0.4,
            transform: `scale(${(idx + 1) / trail.length})`,
          }}
        />
      ))}

      {/* Main glow circle */}
      <motion.div
        className="absolute"
        style={{
          x: springX,
          y: springY,
          translateX: '-50%',
          translateY: '-50%',
        }}
      >
        {/* Outer glow */}
        <motion.div
          className="rounded-full"
          animate={{
            width: isClicking ? 40 : 24,
            height: isClicking ? 40 : 24,
            opacity: isClicking ? 0.4 : 0.2,
          }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          style={{
            background: `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`,
            marginLeft: isClicking ? -20 : -12,
            marginTop: isClicking ? -20 : -12,
          }}
        />

        {/* Inner dot */}
        <motion.div
          className={`absolute rounded-full ${dotColor}`}
          animate={{
            width: isClicking ? 6 : 4,
            height: isClicking ? 6 : 4,
          }}
          style={{
            top: '50%',
            left: '50%',
            translateX: '-50%',
            translateY: '-50%',
            boxShadow: isDark ? '0 0 6px rgba(0, 240, 255, 0.8)' : '0 0 6px rgba(8, 145, 178, 0.5)',
          }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </motion.div>
    </div>
  );
}
