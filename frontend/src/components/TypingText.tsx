/**
 * TypingText Component
 *
 * Simulates a robotic typing/streaming effect for headings and labels.
 * Characters appear one by one with a blinking cursor at the end.
 * Gives that "system booting up" or "AI processing" feel.
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface TypingTextProps {
  /** The text to type out */
  text: string;
  /** Speed in ms per character */
  speed?: number;
  /** Delay before starting (ms) */
  delay?: number;
  /** Whether to show blinking cursor */
  showCursor?: boolean;
  /** CSS class for the text */
  className?: string;
  /** Whether the text should glow */
  glow?: boolean;
  /** Callback when typing completes */
  onComplete?: () => void;
}

export default function TypingText({
  text,
  speed = 50,
  delay = 300,
  showCursor = true,
  className = '',
  glow = false,
  onComplete,
}: TypingTextProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    const startTimer = setTimeout(() => {
      setHasStarted(true);
    }, delay);

    return () => clearTimeout(startTimer);
  }, [delay]);

  useEffect(() => {
    if (!hasStarted) return;

    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsComplete(true);
        onComplete?.();
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [hasStarted, text, speed, onComplete]);

  return (
    <motion.span
      className={clsx('inline-flex items-baseline', className)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <span className={clsx(glow && 'text-glow-cyan')}>
        {displayedText}
      </span>

      {/* Blinking cursor */}
      {showCursor && !isComplete && (
        <motion.span
          className="ml-0.5 inline-block w-[2px] h-[1em] bg-neon-blue"
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, repeatType: 'reverse' }}
        />
      )}

      {/* Cursor fades out after completion */}
      {showCursor && isComplete && (
        <motion.span
          className="ml-0.5 inline-block w-[2px] h-[1em] bg-neon-blue"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1, delay: 1 }}
        />
      )}
    </motion.span>
  );
}
