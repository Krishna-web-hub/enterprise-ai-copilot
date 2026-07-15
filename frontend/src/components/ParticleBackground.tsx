/**
 * ParticleBackground Component
 *
 * Renders an animated neural-network / circuit-board style particle background
 * using tsParticles. Particles connect with lines to simulate neural links.
 * Responds to mouse movement for an interactive feel.
 *
 * Uses ParticlesProvider for engine initialization (v4 API).
 */

import { useMemo } from 'react';
import { Particles, ParticlesProvider } from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import type { ISourceOptions, Engine } from '@tsparticles/engine';

interface ParticleBackgroundProps {
  /** Intensity: 'low' for subtle bg, 'medium' for pages, 'high' for hero sections */
  intensity?: 'low' | 'medium' | 'high';
  /** Primary color of particles (hex) */
  color?: string;
  /** Secondary color for links (hex) */
  linkColor?: string;
  /** Additional CSS class */
  className?: string;
}

const intensityConfig = {
  low: { count: 30, linkOpacity: 0.08, moveSpeed: 0.3, size: { min: 0.5, max: 1.5 } },
  medium: { count: 60, linkOpacity: 0.15, moveSpeed: 0.5, size: { min: 0.5, max: 2 } },
  high: { count: 100, linkOpacity: 0.2, moveSpeed: 0.8, size: { min: 1, max: 3 } },
};

async function particlesInit(engine: Engine): Promise<void> {
  await loadSlim(engine);
}

function ParticlesInner({
  intensity = 'medium',
  color = '#00f0ff',
  linkColor = '#00f0ff',
  className = '',
}: ParticleBackgroundProps) {
  const config = intensityConfig[intensity];

  const options: ISourceOptions = useMemo(
    () => ({
      fullScreen: false,
      fpsLimit: 60,
      particles: {
        number: {
          value: config.count,
          density: {
            enable: true,
          },
        },
        color: {
          value: color,
        },
        shape: {
          type: 'circle',
        },
        opacity: {
          value: { min: 0.1, max: 0.5 },
          animation: {
            enable: true,
            speed: 0.5,
            sync: false,
          },
        },
        size: {
          value: config.size,
          animation: {
            enable: true,
            speed: 1,
            sync: false,
          },
        },
        links: {
          enable: true,
          distance: 150,
          color: linkColor,
          opacity: config.linkOpacity,
          width: 1,
          triangles: {
            enable: true,
            opacity: 0.02,
          },
        },
        move: {
          enable: true,
          speed: config.moveSpeed,
          direction: 'none' as const,
          random: true,
          straight: false,
          outModes: {
            default: 'bounce' as const,
          },
          attract: {
            enable: true,
            rotate: {
              x: 600,
              y: 1200,
            },
          },
        },
      },
      interactivity: {
        events: {
          onHover: {
            enable: true,
            mode: 'grab',
          },
          onClick: {
            enable: true,
            mode: 'push',
          },
        },
        modes: {
          grab: {
            distance: 180,
            links: {
              opacity: 0.4,
              color: color,
            },
          },
          push: {
            quantity: 2,
          },
        },
      },
      detectRetina: true,
      background: {
        color: 'transparent',
      },
    }),
    [config, color, linkColor]
  );

  return (
    <Particles
      className={`absolute inset-0 ${className}`}
      options={options}
    />
  );
}

export default function ParticleBackground(props: ParticleBackgroundProps) {
  return (
    <ParticlesProvider init={particlesInit}>
      <ParticlesInner {...props} />
    </ParticlesProvider>
  );
}
