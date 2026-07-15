/**
 * Register Page - Advanced 3D Robotic AI Aesthetic
 *
 * Matching 3D login aesthetic with RobotScene, circuit SVG, matrix rain.
 */

import { useState, FormEvent, Suspense } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { Shield, Cpu } from 'lucide-react';
import ParticleBackground from '../components/ParticleBackground';
import CyberGrid from '../components/CyberGrid';
import RobotScene from '../components/3d/RobotScene';
import AnimatedCircuitSVG from '../components/AnimatedCircuitSVG';
import MatrixRain from '../components/MatrixRain';
import TextScramble from '../components/TextScramble';
import MagneticButton from '../components/MagneticButton';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await register(email, fullName, password);
      navigate('/');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || 'Registration failed');
      } else {
        setError('Registration failed');
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
      <MatrixRain className="fixed inset-0 w-full h-full" opacity={0.04} speed={0.6} />
      <AnimatedCircuitSVG className="fixed top-0 right-0 w-64 h-64 opacity-30" duration={3} />
      <AnimatedCircuitSVG className="fixed bottom-0 left-0 w-64 h-64 opacity-30 rotate-180" duration={3} />
      <div className="scanline-overlay" />
      <div className="noise-overlay" />

      {/* Content */}
      <motion.div
        className="relative z-10 w-full max-w-md px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* 3D Robot Scene */}
        <motion.div
          className="mx-auto mb-4 h-40 w-40"
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

        {/* Title */}
        <motion.div
          className="mb-6 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          <h1 className="font-display text-3xl font-bold tracking-tight">
            <TextScramble text="NEW OPERATOR" speed={40} delay={500} glow className="text-gradient-cyber" />
          </h1>
          <p className="mt-2 font-mono text-xs uppercase tracking-[0.3em] text-cyber-400/70">
            <TextScramble text="Access Registration Protocol" speed={20} delay={1200} />
          </p>
        </motion.div>

        {/* Form */}
        <motion.div
          className="glass-panel-strong p-8"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.6 }}
        >
          {/* HUD corners */}
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
            <span className="hud-label">New Account Registration</span>
          </div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 font-mono text-xs text-red-400"
              role="alert"
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse mr-2" />
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="fullName" className="hud-label mb-1.5 block">Operator Name</label>
              <input id="fullName" type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="input-cyber" placeholder="Full Name" autoComplete="name" />
            </div>
            <div>
              <label htmlFor="email" className="hud-label mb-1.5 block">User Identifier</label>
              <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-cyber" placeholder="operator@enterprise.com" autoComplete="email" />
            </div>
            <div>
              <label htmlFor="password" className="hud-label mb-1.5 block">Access Key</label>
              <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="input-cyber" placeholder="Minimum 8 characters" autoComplete="new-password" />
            </div>

            <MagneticButton type="submit" disabled={isSubmitting} strength={8} className="btn-cyber-filled w-full disabled:opacity-50 disabled:cursor-not-allowed">
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Initializing...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Shield className="h-4 w-4" />
                  Create Account
                </span>
              )}
            </MagneticButton>
          </form>

          <div className="mt-6 border-t border-robot-border/30 pt-4 text-center">
            <p className="font-mono text-xs text-gray-500">
              Already registered?{' '}
              <Link to="/login" className="text-cyber-400 hover:text-neon-blue transition-colors">Access Login</Link>
            </p>
          </div>
        </motion.div>

        <motion.div className="mt-6 text-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}>
          <p className="font-mono text-[10px] text-gray-600 tracking-wider">v2.0.1 // NEURAL CORE ACTIVE // {new Date().getFullYear()}</p>
        </motion.div>
      </motion.div>
    </div>
  );
}
