/**
 * TextScramble Component
 *
 * Randomizes characters before resolving to actual text.
 * Creates a "decrypting" / "decoding" effect like in sci-fi movies.
 * Characters cycle through random glyphs before settling.
 */

import { useEffect, useState, useCallback } from 'react';
import clsx from 'clsx';

interface TextScrambleProps {
  /** Final text to display */
  text: string;
  /** Speed of scramble (ms per frame) */
  speed?: number;
  /** Delay before starting (ms) */
  delay?: number;
  /** Characters to use for scrambling */
  chars?: string;
  /** CSS class */
  className?: string;
  /** Whether text should glow */
  glow?: boolean;
  /** Trigger re-scramble when this changes */
  trigger?: unknown;
}

const DEFAULT_CHARS = '!<>-_\\/[]{}—=+*^?#________ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

export default function TextScramble({
  text,
  speed = 30,
  delay = 200,
  chars = DEFAULT_CHARS,
  className = '',
  glow = false,
  trigger,
}: TextScrambleProps) {
  const [displayText, setDisplayText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  const scramble = useCallback(() => {
    setIsComplete(false);
    let iteration = 0;
    const length = text.length;

    const startTimeout = setTimeout(() => {
      const interval = setInterval(() => {
        const result = text
          .split('')
          .map((char, index) => {
            if (char === ' ') return ' ';
            if (index < iteration) return text[index];
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join('');

        setDisplayText(result);
        iteration += 1 / 3; // Slower reveal

        if (iteration >= length) {
          clearInterval(interval);
          setDisplayText(text);
          setIsComplete(true);
        }
      }, speed);

      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(startTimeout);
  }, [text, speed, delay, chars]);

  useEffect(() => {
    const cleanup = scramble();
    return cleanup;
  }, [scramble, trigger]);

  return (
    <span
      className={clsx(
        'inline-block font-mono',
        glow && isComplete && 'text-glow-cyan',
        !isComplete && 'text-cyber-400/80',
        className
      )}
    >
      {displayText || '\u00A0'.repeat(text.length)}
    </span>
  );
}
