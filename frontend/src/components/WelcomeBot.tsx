/**
 * WelcomeBot Component — Guided Spotlight Tour
 *
 * Instead of a modal, the bot:
 * - Highlights each sidebar nav item one by one
 * - Shows a tooltip next to the highlighted item explaining what it does
 * - A small floating bot avatar "travels" to each icon
 * - User clicks "Next" to move to the next feature
 * - Shows once for new users, then remembers completion
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import {
  Bot,
  MessageSquare,
  Database,
  Sparkles,
  BookOpen,
  Brain,
  FileText,
  X,
  ChevronRight,
  LayoutDashboard,
} from 'lucide-react';

const TOUR_KEY = 'copilot-tour-completed';

interface TourStep {
  icon: typeof Bot;
  navLabel: string;
  title: string;
  description: string;
  selector: string; // data attribute to find the nav item
}

const tourSteps: TourStep[] = [
  {
    icon: LayoutDashboard,
    navLabel: 'Dashboard',
    title: 'Dashboard',
    description: 'Your command center — see all your stats, recent activity, and quick actions at a glance.',
    selector: '[data-tour="dashboard"]',
  },
  {
    icon: MessageSquare,
    navLabel: 'Chat',
    title: 'AI Chat',
    description: 'Talk to the AI. It automatically picks the right agent — SQL, documents, ML, or general — to answer your question.',
    selector: '[data-tour="chat"]',
  },
  {
    icon: Database,
    navLabel: 'Datasets',
    title: 'Data Repository',
    description: 'Upload your files here — CSV, Excel, JSON, PDF, images. Then ask questions about them or train ML models.',
    selector: '[data-tour="datasets"]',
  },
  {
    icon: Sparkles,
    navLabel: 'Ask Data',
    title: 'Ask Your Data',
    description: 'Type a question in plain English like "top 5 products by revenue" and get instant SQL results with charts.',
    selector: '[data-tour="ask-data"]',
  },
  {
    icon: BookOpen,
    navLabel: 'Documents',
    title: 'Document Q&A',
    description: 'Upload PDFs or Word docs and ask questions. Answers come with citations pointing to the exact source.',
    selector: '[data-tour="documents"]',
  },
  {
    icon: Brain,
    navLabel: 'Models',
    title: 'ML Models',
    description: 'Train machine learning models — classification, regression, clustering. Then run predictions in one click.',
    selector: '[data-tour="models"]',
  },
  {
    icon: FileText,
    navLabel: 'Reports',
    title: 'AI Reports',
    description: 'Generate business reports automatically — executive summaries, forecasts, sales analysis, recommendations.',
    selector: '[data-tour="reports"]',
  },
];

export default function WelcomeBot() {
  const { user } = useAuth();
  const [isVisible, setIsVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [botPosition, setBotPosition] = useState({ top: 100, left: 280 });
  const [tooltipPosition, setTooltipPosition] = useState({ top: 100, left: 290 });

  useEffect(() => {
    const completed = localStorage.getItem(TOUR_KEY);
    if (!completed && user) {
      const timer = setTimeout(() => setIsVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, [user]);

  // Position the bot and tooltip next to the current nav item
  useEffect(() => {
    if (!isVisible) return;

    function updatePosition() {
      const step = tourSteps[currentStep];
      if (!step) return;

      const el = document.querySelector(step.selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        // Bot floats to the right of the nav item
        setBotPosition({
          top: rect.top + rect.height / 2 - 20,
          left: rect.right + 12,
        });
        // Tooltip appears further right
        setTooltipPosition({
          top: rect.top + rect.height / 2 - 40,
          left: rect.right + 56,
        });

        // Add highlight class
        el.classList.add('tour-highlight');
      }

      // Remove highlight from previous items
      tourSteps.forEach((s, i) => {
        if (i !== currentStep) {
          const prevEl = document.querySelector(s.selector);
          prevEl?.classList.remove('tour-highlight');
        }
      });
    }

    updatePosition();
    // Update on resize
    window.addEventListener('resize', updatePosition);
    return () => window.removeEventListener('resize', updatePosition);
  }, [currentStep, isVisible]);

  function handleNext() {
    if (currentStep < tourSteps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      handleDismiss();
    }
  }

  function handleDismiss() {
    // Remove all highlights
    tourSteps.forEach(s => {
      const el = document.querySelector(s.selector);
      el?.classList.remove('tour-highlight');
    });
    setIsVisible(false);
    localStorage.setItem(TOUR_KEY, 'true');
  }

  if (!isVisible) return null;

  const step = tourSteps[currentStep]!;

  return (
    <>
      {/* Semi-transparent overlay (doesn't block sidebar) */}
      <motion.div
        className="fixed inset-0 z-[9990] pointer-events-none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ background: 'rgba(0,0,0,0.3)' }}
      />

      {/* Floating Bot Avatar — travels to each icon */}
      <motion.div
        className="fixed z-[9996] pointer-events-none"
        animate={{ top: botPosition.top, left: botPosition.left }}
        transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      >
        <motion.div
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-robot-panel border-2 border-neon-blue/60 shadow-neon">
            <Bot className="h-5 w-5 text-neon-blue" />
          </div>
        </motion.div>
      </motion.div>

      {/* Tooltip explaining the feature */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          className="fixed z-[9997] pointer-events-auto"
          style={{ top: tooltipPosition.top, left: tooltipPosition.left }}
          initial={{ opacity: 0, x: -10, scale: 0.95 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 10 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        >
          <div className="w-72 rounded-xl border border-cyber-400/30 bg-robot-darker/95 backdrop-blur-xl p-4 shadow-neon">
            {/* Arrow pointing left */}
            <div className="absolute top-5 -left-2 w-3 h-3 rotate-45 bg-robot-darker border-l border-b border-cyber-400/30" />

            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <step.icon className="h-4 w-4 text-neon-blue" />
                <span className="text-sm font-bold text-white">{step.title}</span>
              </div>
              <button onClick={handleDismiss} className="text-gray-500 hover:text-white transition-colors">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Description */}
            <p className="text-xs text-gray-400 leading-relaxed mb-3">
              {step.description}
            </p>

            {/* Footer: progress + next */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {/* Progress */}
                <div className="flex gap-1">
                  {tourSteps.map((_, i) => (
                    <div
                      key={i}
                      className={`w-1.5 h-1.5 rounded-full transition-colors ${
                        i === currentStep ? 'bg-neon-blue' : i < currentStep ? 'bg-cyber-400/40' : 'bg-gray-700'
                      }`}
                    />
                  ))}
                </div>
                <span className="font-mono text-[9px] text-gray-600">
                  {currentStep + 1}/{tourSteps.length}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleDismiss}
                  className="font-mono text-[9px] text-gray-500 hover:text-gray-300 transition-colors uppercase"
                >
                  Skip
                </button>
                <motion.button
                  onClick={handleNext}
                  className="flex items-center gap-1 rounded-md bg-cyber-600 px-3 py-1.5 text-xs font-mono text-white hover:bg-cyber-500 transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {currentStep === tourSteps.length - 1 ? 'Done' : 'Next'}
                  <ChevronRight className="h-3 w-3" />
                </motion.button>
              </div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </>
  );
}
