/**
 * AnimatedCircuitSVG Component
 *
 * SVG circuit-board paths that "draw" themselves on page load.
 * Uses stroke-dasharray/dashoffset animation for the reveal effect.
 * Features multiple circuit paths with staggered animations.
 */

import { motion } from 'framer-motion';

interface AnimatedCircuitSVGProps {
  className?: string;
  /** Color of the circuit lines */
  color?: string;
  /** Animation duration per path (seconds) */
  duration?: number;
}

const circuitPaths = [
  // Main horizontal line with branches
  'M 0 50 L 30 50 L 30 30 L 50 30 L 50 50 L 80 50 L 80 70 L 100 70',
  // Diagonal branch
  'M 20 80 L 40 80 L 50 70 L 70 70 L 70 50 L 90 50',
  // Top circuit
  'M 10 20 L 30 20 L 30 10 L 60 10 L 60 20 L 80 20 L 80 30 L 95 30',
  // Bottom circuit
  'M 5 90 L 25 90 L 35 80 L 55 80 L 55 90 L 75 90 L 85 80 L 100 80',
  // Vertical connections
  'M 40 0 L 40 20 L 50 20 L 50 40',
  'M 70 0 L 70 15 L 80 15 L 80 40',
  // More branches
  'M 0 40 L 15 40 L 15 60 L 25 60 L 25 40 L 40 40',
  'M 60 60 L 75 60 L 75 85 L 90 85 L 90 60 L 100 60',
];

// Circuit node positions (dots at intersections)
const nodes = [
  { x: 30, y: 50 }, { x: 50, y: 30 }, { x: 80, y: 50 }, { x: 50, y: 70 },
  { x: 30, y: 20 }, { x: 60, y: 20 }, { x: 70, y: 15 }, { x: 40, y: 20 },
  { x: 25, y: 60 }, { x: 75, y: 60 }, { x: 55, y: 80 }, { x: 90, y: 50 },
];

export default function AnimatedCircuitSVG({
  className = '',
  color = '#00f0ff',
  duration = 2,
}: AnimatedCircuitSVGProps) {
  return (
    <div className={`pointer-events-none ${className}`}>
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Circuit paths */}
        {circuitPaths.map((path, i) => (
          <motion.path
            key={i}
            d={path}
            fill="none"
            stroke={color}
            strokeWidth="0.3"
            strokeLinecap="round"
            opacity={0.4}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.4 }}
            transition={{
              pathLength: { duration: duration, delay: i * 0.3, ease: 'easeInOut' },
              opacity: { duration: 0.5, delay: i * 0.3 },
            }}
          />
        ))}

        {/* Node dots */}
        {nodes.map((node, i) => (
          <motion.circle
            key={`node-${i}`}
            cx={node.x}
            cy={node.y}
            r="0.8"
            fill={color}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 0.6 }}
            transition={{
              delay: duration * 0.5 + i * 0.1,
              duration: 0.3,
              type: 'spring',
            }}
          />
        ))}

        {/* Pulsing glow on select nodes */}
        {nodes.slice(0, 4).map((node, i) => (
          <motion.circle
            key={`glow-${i}`}
            cx={node.x}
            cy={node.y}
            r="0.8"
            fill="none"
            stroke={color}
            strokeWidth="0.2"
            initial={{ scale: 1, opacity: 0 }}
            animate={{ scale: [1, 3, 1], opacity: [0.5, 0, 0.5] }}
            transition={{
              delay: duration + i * 0.5,
              duration: 2,
              repeat: Infinity,
              repeatDelay: 1,
            }}
          />
        ))}
      </svg>
    </div>
  );
}
