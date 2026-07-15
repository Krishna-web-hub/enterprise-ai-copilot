/**
 * CountUpOnScroll Component
 *
 * Animates a number from 0 to the target value when it enters the viewport.
 * Uses requestAnimationFrame for smooth count-up with easing.
 */

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

interface CountUpOnScrollProps {
  /** Target number to count up to */
  target: number;
  /** Duration of count animation in ms */
  duration?: number;
  /** Prefix (e.g. "$") */
  prefix?: string;
  /** Suffix (e.g. "%", "+") */
  suffix?: string;
  /** Decimal places */
  decimals?: number;
  /** className for the number */
  className?: string;
  /** Only animate once */
  once?: boolean;
}

export default function CountUpOnScroll({
  target,
  duration = 1500,
  prefix = '',
  suffix = '',
  decimals = 0,
  className = '',
  once = true,
}: CountUpOnScrollProps) {
  const [count, setCount] = useState(0);
  const [hasAnimated, setHasAnimated] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once, amount: 0.5 });

  useEffect(() => {
    if (!isInView) return;
    if (once && hasAnimated) return;
    if (target === 0) { setCount(0); return; }

    setHasAnimated(true);
    const startTime = performance.now();

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(eased * target);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setCount(target);
      }
    }

    requestAnimationFrame(animate);
  }, [isInView, target, duration, once, hasAnimated]);

  const displayValue = decimals > 0
    ? count.toFixed(decimals)
    : Math.floor(count).toLocaleString();

  return (
    <motion.span
      ref={ref}
      className={className}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : {}}
      transition={{ duration: 0.3 }}
    >
      {prefix}{displayValue}{suffix}
    </motion.span>
  );
}
