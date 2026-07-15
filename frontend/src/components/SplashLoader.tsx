/**
 * SplashLoader Component
 *
 * Full-screen animated splash screen with:
 * - 3D AI Core logo animation (using the RobotScene)
 * - Animated progress bar
 * - Typing text status messages
 * - Fades out after loading completes
 */

import { useState, useEffect, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import RobotScene from './3d/RobotScene';

const LOADING_MESSAGES = [
  'Initializing neural core...',
  'Loading AI modules...',
  'Connecting to intelligence network...',
  'Calibrating data streams...',
  'System ready.',
];

interface SplashLoaderProps {
  /** Minimum time to show splash (ms) */
  minDuration?: number;
  /** Callback when splash is done */
  onComplete: () => void;
}

export default function SplashLoader({ minDuration = 3500, onComplete }: SplashLoaderProps) {
  const [progress, setProgress] = useState(0);
  const [messageIdx, setMessageIdx] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const startTime = Date.now();
    const stepDuration = minDuration / LOADING_MESSAGES.length;

    // Progress animation
    const progressInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min((elapsed / minDuration) * 100, 100);
      setProgress(newProgress);

      // Update message
      const newIdx = Math.min(
        Math.floor(elapsed / stepDuration),
        LOADING_MESSAGES.length - 1
      );
      setMessageIdx(newIdx);

      if (newProgress >= 100) {
        clearInterval(progressInterval);
        setTimeout(() => {
          setIsExiting(true);
          setTimeout(onComplete, 600); // Wait for exit animation
        }, 400);
      }
    }, 30);

    return () => clearInterval(progressInterval);
  }, [minDuration, onComplete]);

  return (
    <AnimatePresence>
      {!isExiting && (
        <motion.div
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-robot-dark overflow-hidden"
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.6, ease: 'easeInOut' }}
        >
          {/* Background effects */}
          <div className="absolute inset-0 bg-cyber-grid opacity-20" />
          <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse at center, rgba(0, 240, 255, 0.05) 0%, transparent 60%)' }} />

          {/* Animated circuit lines */}
          <motion.div
            className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-neon-blue/40 to-transparent"
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <motion.div
            className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-neon-purple/40 to-transparent"
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 2, repeat: Infinity, delay: 1 }}
          />

          {/* 3D Logo */}
          <motion.div
            className="w-56 h-56 mb-8"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          >
            <Suspense fallback={
              <div className="flex h-full w-full items-center justify-center">
                <div className="h-16 w-16 rounded-full border-2 border-neon-blue/30 border-t-neon-blue animate-spin" />
              </div>
            }>
              <RobotScene />
            </Suspense>
          </motion.div>

          {/* Brand name */}
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            <h1 className="font-display text-4xl font-bold tracking-tight text-gradient-cyber">
              AI COPILOT
            </h1>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.4em] text-cyber-400/60">
              Enterprise Intelligence System
            </p>
          </motion.div>

          {/* Progress bar */}
          <motion.div
            className="w-72 mb-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <div className="h-[3px] w-full rounded-full bg-robot-border/30 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-neon-blue via-neon-purple to-neon-blue"
                style={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
              />
            </div>
            {/* Progress percentage */}
            <div className="flex justify-between mt-1.5">
              <span className="font-mono text-[9px] text-gray-600">{Math.round(progress)}%</span>
              <span className="font-mono text-[9px] text-gray-600">
                {progress >= 100 ? 'COMPLETE' : 'LOADING'}
              </span>
            </div>
          </motion.div>

          {/* Status message */}
          <motion.div
            className="h-5 flex items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <AnimatePresence mode="wait">
              <motion.p
                key={messageIdx}
                className="font-mono text-[11px] text-cyber-400/70"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                transition={{ duration: 0.2 }}
              >
                {LOADING_MESSAGES[messageIdx]}
              </motion.p>
            </AnimatePresence>
          </motion.div>

          {/* Version tag */}
          <motion.p
            className="absolute bottom-6 font-mono text-[9px] text-gray-700 tracking-wider"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
          >
            v2.0.1 // NEURAL CORE // {new Date().getFullYear()}
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
