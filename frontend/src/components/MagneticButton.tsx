/**
 * MagneticButton Component
 *
 * A button that slightly "pulls" toward the cursor when hovered,
 * creating a magnetic attraction effect. Springs back when mouse leaves.
 */

import { useRef, useState, ReactNode } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface MagneticButtonProps {
  children: ReactNode;
  className?: string;
  /** Magnetic strength (pixels of max displacement) */
  strength?: number;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit';
}

export default function MagneticButton({
  children,
  className = '',
  strength = 10,
  onClick,
  disabled = false,
  type = 'button',
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  function handleMouseMove(e: React.MouseEvent<HTMLButtonElement>) {
    if (!ref.current || disabled) return;
    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const deltaX = (e.clientX - centerX) / (rect.width / 2);
    const deltaY = (e.clientY - centerY) / (rect.height / 2);

    setPosition({
      x: deltaX * strength,
      y: deltaY * strength,
    });
  }

  function handleMouseLeave() {
    setPosition({ x: 0, y: 0 });
  }

  return (
    <motion.button
      ref={ref}
      type={type}
      className={clsx(className, disabled && 'opacity-50 cursor-not-allowed')}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      disabled={disabled}
      animate={{
        x: position.x,
        y: position.y,
      }}
      transition={{ type: 'spring', stiffness: 200, damping: 15, mass: 0.5 }}
    >
      {children}
    </motion.button>
  );
}
