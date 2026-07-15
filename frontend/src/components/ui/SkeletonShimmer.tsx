/**
 * SkeletonShimmer Component
 *
 * Animated loading placeholder with a sweeping neon shimmer effect.
 * Supports various shapes: line, circle, card, stat-card, and custom.
 */

import React from 'react';
import clsx from 'clsx';

interface SkeletonShimmerProps {
  /** Preset shape */
  variant?: 'line' | 'circle' | 'card' | 'stat-card';
  /** Width (for line/custom) */
  width?: string;
  /** Height (for line/custom) */
  height?: string;
  /** Number of lines (for line variant) */
  lines?: number;
  /** Additional className */
  className?: string;
}

function ShimmerBase({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={clsx('relative overflow-hidden rounded-lg', className)} style={style}>
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent dark:via-cyber-400/5 animate-[shimmer_1.5s_infinite]" />
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}

export default function SkeletonShimmer({
  variant = 'line',
  width,
  height,
  lines = 1,
  className = '',
}: SkeletonShimmerProps) {
  if (variant === 'circle') {
    return (
      <ShimmerBase
        className={clsx(
          'rounded-full bg-robot-border/20 dark:bg-robot-border/20',
          className
        )}
      />
    );
  }

  if (variant === 'card') {
    return (
      <div className={clsx('glass-panel p-5 space-y-3', className)}>
        <ShimmerBase className="h-4 w-3/4 bg-robot-border/20 rounded" />
        <ShimmerBase className="h-3 w-full bg-robot-border/15 rounded" />
        <ShimmerBase className="h-3 w-5/6 bg-robot-border/15 rounded" />
        <ShimmerBase className="h-8 w-1/3 bg-robot-border/20 rounded mt-4" />
      </div>
    );
  }

  if (variant === 'stat-card') {
    return (
      <div className={clsx('glass-panel p-5', className)}>
        <div className="flex items-start gap-4">
          <ShimmerBase className="h-11 w-11 rounded-lg bg-robot-border/20" />
          <div className="flex-1 space-y-2">
            <ShimmerBase className="h-3 w-16 bg-robot-border/15 rounded" />
            <ShimmerBase className="h-6 w-12 bg-robot-border/20 rounded" />
          </div>
        </div>
      </div>
    );
  }

  // Line variant
  return (
    <div className={clsx('space-y-2', className)} style={{ width }}>
      {Array.from({ length: lines }).map((_, i) => (
        <ShimmerBase
          key={i}
          className="bg-robot-border/20 rounded"
          style={{
            height: height || '12px',
            width: i === lines - 1 && lines > 1 ? '70%' : '100%',
          }}
        />
      ))}
    </div>
  );
}

// Additional preset layouts
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="flex items-end justify-between">
        <div className="space-y-2">
          <ShimmerBase className="h-8 w-48 bg-robot-border/20 rounded" />
          <ShimmerBase className="h-3 w-64 bg-robot-border/15 rounded" />
        </div>
        <ShimmerBase className="h-8 w-40 bg-robot-border/20 rounded" />
      </div>

      {/* Stat cards skeleton */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonShimmer key={i} variant="stat-card" />
        ))}
      </div>

      {/* Quick actions skeleton */}
      <div className="glass-panel p-6">
        <ShimmerBase className="h-4 w-32 bg-robot-border/20 rounded mb-4" />
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-robot-border/20 p-5 flex flex-col items-center gap-3">
              <ShimmerBase className="h-12 w-12 rounded-xl bg-robot-border/20" />
              <ShimmerBase className="h-3 w-20 bg-robot-border/15 rounded" />
            </div>
          ))}
        </div>
      </div>

      {/* Activity panels skeleton */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="glass-panel">
            <div className="border-b border-robot-border/20 px-5 py-3">
              <ShimmerBase className="h-3 w-32 bg-robot-border/15 rounded" />
            </div>
            <div className="p-4 space-y-3">
              {Array.from({ length: 3 }).map((_, j) => (
                <div key={j} className="flex items-center gap-3">
                  <ShimmerBase className="h-7 w-7 rounded-md bg-robot-border/20" />
                  <ShimmerBase className="h-3 flex-1 bg-robot-border/15 rounded" />
                  <ShimmerBase className="h-3 w-16 bg-robot-border/10 rounded" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
