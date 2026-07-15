/**
 * TiltCard Component
 *
 * A 3D perspective tilt card that responds to mouse position.
 * Uses pure CSS transforms (no Three.js) for performance.
 * Features:
 * - Smooth 3D tilt following cursor
 * - Glare/shine effect on the surface
 * - Spring-back animation on mouse leave
 */

import { useRef, useState, ReactNode } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** Max tilt angle in degrees */
  maxTilt?: number;
  /** Glare effect intensity (0-1) */
  glareIntensity?: number;
  /** Scale on hover */
  hoverScale?: number;
  /** Border glow color */
  glowColor?: string;
  onClick?: () => void;
}

export default function TiltCard({
  children,
  className = '',
  maxTilt = 15,
  glareIntensity = 0.3,
  hoverScale = 1.02,
  glowColor = 'rgba(0, 240, 255, 0.2)',
  onClick,
}: TiltCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ rotateX: 0, rotateY: 0 });
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50 });
  const [isHovered, setIsHovered] = useState(false);

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Normalized -1 to 1
    const percentX = (e.clientX - centerX) / (rect.width / 2);
    const percentY = (e.clientY - centerY) / (rect.height / 2);

    setTransform({
      rotateX: -percentY * maxTilt,
      rotateY: percentX * maxTilt,
    });

    // Glare position (percentage)
    setGlarePos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  }

  function handleMouseLeave() {
    setIsHovered(false);
    setTransform({ rotateX: 0, rotateY: 0 });
  }

  function handleMouseEnter() {
    setIsHovered(true);
  }

  return (
    <motion.div
      ref={cardRef}
      className={clsx('relative', onClick && 'cursor-pointer', className)}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      animate={{
        rotateX: transform.rotateX,
        rotateY: transform.rotateY,
        scale: isHovered ? hoverScale : 1,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      style={{
        transformStyle: 'preserve-3d',
        perspective: '1000px',
        boxShadow: isHovered
          ? `0 20px 40px rgba(0,0,0,0.3), 0 0 20px ${glowColor}`
          : '0 4px 12px rgba(0,0,0,0.2)',
      }}
    >
      {children}

      {/* Glare overlay */}
      {isHovered && (
        <div
          className="pointer-events-none absolute inset-0 rounded-xl overflow-hidden"
          style={{ transform: 'translateZ(1px)' }}
        >
          <div
            className="absolute inset-0 transition-opacity duration-200"
            style={{
              background: `radial-gradient(circle at ${glarePos.x}% ${glarePos.y}%, rgba(255,255,255,${glareIntensity}), transparent 60%)`,
            }}
          />
        </div>
      )}
    </motion.div>
  );
}
