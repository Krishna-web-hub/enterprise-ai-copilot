/**
 * StaggeredList Component
 *
 * Animates children sequentially as they enter the viewport.
 * Each child gets a staggered delay for a cascading reveal effect.
 */

import { ReactNode, Children } from 'react';
import { motion } from 'framer-motion';

interface StaggeredListProps {
  children: ReactNode;
  /** Delay between each child (seconds) */
  staggerDelay?: number;
  /** Base delay before animation starts */
  baseDelay?: number;
  /** Direction of entrance animation */
  direction?: 'up' | 'down' | 'left' | 'right';
  /** Distance to travel (px) */
  distance?: number;
  /** Duration per item */
  duration?: number;
  /** Only animate once */
  once?: boolean;
  /** Container className */
  className?: string;
}

export default function StaggeredList({
  children,
  staggerDelay = 0.08,
  baseDelay = 0,
  direction = 'up',
  distance = 30,
  duration = 0.5,
  once = true,
  className = '',
}: StaggeredListProps) {
  const getInitial = () => {
    switch (direction) {
      case 'up': return { opacity: 0, y: distance };
      case 'down': return { opacity: 0, y: -distance };
      case 'left': return { opacity: 0, x: -distance };
      case 'right': return { opacity: 0, x: distance };
    }
  };

  const getAnimate = () => {
    switch (direction) {
      case 'up':
      case 'down': return { opacity: 1, y: 0 };
      case 'left':
      case 'right': return { opacity: 1, x: 0 };
    }
  };

  const childArray = Children.toArray(children);

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount: 0.1 }}
    >
      {childArray.map((child, index) => (
        <motion.div
          key={index}
          initial={getInitial()}
          whileInView={getAnimate()}
          viewport={{ once }}
          transition={{
            duration,
            delay: baseDelay + index * staggerDelay,
            ease: [0.22, 1, 0.36, 1],
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
