/**
 * Dashboard Page - Advanced 3D Robotic AI Command Center
 *
 * Overview with 3D TiltCards, TextScramble headings,
 * holographic HUD stat cards with animated counters.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  Brain,
  FileText,
  MessageSquare,
  BookOpen,
  Sparkles,
  Upload,
  Activity,
  Terminal,
  ArrowRight,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { DashboardData, getDashboard } from '../services/dashboard';
import HoloStatCard from '../components/HoloStatCard';
import TextScramble from '../components/TextScramble';
import TiltCard from '../components/TiltCard';
import ScrollReveal from '../components/animations/ScrollReveal';
import { DashboardSkeleton } from '../components/ui/SkeletonShimmer';
import { useTheme } from '../context/ThemeContext';
import clsx from 'clsx';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { type: "spring" as const, stiffness: 300, damping: 24 },
  },
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    setIsLoading(true);
    try {
      const result = await getDashboard();
      setData(result);
    } catch {
      // Show zeros on error
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  const stats = [
    { label: 'Datasets', value: data?.total_datasets ?? 0, icon: Database, color: 'blue' as const, to: '/app/datasets', code: 'DAT' },
    { label: 'Models', value: data?.total_models ?? 0, icon: Brain, color: 'purple' as const, to: '/app/models', code: 'MDL' },
    { label: 'Documents', value: data?.total_documents ?? 0, icon: BookOpen, color: 'green' as const, to: '/app/documents', code: 'DOC' },
    { label: 'Chats', value: data?.total_chat_sessions ?? 0, icon: MessageSquare, color: 'orange' as const, to: '/app/chat', code: 'COM' },
    { label: 'Reports', value: data?.total_reports ?? 0, icon: FileText, color: 'cyan' as const, to: '/app/reports', code: 'RPT' },
  ];

  const quickActions = [
    { label: 'Upload Dataset', icon: Upload, to: '/app/datasets', description: 'Import new data source' },
    { label: 'Start Chat', icon: MessageSquare, to: '/app/chat', description: 'Open AI communication' },
    { label: 'Ask Your Data', icon: Sparkles, to: '/app/ask-data', description: 'Natural language query' },
    { label: 'Upload Document', icon: BookOpen, to: '/app/documents', description: 'Add to knowledge base' },
  ];

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header with scramble effect */}
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display">
            <TextScramble text="Command Center" speed={40} delay={300} glow className="text-gradient-cyber text-3xl" />
          </h1>
          <p className="mt-2 font-mono text-xs text-gray-500 uppercase tracking-wider">
            <TextScramble text="System overview // All modules operational" speed={15} delay={1500} />
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 rounded-md bg-robot-panel/50 border border-robot-border/30 px-3 py-1.5">
          <Activity className={clsx('h-3 w-3 animate-glow-pulse', isDark ? 'text-neon-green/60' : 'text-emerald-500')} />
          <span className={clsx('font-mono text-[10px] uppercase', isDark ? 'text-gray-500' : 'text-gray-600')}>All Systems Nominal</span>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((stat) => (
          <HoloStatCard
            key={stat.label}
            label={stat.label}
            value={stat.value}
            icon={stat.icon}
            color={stat.color}
            code={stat.code}
            onClick={() => navigate(stat.to)}
            variants={itemVariants}
          />
        ))}
      </motion.div>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <TiltCard className="glass-panel p-6 relative overflow-hidden rounded-xl" maxTilt={5} glareIntensity={0.15}>
          {/* Background accent */}
          <div className="absolute -right-20 -top-20 w-64 h-64 bg-cyber-400/5 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="flex items-center gap-2 mb-5 relative z-10">
          <Terminal className="h-4 w-4 text-cyber-400/70" />
          <span className="hud-label">Quick Actions</span>
          <div className="ml-4 flex-1 h-[1px] bg-gradient-to-r from-robot-border/50 to-transparent" />
        </div>

        {/* Action cards */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 relative z-10">
          {quickActions.map((action) => (
            <motion.button
              key={action.label}
              onClick={() => navigate(action.to)}
              className={clsx(
                'group relative flex flex-col items-center gap-3 rounded-xl border p-5 text-center transition-all duration-300',
                isDark
                  ? 'border-robot-border/40 bg-robot-darker/50 hover:border-cyber-400/40 hover:bg-cyber-400/5'
                  : 'border-gray-100 bg-white/60 hover:border-cyan-200 hover:bg-white hover:shadow-md'
              )}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className={clsx(
                'flex h-12 w-12 items-center justify-center rounded-xl border transition-all duration-300',
                isDark
                  ? 'bg-robot-panel border-robot-border/30 group-hover:border-cyber-400/30 group-hover:shadow-neon'
                  : 'bg-cyan-50 border-cyan-100 group-hover:bg-cyan-100 group-hover:shadow-sm'
              )}>
                <action.icon className={clsx('h-5 w-5 transition-colors duration-300', isDark ? 'text-gray-400 group-hover:text-neon-blue' : 'text-cyan-600 group-hover:text-cyan-700')} />
              </div>
              <div>
                <p className={clsx('text-sm font-medium transition-colors', isDark ? 'text-gray-300 group-hover:text-white' : 'text-gray-700 group-hover:text-gray-900')}>
                  {action.label}
                </p>
                <p className={clsx('mt-0.5 font-mono text-[9px] uppercase tracking-wider', isDark ? 'text-gray-600' : 'text-gray-400')}>
                  {action.description}
                </p>
              </div>
              <ArrowRight className={clsx('absolute top-3 right-3 h-3 w-3 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-1 group-hover:translate-x-0', isDark ? 'text-cyber-400' : 'text-cyan-500')} />
            </motion.button>
          ))}
        </div>
        </TiltCard>
      </motion.div>

      {/* Recent Activity */}
      <ScrollReveal preset="fade-up" delay={0.2}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Datasets */}
        <motion.div variants={itemVariants} className="glass-panel overflow-hidden">
          {/* Panel header */}
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Database className="h-3.5 w-3.5 text-blue-400/70" />
            <span className="hud-label">Recent Datasets</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">
              {data?.recent_datasets?.length ?? 0} entries
            </span>
          </div>

          {data?.recent_datasets && data.recent_datasets.length > 0 ? (
            <ul className="divide-y divide-robot-border/20">
              {data.recent_datasets.map((ds, index) => (
                <motion.li
                  key={ds.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="group flex items-center gap-3 px-5 py-3 transition-all duration-200 hover:bg-blue-500/5 cursor-pointer"
                >
                  {/* Index number */}
                  <span className="font-mono text-[9px] text-gray-600 w-4">{String(index + 1).padStart(2, '0')}</span>

                  {/* Icon */}
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-500/10 border border-blue-500/20">
                    <Database className="h-3.5 w-3.5 text-blue-400" />
                  </div>

                  {/* Name */}
                  <span className="flex-1 truncate text-sm text-gray-300 group-hover:text-white transition-colors">
                    {ds.name}
                  </span>

                  {/* Date */}
                  <span className="font-mono text-[10px] text-gray-600">{formatDate(ds.created_at)}</span>

                  {/* Hover indicator */}
                  <div className="w-1 h-1 rounded-full bg-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <Database className="h-6 w-6 text-gray-700" />
              <p className="font-mono text-xs text-gray-600">No datasets uploaded yet</p>
              <button
                onClick={() => navigate('/datasets')}
                className="mt-2 font-mono text-[10px] text-cyber-400 hover:text-neon-blue uppercase tracking-wider transition-colors"
              >
                [Upload First Dataset]
              </button>
            </div>
          )}
        </motion.div>

        {/* Recent Chats */}
        <motion.div variants={itemVariants} className="glass-panel overflow-hidden">
          {/* Panel header */}
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <MessageSquare className="h-3.5 w-3.5 text-orange-400/70" />
            <span className="hud-label">Recent Communications</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">
              {data?.recent_chats?.length ?? 0} sessions
            </span>
          </div>

          {data?.recent_chats && data.recent_chats.length > 0 ? (
            <ul className="divide-y divide-robot-border/20">
              {data.recent_chats.map((chat, index) => (
                <motion.li
                  key={chat.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="group flex items-center gap-3 px-5 py-3 transition-all duration-200 hover:bg-orange-500/5 cursor-pointer"
                >
                  {/* Index number */}
                  <span className="font-mono text-[9px] text-gray-600 w-4">{String(index + 1).padStart(2, '0')}</span>

                  {/* Icon */}
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-orange-500/10 border border-orange-500/20">
                    <MessageSquare className="h-3.5 w-3.5 text-orange-400" />
                  </div>

                  {/* Title */}
                  <span className="flex-1 truncate text-sm text-gray-300 group-hover:text-white transition-colors">
                    {chat.title}
                  </span>

                  {/* Date */}
                  <span className="font-mono text-[10px] text-gray-600">{formatDate(chat.created_at)}</span>

                  {/* Hover indicator */}
                  <div className="w-1 h-1 rounded-full bg-orange-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <MessageSquare className="h-6 w-6 text-gray-700" />
              <p className="font-mono text-xs text-gray-600">No conversations yet</p>
              <button
                onClick={() => navigate('/chat')}
                className="mt-2 font-mono text-[10px] text-cyber-400 hover:text-neon-blue uppercase tracking-wider transition-colors"
              >
                [Start First Chat]
              </button>
            </div>
          )}
        </motion.div>
        </div>
      </ScrollReveal>

      {/* Footer status line */}
      <motion.div variants={itemVariants} className="flex items-center justify-center gap-4 pt-2">
        <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-robot-border/30 to-transparent" />
        <span className="font-mono text-[9px] text-gray-700 uppercase tracking-widest">
          Neural Core v2.0 // {new Date().toISOString().slice(0, 10)}
        </span>
        <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-robot-border/30 to-transparent" />
      </motion.div>
    </motion.div>
  );
}
