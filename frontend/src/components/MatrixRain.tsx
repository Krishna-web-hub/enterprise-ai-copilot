/**
 * MatrixRain Component
 *
 * A canvas-based "code rain" effect inspired by The Matrix.
 * Characters fall vertically with varying speeds and opacities.
 * Renders on a transparent canvas as a background layer.
 */

import { useEffect, useRef } from 'react';

interface MatrixRainProps {
  /** CSS class for container */
  className?: string;
  /** Color of the characters */
  color?: string;
  /** Font size of characters */
  fontSize?: number;
  /** Opacity of the entire effect (0-1) */
  opacity?: number;
  /** Speed multiplier */
  speed?: number;
}

const CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<>{}[]|/\\';

export default function MatrixRain({
  className = '',
  color = '#00f0ff',
  fontSize = 12,
  opacity = 0.06,
  speed = 1,
}: MatrixRainProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = canvas.offsetWidth;
    let height = canvas.offsetHeight;
    canvas.width = width;
    canvas.height = height;

    const columns = Math.floor(width / fontSize);
    const drops: number[] = new Array(columns).fill(0).map(() => Math.random() * -100);

    function draw() {
      if (!ctx || !canvas) return;

      // Semi-transparent black overlay to create fade trail
      ctx.fillStyle = `rgba(10, 14, 26, 0.05)`;
      ctx.fillRect(0, 0, width, height);

      ctx.fillStyle = color;
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const charIdx = Math.floor(Math.random() * CHARS.length);
        const char = CHARS[charIdx] ?? '0';
        const x = i * fontSize;
        const y = (drops[i] ?? 0) * fontSize;

        // Varying opacity per column
        const colOpacity = 0.3 + Math.random() * 0.7;
        ctx.globalAlpha = colOpacity;
        ctx.fillText(char, x, y);

        // Reset drop when it goes off screen (with randomness)
        if (y > height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i] = (drops[i] ?? 0) + speed * (0.5 + Math.random() * 0.5);
      }

      ctx.globalAlpha = 1;
      animFrameRef.current = requestAnimationFrame(draw);
    }

    // Handle resize
    function handleResize() {
      if (!canvas) return;
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width;
      canvas.height = height;
    }

    window.addEventListener('resize', handleResize);
    animFrameRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [color, fontSize, speed]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none ${className}`}
      style={{ opacity }}
    />
  );
}
