/**
 * LandingPage — Public Main Page with Scroll Animations
 *
 * Showcases the app's features with parallax hero, staggered reveals,
 * count-up stats, and scroll-triggered animations throughout.
 */

import { Suspense, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  MessageSquare,
  Database,
  Brain,
  BookOpen,
  Sparkles,
  FileText,
  Shield,
  Zap,
  ArrowRight,
  Lock,
  Users,
  BarChart3,
  Globe,
} from 'lucide-react';
import RobotScene from '../components/3d/RobotScene';
import ParticleBackground from '../components/ParticleBackground';
import CyberGrid from '../components/CyberGrid';
import AnimatedCircuitSVG from '../components/AnimatedCircuitSVG';
import TextScramble from '../components/TextScramble';
import ScrollReveal from '../components/animations/ScrollReveal';
import StaggeredList from '../components/animations/StaggeredList';
import ParallaxLayer from '../components/animations/ParallaxLayer';
import CountUpOnScroll from '../components/animations/CountUpOnScroll';

const features = [
  { icon: MessageSquare, title: 'AI Chat', description: 'Conversational AI that routes queries through specialized agents for precise answers.', color: 'cyan' },
  { icon: Database, title: 'Data Analysis', description: 'Upload datasets and ask questions in plain English. AI generates SQL and visualizations.', color: 'blue' },
  { icon: Brain, title: 'ML Models', description: 'Train, deploy, and run predictions with classification, regression, and clustering models.', color: 'purple' },
  { icon: BookOpen, title: 'Document Q&A', description: 'Upload documents and get AI answers grounded in your content with source citations.', color: 'green' },
  { icon: Sparkles, title: 'Natural Language SQL', description: 'Ask business questions and get instant SQL-powered answers from your data.', color: 'orange' },
  { icon: FileText, title: 'AI Reports', description: 'Generate executive summaries, forecasts, and recommendation reports automatically.', color: 'teal' },
];

const colorMap: Record<string, { icon: string; border: string; bg: string }> = {
  cyan: { icon: 'text-neon-blue', border: 'border-cyber-400/30 hover:border-cyber-400/60', bg: 'bg-cyber-400/10' },
  blue: { icon: 'text-blue-400', border: 'border-blue-400/30 hover:border-blue-400/60', bg: 'bg-blue-400/10' },
  purple: { icon: 'text-purple-400', border: 'border-purple-400/30 hover:border-purple-400/60', bg: 'bg-purple-400/10' },
  green: { icon: 'text-neon-green', border: 'border-emerald-400/30 hover:border-emerald-400/60', bg: 'bg-emerald-400/10' },
  orange: { icon: 'text-orange-400', border: 'border-orange-400/30 hover:border-orange-400/60', bg: 'bg-orange-400/10' },
  teal: { icon: 'text-teal-400', border: 'border-teal-400/30 hover:border-teal-400/60', bg: 'bg-teal-400/10' },
};

export default function LandingPage() {
  const navigate = useNavigate();
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);

  function handleInteraction() {
    setShowLoginPrompt(true);
    setTimeout(() => navigate('/login'), 1500);
  }

  return (
    <div className="relative min-h-screen bg-[#0a0e1a] overflow-x-hidden text-gray-100">
      {/* Background layers */}
      <CyberGrid showOrbs showGrid orbCount={3} />
      <ParticleBackground intensity="low" />
      <div className="noise-overlay" />

      {/* Circuit decorations with parallax */}
      <ParallaxLayer speed={0.2} className="fixed top-0 left-0 w-48 h-48 z-0">
        <AnimatedCircuitSVG className="w-full h-full opacity-20" duration={4} />
      </ParallaxLayer>
      <ParallaxLayer speed={-0.15} className="fixed bottom-0 right-0 w-48 h-48 z-0">
        <AnimatedCircuitSVG className="w-full h-full opacity-20 rotate-180" duration={4} />
      </ParallaxLayer>

      {/* Login prompt overlay */}
      {showLoginPrompt && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <motion.div
            className="glass-panel-strong p-8 text-center max-w-sm"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-cyber-400/10 border border-cyber-400/30">
              <Lock className="h-7 w-7 text-neon-blue" />
            </div>
            <h3 className="text-lg font-bold text-white">Authentication Required</h3>
            <p className="mt-2 font-mono text-xs text-gray-400">Sign in to access all features</p>
            <p className="mt-3 font-mono text-[10px] text-cyber-400/60 animate-pulse">Redirecting to login...</p>
          </motion.div>
        </motion.div>
      )}

      {/* ═══════════ HERO SECTION ═══════════ */}
      <section className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-10">
        {/* 3D Logo with parallax */}
        <ParallaxLayer speed={-0.2}>
          <motion.div
            className="w-64 h-64 mb-6"
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          >
            <Suspense fallback={
              <div className="flex h-full w-full items-center justify-center">
                <div className="h-12 w-12 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" />
              </div>
            }>
              <RobotScene />
            </Suspense>
          </motion.div>
        </ParallaxLayer>

        {/* Title */}
        <motion.div
          className="text-center mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
        >
          <h1 className="font-display text-5xl md:text-6xl font-bold tracking-tight">
            <TextScramble text="AI COPILOT" speed={50} delay={800} glow className="text-gradient-cyber" />
          </h1>
          <p className="mt-4 font-mono text-sm text-gray-400 max-w-lg mx-auto">
            Enterprise-grade AI analytics platform. Chat with your data,
            train ML models, query documents, and generate reports — all powered by
            intelligent agent orchestration.
          </p>
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          className="flex gap-4 mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
        >
          <button onClick={() => navigate('/login')} className="btn-cyber-filled px-8 py-3 text-sm">
            <Shield className="h-4 w-4 mr-2 inline" /> Sign In
          </button>
          <button onClick={() => navigate('/register')} className="btn-cyber px-8 py-3 text-sm">
            Get Started <ArrowRight className="h-4 w-4 ml-2 inline" />
          </button>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="flex flex-col items-center gap-2">
            <span className="font-mono text-[9px] text-gray-600 uppercase tracking-widest">Explore Features</span>
            <div className="w-[1px] h-6 bg-gradient-to-b from-cyber-400/40 to-transparent" />
          </div>
        </motion.div>
      </section>

      {/* ═══════════ STATS SECTION ═══════════ */}
      <section className="relative z-10 py-16 border-y border-robot-border/20">
        <div className="max-w-4xl mx-auto px-4">
          <ScrollReveal preset="fade-up">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                <CountUpOnScroll target={6} className="font-display text-4xl font-bold text-neon-blue" />
                <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">AI Agents</p>
              </div>
              <div>
                <CountUpOnScroll target={100} suffix="+" className="font-display text-4xl font-bold text-neon-purple" />
                <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">File Types</p>
              </div>
              <div>
                <CountUpOnScroll target={50} suffix="ms" className="font-display text-4xl font-bold text-neon-green" />
                <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">Avg Response</p>
              </div>
              <div>
                <CountUpOnScroll target={99.9} suffix="%" decimals={1} className="font-display text-4xl font-bold text-orange-400" />
                <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">Uptime</p>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* ═══════════ FEATURES SECTION ═══════════ */}
      <section className="relative z-10 px-4 py-24 max-w-6xl mx-auto">
        <ScrollReveal preset="fade-up" className="text-center mb-14">
          <h2 className="font-display text-3xl font-bold text-white">Intelligent Modules</h2>
          <p className="mt-3 font-mono text-xs text-gray-500 uppercase tracking-wider">
            Six specialized AI agents working together
          </p>
        </ScrollReveal>

        <StaggeredList
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
          staggerDelay={0.1}
          direction="up"
          distance={40}
        >
          {features.map((feature) => {
            const colors = colorMap[feature.color] ?? colorMap.cyan!;
            if (!colors) return null;
            return (
              <motion.div
                key={feature.title}
                onClick={handleInteraction}
                className={`group cursor-pointer rounded-xl border bg-robot-panel/50 backdrop-blur-sm p-6 transition-all duration-300 hover:bg-robot-panel/80 ${colors.border}`}
                whileHover={{ scale: 1.03, y: -5 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${colors.bg} mb-4 transition-transform group-hover:scale-110`}>
                  <feature.icon className={`h-5 w-5 ${colors.icon}`} />
                </div>
                <h3 className="text-sm font-bold text-white mb-2">{feature.title}</h3>
                <p className="text-xs text-gray-400 leading-relaxed">{feature.description}</p>
                <div className="mt-4 flex items-center gap-1 font-mono text-[9px] text-gray-600 uppercase tracking-wider group-hover:text-cyber-400 transition-colors">
                  <Lock className="h-3 w-3" /> Sign in to access
                </div>
              </motion.div>
            );
          })}
        </StaggeredList>
      </section>

      {/* ═══════════ DEMO PREVIEW SECTION ═══════════ */}
      <section className="relative z-10 px-4 py-24 max-w-5xl mx-auto">
        <ScrollReveal preset="fade-up" className="text-center mb-10">
          <h2 className="font-display text-3xl font-bold text-white">Command Center Preview</h2>
          <p className="mt-3 font-mono text-xs text-gray-500 uppercase tracking-wider">Your AI-powered analytics dashboard</p>
        </ScrollReveal>

        <ScrollReveal preset="scale" delay={0.2}>
          <motion.div
            className="rounded-xl border border-robot-border/40 bg-robot-panel/30 backdrop-blur-sm overflow-hidden cursor-pointer"
            onClick={handleInteraction}
            whileHover={{ scale: 1.01 }}
          >
            {/* Mock header */}
            <div className="flex items-center gap-2 border-b border-robot-border/30 px-4 py-2.5 bg-robot-darker/50">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-neon-green/60" />
              </div>
              <span className="font-mono text-[9px] text-gray-500 ml-3">ai-copilot://dashboard</span>
            </div>

            {/* Mock content */}
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-5 gap-3">
                {['Datasets', 'Models', 'Documents', 'Chats', 'Reports'].map((label, i) => (
                  <div key={label} className="rounded-lg border border-robot-border/20 bg-robot-darker/50 p-3 text-center">
                    <p className="font-mono text-[8px] text-gray-600 uppercase">{label}</p>
                    <p className="font-mono text-lg font-bold text-white mt-1">{[12, 5, 28, 47, 9][i]}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-robot-border/20 bg-robot-darker/50 p-3">
                  <p className="font-mono text-[8px] text-gray-600 uppercase mb-2">Recent Activity</p>
                  {[1, 2, 3].map(i => (
                    <div key={i} className="flex items-center gap-2 py-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-neon-blue/40" />
                      <div className="h-2 rounded bg-robot-border/30 flex-1" style={{ width: `${60 + i * 10}%` }} />
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-robot-border/20 bg-robot-darker/50 p-3">
                  <p className="font-mono text-[8px] text-gray-600 uppercase mb-2">AI Chat</p>
                  <div className="space-y-2">
                    <div className="flex justify-end"><div className="h-3 w-24 rounded-full bg-cyber-400/20" /></div>
                    <div className="flex justify-start"><div className="h-3 w-32 rounded-full bg-robot-border/30" /></div>
                    <div className="flex justify-end"><div className="h-3 w-20 rounded-full bg-cyber-400/20" /></div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-center py-3">
                <div className="flex items-center gap-2 rounded-md border border-cyber-400/20 bg-cyber-400/5 px-4 py-2">
                  <Lock className="h-3.5 w-3.5 text-neon-blue" />
                  <span className="font-mono text-[10px] text-cyber-400">Click to sign in and access your dashboard</span>
                </div>
              </div>
            </div>
          </motion.div>
        </ScrollReveal>
      </section>

      {/* ═══════════ HOW IT WORKS ═══════════ */}
      <section className="relative z-10 px-4 py-24 max-w-4xl mx-auto">
        <ScrollReveal preset="fade-up" className="text-center mb-12">
          <h2 className="font-display text-3xl font-bold text-white">How It Works</h2>
          <p className="mt-3 font-mono text-xs text-gray-500 uppercase tracking-wider">Intelligent agent orchestration pipeline</p>
        </ScrollReveal>

        <StaggeredList
          className="grid grid-cols-1 md:grid-cols-4 gap-6"
          staggerDelay={0.15}
          direction="up"
        >
          {[
            { step: '01', title: 'Ask', desc: 'Type your question in natural language', icon: MessageSquare },
            { step: '02', title: 'Plan', desc: 'AI Planner analyzes and creates strategy', icon: Brain },
            { step: '03', title: 'Execute', desc: 'Specialized agents process your request', icon: Zap },
            { step: '04', title: 'Deliver', desc: 'Synthesized answer with sources', icon: BarChart3 },
          ].map((item) => (
            <div key={item.step} className="text-center p-4">
              <ParallaxLayer speed={0.1}>
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-cyber-400/30 bg-cyber-400/5">
                  <item.icon className="h-5 w-5 text-neon-blue" />
                </div>
              </ParallaxLayer>
              <span className="font-mono text-[9px] text-cyber-400/50">{item.step}</span>
              <h4 className="text-sm font-bold text-white mb-1">{item.title}</h4>
              <p className="font-mono text-[10px] text-gray-500">{item.desc}</p>
            </div>
          ))}
        </StaggeredList>
      </section>

      {/* ═══════════ TRUST SECTION ═══════════ */}
      <section className="relative z-10 px-4 py-20 border-t border-robot-border/20">
        <div className="max-w-4xl mx-auto">
          <ScrollReveal preset="fade-up" className="text-center mb-10">
            <h2 className="font-display text-2xl font-bold text-white">Enterprise Ready</h2>
          </ScrollReveal>

          <StaggeredList className="grid grid-cols-1 md:grid-cols-3 gap-6" staggerDelay={0.12}>
            <div className="text-center p-6 rounded-xl border border-robot-border/20 bg-robot-panel/20">
              <Shield className="mx-auto h-8 w-8 text-neon-blue/60 mb-3" />
              <h4 className="text-sm font-bold text-white mb-1">Secure by Default</h4>
              <p className="font-mono text-[10px] text-gray-500">JWT auth, encrypted data, role-based access</p>
            </div>
            <div className="text-center p-6 rounded-xl border border-robot-border/20 bg-robot-panel/20">
              <Users className="mx-auto h-8 w-8 text-neon-purple/60 mb-3" />
              <h4 className="text-sm font-bold text-white mb-1">Multi-User</h4>
              <p className="font-mono text-[10px] text-gray-500">Isolated workspaces per user, team collaboration</p>
            </div>
            <div className="text-center p-6 rounded-xl border border-robot-border/20 bg-robot-panel/20">
              <Globe className="mx-auto h-8 w-8 text-neon-green/60 mb-3" />
              <h4 className="text-sm font-bold text-white mb-1">API First</h4>
              <p className="font-mono text-[10px] text-gray-500">RESTful API, WebSocket support, extensible</p>
            </div>
          </StaggeredList>
        </div>
      </section>

      {/* ═══════════ FOOTER CTA ═══════════ */}
      <section className="relative z-10 px-4 py-20 text-center">
        <ScrollReveal preset="scale">
          <Zap className="mx-auto h-8 w-8 text-neon-blue/50 mb-4" />
          <h2 className="font-display text-2xl font-bold text-white mb-3">Ready to get started?</h2>
          <p className="font-mono text-xs text-gray-500 mb-6 max-w-md mx-auto">
            Create your account and start analyzing data with AI in minutes.
          </p>
          <div className="flex justify-center gap-4">
            <button onClick={() => navigate('/register')} className="btn-cyber-filled px-8 py-3 text-sm">Create Account</button>
            <button onClick={() => navigate('/login')} className="btn-cyber px-8 py-3 text-sm">Sign In</button>
          </div>
        </ScrollReveal>

        <div className="mt-16 pt-6 border-t border-robot-border/20">
          <p className="font-mono text-[9px] text-gray-700 tracking-wider">
            AI COPILOT // ENTERPRISE INTELLIGENCE SYSTEM // {new Date().getFullYear()}
          </p>
        </div>
      </section>
    </div>
  );
}
