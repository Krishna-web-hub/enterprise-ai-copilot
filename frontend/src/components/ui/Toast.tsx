/**
 * Toast Notification System
 *
 * Provides a context-based toast notification system with cyber styling.
 * Supports success, error, info, and warning types.
 * Toasts auto-dismiss and stack from the top-right.
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import clsx from 'clsx';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: number;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toast: (type: ToastType, title: string, message?: string, duration?: number) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const toastConfig: Record<ToastType, { icon: typeof CheckCircle; color: string; border: string; bg: string }> = {
  success: {
    icon: CheckCircle,
    color: 'text-neon-green',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-400',
    border: 'border-red-500/30',
    bg: 'bg-red-500/5',
  },
  info: {
    icon: Info,
    color: 'text-neon-blue',
    border: 'border-cyber-400/30',
    bg: 'bg-cyber-400/5',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-yellow-400',
    border: 'border-yellow-400/30',
    bg: 'bg-yellow-400/5',
  },
};

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const config = toastConfig[t.type];
  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 50, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={clsx(
        'flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-md min-w-[300px] max-w-[400px]',
        'bg-robot-panel/90 dark:bg-robot-panel/90',
        config.border
      )}
    >
      <Icon className={clsx('h-5 w-5 flex-shrink-0 mt-0.5', config.color)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{t.title}</p>
        {t.message && (
          <p className="mt-0.5 font-mono text-[10px] text-gray-400">{t.message}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(t.id)}
        className="text-gray-500 hover:text-white transition-colors flex-shrink-0"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      {/* Auto-dismiss progress bar */}
      <motion.div
        className={clsx('absolute bottom-0 left-0 h-[2px] rounded-b-xl', config.color.replace('text-', 'bg-'))}
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: (t.duration || 4000) / 1000, ease: 'linear' }}
      />
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let nextId = 0;

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, title: string, message?: string, duration = 4000) => {
    const id = ++nextId;
    setToasts(prev => [...prev, { id, type, title, message, duration }]);
    setTimeout(() => dismiss(id), duration);
  }, [dismiss]);

  const contextValue: ToastContextType = {
    toast: addToast,
    success: (title, message) => addToast('success', title, message),
    error: (title, message) => addToast('error', title, message),
    info: (title, message) => addToast('info', title, message),
    warning: (title, message) => addToast('warning', title, message),
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}

      {/* Toast container */}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2">
        <AnimatePresence mode="popLayout">
          {toasts.map(t => (
            <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
