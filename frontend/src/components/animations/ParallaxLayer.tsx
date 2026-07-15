/**
 * ParallaxLayer Component
 *
 * Creates a depth-based movement effect on scroll.
 * Elements with higher speed values move faster, creating depth illusion.
 * Uses Framer Motion's useScroll + useTransform.
 */

import { ReactNode, useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

interface ParallaxLayerProps {
  children: ReactNode;
  /** Speed multiplier: positive = moves down slower (background feel), negative = moves up */
  speed?: number;
  /** Additional className */
  className?: string;
  /** Horizontal parallax offset */
  horizontal?: number;
}

export default function ParallaxLayer({
  children,
  speed = 0.3,
  horizontal = 0,
  className = '',
}: ParallaxLayerProps) {
  const ref = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });

  // Transform scroll progress (0-1) into pixel offset
  const y = useTransform(scrollYProgress, [0, 1], [speed * 100, -speed * 100]);
  const x = useTransform(scrollYProgress, [0, 1], [horizontal * 50, -horizontal * 50]);

  return (
    <motion.div
      ref={ref}
      className={className}
      style={{ y, x }}
    >
      {children}
    </motion.div>
  );
}
