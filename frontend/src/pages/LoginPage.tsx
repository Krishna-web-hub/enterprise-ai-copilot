/**
 * Login Page - Advanced 3D Robotic AI Aesthetic
 *
 * Features a 3D AI Core scene (Three.js), animated circuit SVG,
 * matrix rain background, magnetic button, and text scramble effects.
 */

import { useState, FormEvent, Suspense } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { Shield, Cpu, Activity } from 'lucide-react';
import ParticleBackground from '../components/ParticleBackground';
import CyberGrid from '../components/CyberGrid';
import RobotScene from '../components/3d/RobotScene';
import AnimatedCircuitSVG from '../components/AnimatedCircuitSVG';
import MatrixRain from '../components/MatrixRain';
import TextScramble from '../components/TextScramble';
import MagneticButton from '../components/MagneticButton';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showSignupHint, setShowSignupHint] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setShowSignupHint(false);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        const status = axiosErr.response?.status;
        const detail = axiosErr.response?.data?.detail || '';

        if (status === 404 || detail.toLowerCase().includes('no account found')) {
          setError('No account found with this email.');
          setShowSignupHint(true);
        } else if (status === 401) {
          setError('Incorrect password. Please try again.');
        } else {
          setError(detail || 'Login failed. Please try again.');
        }
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0a0e1a] text-gray-100">
      {/* Background layers */}
      <CyberGrid showOrbs showGrid orbCount={4} />
      <ParticleBackground intensity="medium" />

      {/* Matrix rain - very subtle */}
      <MatrixRain className="fixed inset-0 w-full h-full" opacity={0.04} speed={0.6} />

      {/* Animated circuit SVG in corners */}
      <AnimatedCircuitSVG className="fixed top-0 left-0 w-64 h-64 opacity-30" duration={3} />
      <AnimatedCircuitSVG className="fixed bottom-0 right-0 w-64 h-64 opacity-30 rotate-180" duration={3} />

      {/* Scanline + noise */}
      <div className="scanline-overlay" />
      <div className="noise-overlay" />

      {/* Main content */}
      <motion.div
        className="relative z-10 w-full max-w-md px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* 3D Robot Scene as logo */}
        <motion.div
          className="mx-auto mb-4 h-48 w-48"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          <Suspense fallback={
            <div className="flex h-full w-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" />
            </div>
          }>
            <RobotScene />
          </Suspense>
        </motion.div>

        {/* Title with scramble effect */}
        <motion.div
          className="mb-8 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          <h1 className="font-display text-3xl font-bold tracking-tight">
            <TextScramble text="AI COPILOT" speed={40} delay={500} glow className="text-gradient-cyber" />
          </h1>
          <p className="mt-2 font-mono text-xs uppercase tracking-[0.3em] text-cyber-400/70">
            <TextScramble text="Enterprise Intelligence System" speed={20} delay={1200} />
          </p>

          {/* Status indicators */}
          <div className="mt-4 flex items-center justify-center gap-4">
            <span className="flex items-center gap-1.5 font-mono text-[10px] text-gray-500">
              <span className="status-dot status-dot--online" />
              SYSTEM ONLINE
            </span>
            <span className="flex items-center gap-1.5 font-mono text-[10px] text-gray-500">
              <Shield className="h-3 w-3 text-cyber-400/60" />
              SECURE
            </span>
          </div>
        </motion.div>

        {/* Login Form Panel */}
        <motion.div
          className="glass-panel-strong p-8"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.6 }}
        >
          {/* HUD corner decorations */}
          <div className="absolute top-3 left-3 w-4 h-4">
            <span className="absolute top-0 left-0 w-full h-[1px] bg-neon-blue/60" />
            <span className="absolute top-0 left-0 w-[1px] h-full bg-neon-blue/60" />
          </div>
          <div className="absolute top-3 right-3 w-4 h-4">
            <span className="absolute top-0 right-0 w-full h-[1px] bg-neon-blue/60" />
            <span className="absolute top-0 right-0 w-[1px] h-full bg-neon-blue/60" />
          </div>
          <div className="absolute bottom-3 left-3 w-4 h-4">
            <span className="absolute bottom-0 left-0 w-full h-[1px] bg-neon-blue/60" />
            <span className="absolute bottom-0 left-0 w-[1px] h-full bg-neon-blue/60" />
          </div>
          <div className="absolute bottom-3 right-3 w-4 h-4">
            <span className="absolute bottom-0 right-0 w-full h-[1px] bg-neon-blue/60" />
            <span className="absolute bottom-0 right-0 w-[1px] h-full bg-neon-blue/60" />
          </div>

          {/* Panel header */}
          <div className="mb-6 flex items-center gap-2 border-b border-robot-border/50 pb-4">
            <Cpu className="h-4 w-4 text-cyber-400/70" />
            <span className="hud-label">Authentication Protocol</span>
            <Activity className="ml-auto h-3 w-3 text-neon-green/60 animate-glow-pulse" />
          </div>

          {/* Error message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-400"
              role="alert"
            >
              <p className="flex items-center gap-2">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                {error}
              </p>
              {showSignupHint && (
                <p className="mt-2 text-gray-400">
                  No account?{' '}
                  <Link to="/register" className="text-neon-blue hover:text-white underline transition-colors">
                    Initialize new account
                  </Link>
                </p>
              )}
            </motion.div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="hud-label mb-1.5 block">
                User Identifier
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-cyber"
                placeholder="operator@enterprise.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="hud-label mb-1.5 block">
                Access Key
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-cyber"
                placeholder="Enter secure passphrase"
                autoComplete="current-password"
              />
            </div>

            <MagneticButton
              type="submit"
              disabled={isSubmitting}
              strength={8}
              className="btn-cyber-filled w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Authenticating...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Shield className="h-4 w-4" />
                  Initialize Session
                </span>
              )}
            </MagneticButton>
          </form>

          {/* Footer link */}
          <div className="mt-6 border-t border-robot-border/30 pt-4 text-center">
            <p className="font-mono text-xs text-gray-500">
              New operator?{' '}
              <Link to="/register" className="text-cyber-400 hover:text-neon-blue transition-colors">
                Register Access
              </Link>
            </p>
          </div>
        </motion.div>

        {/* Bottom system info */}
        <motion.div
          className="mt-6 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.6 }}
        >
          <p className="font-mono text-[10px] text-gray-600 tracking-wider">
            v2.0.1 // NEURAL CORE ACTIVE // {new Date().getFullYear()}
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}
