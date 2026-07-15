/**
 * RippleButton Component
 *
 * A button with an expanding ripple effect on click.
 * Neon-styled ripple that expands from the click point and fades out.
 */

import { useState, useRef, ReactNode, MouseEvent } from 'react';
import clsx from 'clsx';

interface Ripple {
  id: number;
  x: number;
  y: number;
  size: number;
}

interface RippleButtonProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit';
  /** Ripple color (tailwind/css color) */
  rippleColor?: string;
}

export default function RippleButton({
  children,
  className = '',
  onClick,
  disabled = false,
  type = 'button',
  rippleColor = 'rgba(0, 240, 255, 0.3)',
}: RippleButtonProps) {
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const nextId = useRef(0);

  function handleClick(e: MouseEvent<HTMLButtonElement>) {
    if (disabled) return;

    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const size = Math.max(rect.width, rect.height) * 2.5;

    const id = nextId.current++;
    setRipples(prev => [...prev, { id, x, y, size }]);

    // Remove ripple after animation
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== id));
    }, 600);

    onClick?.();
  }

  return (
    <button
      ref={buttonRef}
      type={type}
      onClick={handleClick}
      disabled={disabled}
      className={clsx('relative overflow-hidden', className)}
    >
      {/* Ripple effects */}
      {ripples.map(ripple => (
        <span
          key={ripple.id}
          className="absolute rounded-full pointer-events-none animate-[ripple-expand_0.6s_ease-out_forwards]"
          style={{
            left: ripple.x - ripple.size / 2,
            top: ripple.y - ripple.size / 2,
            width: ripple.size,
            height: ripple.size,
            background: rippleColor,
          }}
        />
      ))}

      {/* Content */}
      <span className="relative z-10">{children}</span>

      <style>{`
        @keyframes ripple-expand {
          0% { transform: scale(0); opacity: 1; }
          100% { transform: scale(1); opacity: 0; }
        }
      `}</style>
    </button>
  );
}
