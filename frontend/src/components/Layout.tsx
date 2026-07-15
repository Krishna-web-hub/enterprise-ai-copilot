/**
 * Layout Component - Dual Mode with Collapsible Sidebar
 *
 * Provides the app shell with:
 * - Responsive collapsible sidebar (icon-only on collapse)
 * - Theme-aware dark/light modes
 * - Animated page transitions
 * - Custom cursor glow (dark mode)
 */

import { Suspense, useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import InteractiveBackground from './3d/InteractiveBackground';
import CursorGlow from './CursorGlow';
import WelcomeBot from './WelcomeBot';
import {
  LayoutDashboard,
  MessageSquare,
  Database,
  Sparkles,
  BookOpen,
  Brain,
  FileText,
  LogOut,
  Bot,
  Wifi,
  Cpu,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import HudHeader from './HudHeader';

const navItems = [
  { to: '/app', icon: LayoutDashboard, label: 'Dashboard', code: 'DSH', tour: 'dashboard' },
  { to: '/app/chat', icon: MessageSquare, label: 'Chat', code: 'COM', tour: 'chat' },
  { to: '/app/datasets', icon: Database, label: 'Datasets', code: 'DAT', tour: 'datasets' },
  { to: '/app/ask-data', icon: Sparkles, label: 'Ask Data', code: 'QRY', tour: 'ask-data' },
  { to: '/app/documents', icon: BookOpen, label: 'Documents', code: 'DOC', tour: 'documents' },
  { to: '/app/models', icon: Brain, label: 'Models', code: 'MDL', tour: 'models' },
  { to: '/app/reports', icon: FileText, label: 'Reports', code: 'RPT', tour: 'reports' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { resolvedTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isDark = resolvedTheme === 'dark';
  const [collapsed, setCollapsed] = useState(false);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className={clsx('flex h-screen overflow-hidden', isDark ? 'bg-robot-dark' : 'bg-gradient-to-br from-sky-50/50 via-white to-cyan-50/30')}>
      {/* Custom cursor */}
      <CursorGlow />

      {/* Welcome bot tour (shows once for new users) */}
      <WelcomeBot />

      {/* Sidebar */}
      <motion.aside
        className={clsx(
          'relative z-10 flex flex-col border-r transition-colors',
          isDark ? 'border-robot-border/50 bg-robot-darker' : 'border-gray-100 bg-white/80 backdrop-blur-xl shadow-sm'
        )}
        animate={{ width: collapsed ? 72 : 256 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Circuit line (dark only) */}
        {isDark && !collapsed && (
          <div className="absolute top-0 right-0 bottom-0 w-[1px]">
            <div className="h-full w-full bg-gradient-to-b from-transparent via-cyber-400/20 to-transparent" />
            <motion.div
              className="absolute left-[-2px] w-[5px] h-[5px] rounded-full bg-neon-blue shadow-neon"
              animate={{ top: ['0%', '100%'] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
            />
          </div>
        )}

        {/* Logo section */}
        <div className={clsx(
          'relative flex h-16 items-center gap-3 px-4 border-b',
          isDark ? 'border-robot-border/30' : 'border-gray-100'
        )}>
          <div className={clsx(
            'relative flex h-9 w-9 items-center justify-center rounded-lg border flex-shrink-0',
            isDark ? 'bg-robot-panel border-cyber-400/30 shadow-neon' : 'bg-cyber-50 border-cyber-200 shadow-sm'
          )}>
            <Bot className={clsx('h-5 w-5', isDark ? 'text-neon-blue' : 'text-cyber-600')} />
            {isDark && <span className="absolute inset-0 rounded-lg border border-cyber-400/20 animate-pulse-ring" />}
          </div>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="overflow-hidden"
            >
              <span className={clsx('text-sm font-bold tracking-wide', isDark ? 'text-white' : 'text-gray-900')}>AI COPILOT</span>
              <p className={clsx('font-mono text-[9px] tracking-widest', isDark ? 'text-cyber-400/60' : 'text-cyber-600/60')}>ENTERPRISE v2.0</p>
            </motion.div>
          )}
        </div>

        {/* Status bar (expanded only) */}
        {!collapsed && (
          <div className={clsx(
            'flex items-center gap-3 px-5 py-2 border-b',
            isDark ? 'border-robot-border/20' : 'border-gray-100'
          )}>
            <span className="flex items-center gap-1.5">
              <span className="status-dot status-dot--online" />
              <span className="font-mono text-[9px] text-gray-500 uppercase">Online</span>
            </span>
            <span className="flex items-center gap-1">
              <Wifi className={clsx('h-3 w-3', isDark ? 'text-neon-green/50' : 'text-emerald-500/60')} />
              <span className="font-mono text-[9px] text-gray-500">Connected</span>
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="mt-3 flex-1 space-y-0.5 px-2 overflow-y-auto">
          {!collapsed && (
            <div className="px-3 py-2">
              <span className="hud-label">Navigation</span>
            </div>
          )}

          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/app'}
              title={collapsed ? item.label : undefined}
              data-tour={item.tour}
              className={({ isActive }) =>
                clsx(
                  'group relative flex items-center rounded-lg text-sm font-medium transition-all duration-300',
                  collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
                  isActive
                    ? isDark
                      ? 'text-white bg-cyber-400/10 border border-cyber-400/30'
                      : 'text-cyber-700 bg-cyber-50 border border-cyber-200'
                    : isDark
                      ? 'text-gray-400 border border-transparent hover:text-white hover:bg-white/5 hover:border-robot-border/50'
                      : 'text-gray-600 border border-transparent hover:text-gray-900 hover:bg-gray-50 hover:border-gray-200'
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active-glow"
                      className={clsx(
                        'absolute -left-2 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full',
                        isDark ? 'bg-neon-blue shadow-neon' : 'bg-cyber-500 shadow-neon-light'
                      )}
                      initial={false}
                      transition={{ type: "spring" as const, stiffness: 400, damping: 30 }}
                    />
                  )}

                  <div className={clsx(
                    'flex h-7 w-7 items-center justify-center rounded-md transition-all duration-300 flex-shrink-0',
                    isActive
                      ? isDark ? 'bg-cyber-400/20' : 'bg-cyber-100'
                      : 'bg-transparent'
                  )}>
                    <item.icon className={clsx(
                      'h-4 w-4 transition-colors duration-300',
                      isActive
                        ? isDark ? 'text-neon-blue' : 'text-cyber-600'
                        : isDark ? 'text-gray-500 group-hover:text-gray-300' : 'text-gray-400 group-hover:text-gray-700'
                    )} />
                  </div>

                  {!collapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      <span className={clsx(
                        'font-mono text-[9px] tracking-wider',
                        isActive
                          ? isDark ? 'text-cyber-400/70' : 'text-cyber-600/70'
                          : isDark ? 'text-gray-600' : 'text-gray-400'
                      )}>
                        {item.code}
                      </span>
                    </>
                  )}

                  {isActive && isDark && !collapsed && (
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-neon-blue animate-glow-pulse" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Collapse toggle button */}
        <div className={clsx('px-3 py-2 border-t', isDark ? 'border-robot-border/20' : 'border-gray-100')}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={clsx(
              'flex items-center gap-2 w-full rounded-lg px-3 py-2 text-xs font-mono transition-all',
              isDark
                ? 'text-gray-500 hover:text-white hover:bg-white/5'
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50',
              collapsed && 'justify-center'
            )}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" />
                <span className="uppercase tracking-wider">Collapse</span>
              </>
            )}
          </button>
        </div>

        {/* User section */}
        <div className="p-3">
          {collapsed ? (
            <button
              onClick={handleLogout}
              className="flex w-full items-center justify-center rounded-lg p-2 text-gray-500 hover:bg-red-500/10 hover:text-red-400 transition-all"
              title="End Session"
            >
              <LogOut className="h-4 w-4" />
            </button>
          ) : (
            <div className="glass-panel p-3">
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'relative flex h-9 w-9 items-center justify-center rounded-full border flex-shrink-0',
                  isDark ? 'bg-robot-panel border-robot-border' : 'bg-gray-50 border-gray-200'
                )}>
                  <Cpu className={clsx('h-4 w-4', isDark ? 'text-cyber-400/70' : 'text-cyber-600/70')} />
                  <span className={clsx(
                    'absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-neon-green border-2',
                    isDark ? 'border-robot-darker' : 'border-white'
                  )} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={clsx('truncate text-xs font-medium', isDark ? 'text-white' : 'text-gray-900')}>{user?.full_name}</p>
                  <p className={clsx('font-mono text-[9px] uppercase tracking-wider', isDark ? 'text-cyber-400/50' : 'text-cyber-600/50')}>{user?.role || 'Operator'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="rounded-lg p-2 text-gray-500 hover:bg-red-500/10 hover:text-red-400 transition-all border border-transparent hover:border-red-500/30"
                  title="End Session"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </motion.aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden relative z-10">
        <HudHeader />

        {/* Page content */}
        <main className={clsx(
          'flex-1 overflow-y-auto p-6 relative',
          isDark ? 'bg-robot-dark' : 'bg-transparent'
        )}>
          {/* Interactive 3D background (both modes) */}
          <Suspense fallback={null}>
            <InteractiveBackground />
          </Suspense>

          <div className="pointer-events-none absolute inset-0 bg-cyber-grid opacity-40" />

          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              className="relative z-10"
              initial={{ opacity: 0, y: 12, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -8, filter: 'blur(2px)' }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
