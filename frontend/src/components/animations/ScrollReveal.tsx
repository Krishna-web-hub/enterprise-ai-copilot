/**
 * ScrollReveal Component
 *
 * Wrapper that reveals its children with animation when they enter the viewport.
 * Uses Framer Motion's whileInView with configurable presets.
 *
 * Presets:
 * - fade-up: fade in + slide up
 * - fade-down: fade in + slide down
 * - fade-left: fade in + slide from left
 * - fade-right: fade in + slide from right
 * - scale: fade in + scale up from 0.8
 * - rotate: fade in + slight rotation
 * - blur: fade in + deblur
 */

import { ReactNode } from 'react';
import { motion } from 'framer-motion';

type RevealPreset = 'fade-up' | 'fade-down' | 'fade-left' | 'fade-right' | 'scale' | 'rotate' | 'blur';

interface ScrollRevealProps {
  children: ReactNode;
  preset?: RevealPreset;
  /** Delay in seconds */
  delay?: number;
  /** Duration in seconds */
  duration?: number;
  /** How much of the element should be visible before triggering (0-1) */
  threshold?: number;
  /** Only animate once */
  once?: boolean;
  /** Additional className */
  className?: string;
}

const presets: Record<RevealPreset, { initial: Record<string, number | string>; animate: Record<string, number | string> }> = {
  'fade-up': {
    initial: { opacity: 0, y: 40 },
    animate: { opacity: 1, y: 0 },
  },
  'fade-down': {
    initial: { opacity: 0, y: -40 },
    animate: { opacity: 1, y: 0 },
  },
  'fade-left': {
    initial: { opacity: 0, x: -40 },
    animate: { opacity: 1, x: 0 },
  },
  'fade-right': {
    initial: { opacity: 0, x: 40 },
    animate: { opacity: 1, x: 0 },
  },
  'scale': {
    initial: { opacity: 0, scale: 0.8 },
    animate: { opacity: 1, scale: 1 },
  },
  'rotate': {
    initial: { opacity: 0, rotate: -5, y: 20 },
    animate: { opacity: 1, rotate: 0, y: 0 },
  },
  'blur': {
    initial: { opacity: 0, filter: 'blur(10px)', y: 20 },
    animate: { opacity: 1, filter: 'blur(0px)', y: 0 },
  },
};

export default function ScrollReveal({
  children,
  preset = 'fade-up',
  delay = 0,
  duration = 0.6,
  threshold = 0.2,
  once = true,
  className = '',
}: ScrollRevealProps) {
  const { initial, animate } = presets[preset];

  return (
    <motion.div
      className={className}
      initial={initial}
      whileInView={animate}
      viewport={{ once, amount: threshold }}
      transition={{
        duration,
        delay,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
