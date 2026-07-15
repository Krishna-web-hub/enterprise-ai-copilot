/**
 * AnimatedNumber Component
 *
 * Smoothly transitions between number values when data changes.
 * Uses spring physics for a natural feel. Supports formatting.
 */

import { useEffect, useRef, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  /** Target value */
  value: number;
  /** Duration in seconds */
  duration?: number;
  /** Decimal places */
  decimals?: number;
  /** Prefix (e.g. "$") */
  prefix?: string;
  /** Suffix (e.g. "%") */
  suffix?: string;
  /** Use locale formatting (commas) */
  locale?: boolean;
  /** className */
  className?: string;
}

export default function AnimatedNumber({
  value,
  duration = 0.8,
  decimals = 0,
  prefix = '',
  suffix = '',
  locale = true,
  className = '',
}: AnimatedNumberProps) {
  const spring = useSpring(0, {
    stiffness: 100,
    damping: 30,
    duration: duration * 1000,
  });

  const display = useTransform(spring, (latest) => {
    if (locale && decimals === 0) {
      return `${prefix}${Math.round(latest).toLocaleString()}${suffix}`;
    }
    return `${prefix}${latest.toFixed(decimals)}${suffix}`;
  });

  const [displayValue, setDisplayValue] = useState(`${prefix}0${suffix}`);
  const prevValue = useRef(0);

  useEffect(() => {
    spring.set(value);
    prevValue.current = value;
  }, [value, spring]);

  useEffect(() => {
    const unsubscribe = display.on('change', (v) => {
      setDisplayValue(v);
    });
    return unsubscribe;
  }, [display]);

  return (
    <motion.span className={className}>
      {displayValue}
    </motion.span>
  );
}
