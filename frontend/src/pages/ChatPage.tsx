/**
 * Chat Page — Advanced Terminal/Command-Center
 *
 * Features:
 * - Expandable AI "thinking" panel showing reasoning steps
 * - Pinned sessions section (max 5) with rank ordering
 * - Right-click/menu for rename, delete, pin/unpin
 * - Auto-rename session title from first message summary
 * - Robotic terminal aesthetic
 */

import { useEffect, useRef, useState } from 'react';
import {
  Send,
  Plus,
  MessageSquare,
  Bot,
  User,
  Clock,
  ChevronDown,
  ChevronUp,
  Loader2,
  Terminal,
  Cpu,
  Pin,
  PinOff,
  Trash2,
  Pencil,
  MoreVertical,
  X,
  Check,
  Brain,
  Zap,
  Paperclip,
  Image,
  FileText,
  Mic,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import {
  AgentMetadata,
  ChatMessage,
  ChatSession,
  createSession,
  deleteSession,
  getMessages,
  listSessions,
  pinSession,
  renameSession,
  sendMessage,
  sendMultimodalMessage,
  unpinSession,
} from '../services/chat';
import { useToast } from '../components/ui/Toast';
import { useTheme } from '../context/ThemeContext';

// ─── Agent labels and colors ──────────────────────────────────

const AGENT_LABELS: Record<string, string> = {
  sql_agent: 'SQL Agent',
  rag_agent: 'RAG Agent',
  ml_agent: 'ML Agent',
  vision_agent: 'Vision Agent',
  general: 'General Agent',
};

const AGENT_COLORS: Record<string, string> = {
  sql_agent: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  rag_agent: 'text-green-400 bg-green-400/10 border-green-400/30',
  ml_agent: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
  vision_agent: 'text-pink-400 bg-pink-400/10 border-pink-400/30',
  general: 'text-gray-400 bg-gray-400/10 border-gray-400/30',
};

function AgentBadge({ agent }: { agent: string }) {
  return (
    <span className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${AGENT_COLORS[agent] || AGENT_COLORS.general}`}>
      {AGENT_LABELS[agent] || agent}
    </span>
  );
}

// ─── Thinking/Reasoning Panel ─────────────────────────────────

function ThinkingPanel({ metadata }: { metadata: AgentMetadata }) {
  const [expanded, setExpanded] = useState(false);

  const hasThinking = metadata.plan_reasoning || metadata.plan_steps || metadata.step_results;
  if (!hasThinking) return null;

  return (
    <div className="mt-2 rounded-lg border border-cyber-400/20 bg-robot-darker/80 text-xs overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-gray-400 hover:text-gray-200 transition-colors"
      >
        <Brain className="h-3 w-3 text-neon-purple" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-400/70">AI Thinking Process</span>
        <span className="ml-auto flex items-center gap-2">
          {metadata.total_time_ms && (
            <span className="flex items-center gap-1 font-mono text-[9px] text-gray-600">
              <Clock className="h-2.5 w-2.5" />
              {(metadata.total_time_ms / 1000).toFixed(1)}s
            </span>
          )}
          {metadata.agents_used && (
            <span className="flex gap-1">
              {metadata.agents_used.map((a, i) => (
                <AgentBadge key={i} agent={a} />
              ))}
            </span>
          )}
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-robot-border/20 px-3 py-3 space-y-3">
              {/* Plan reasoning */}
              {metadata.plan_reasoning && (
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Zap className="h-3 w-3 text-neon-blue/70" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-cyber-400/60">Reasoning</span>
                  </div>
                  <p className="text-gray-300 font-mono text-[11px] leading-relaxed pl-4 border-l border-cyber-400/20">
                    {metadata.plan_reasoning}
                  </p>
                </div>
              )}

              {/* Plan steps */}
              {metadata.plan_steps && metadata.plan_steps.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Terminal className="h-3 w-3 text-neon-green/70" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-cyber-400/60">Execution Plan</span>
                  </div>
                  <div className="space-y-1.5 pl-4">
                    {metadata.plan_steps.map((step, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="font-mono text-[9px] text-gray-600 mt-0.5 w-4">{String(i + 1).padStart(2, '0')}</span>
                        <AgentBadge agent={step.agent} />
                        <span className="text-gray-400 font-mono text-[10px] flex-1">{step.instruction}</span>
                        {metadata.step_results && metadata.step_results[i] && (
                          <span className={`w-1.5 h-1.5 rounded-full mt-1 ${metadata.step_results[i]?.success ? 'bg-neon-green' : 'bg-red-400'}`} />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Step results detail */}
              {metadata.step_results && metadata.step_results.some(r => r.result) && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Cpu className="h-3 w-3 text-purple-400/70" />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-cyber-400/60">Agent Outputs</span>
                  </div>
                  <div className="space-y-1.5 pl-4">
                    {metadata.step_results.filter(r => r.result).map((r, i) => (
                      <div key={i} className="rounded-md border border-robot-border/20 bg-robot-panel/30 p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <AgentBadge agent={r.agent} />
                          <span className={`w-1.5 h-1.5 rounded-full ${r.success ? 'bg-neon-green' : 'bg-red-400'}`} />
                        </div>
                        <p className="font-mono text-[10px] text-gray-500 line-clamp-3">{r.result}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Session Context Menu ─────────────────────────────────────

function SessionMenu({
  session,
  onRename,
  onDelete,
  onPin,
  onUnpin,
  onClose,
}: {
  session: ChatSession;
  onRename: () => void;
  onDelete: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onClose: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-robot-border/50 bg-robot-darker shadow-lg overflow-hidden"
    >
      <button
        onClick={() => { onRename(); onClose(); }}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 hover:bg-cyber-400/10 hover:text-white transition-colors"
      >
        <Pencil className="h-3 w-3" /> Rename
      </button>
      {session.is_pinned ? (
        <button
          onClick={() => { onUnpin(); onClose(); }}
          className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 hover:bg-cyber-400/10 hover:text-white transition-colors"
        >
          <PinOff className="h-3 w-3" /> Unpin
        </button>
      ) : (
        <button
          onClick={() => { onPin(); onClose(); }}
          className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 hover:bg-cyber-400/10 hover:text-white transition-colors"
        >
          <Pin className="h-3 w-3" /> Pin
        </button>
      )}
      <button
        onClick={() => { onDelete(); onClose(); }}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
      >
        <Trash2 className="h-3 w-3" /> Delete
      </button>
    </motion.div>
  );
}

// ─── Markdown Formatter ───────────────────────────────────────

/**
 * Simple markdown to HTML converter for chat messages.
 * Supports: **bold**, *italic*, `code`, ```code blocks```, and line breaks.
 */
function formatMarkdown(text: string): string {
  let html = text
    // Escape HTML entities first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Code blocks (```...```)
    .replace(/```([\s\S]*?)```/g, '<pre class="my-2 rounded-md bg-robot-darker/50 border border-robot-border/20 p-2 font-mono text-[11px] text-cyber-400 overflow-x-auto">$1</pre>')
    // Inline code (`...`)
    .replace(/`([^`]+)`/g, '<code class="rounded bg-robot-darker/50 border border-robot-border/20 px-1.5 py-0.5 font-mono text-[11px] text-cyber-400">$1</code>')
    // Bold (**...**)
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-white">$1</strong>')
    // Italic (*...*)
    .replace(/\*(.+?)\*/g, '<em class="italic">$1</em>')
    // Numbered lists (1. 2. 3.)
    .replace(/^(\d+)\.\s/gm, '<span class="text-neon-blue font-bold mr-1">$1.</span>')
    // Bullet points (- item)
    .replace(/^-\s/gm, '<span class="text-neon-blue mr-1">•</span>');

  return html;
}

// ─── Message Content Renderer ─────────────────────────────────

/**
 * Renders message content with inline attachment previews.
 * Detects [📎 filename] patterns and attachment metadata to show
 * image thumbnails, file icons, and audio indicators inline.
 */
function MessageContent({ content, metadata, role }: { content: string; metadata: AgentMetadata | null; role: string }) {
  // Check if metadata has attachments info
  const attachments: { filename: string; category: string; content_type: string; storage_key: string }[] =
    (metadata as Record<string, unknown>)?.attachments as typeof attachments || [];

  // Split content into text lines and attachment references
  const lines = content.split('\n');
  const textLines: string[] = [];
  const attachmentRefs: string[] = [];

  for (const line of lines) {
    if (line.match(/^\[📎\s.+\]$/) || line.match(/^\[Attached\s/)) {
      attachmentRefs.push(line);
    } else {
      textLines.push(line);
    }
  }

  const textContent = textLines.join('\n').trim();

  return (
    <div className="space-y-2">
      {/* Text content */}
      {textContent && (
        <div className="text-sm whitespace-pre-wrap leading-relaxed" dangerouslySetInnerHTML={{ __html: formatMarkdown(textContent) }} />
      )}

      {/* Inline attachment indicators */}
      {(attachments.length > 0 || attachmentRefs.length > 0) && (
        <div className="flex flex-wrap gap-2 mt-2">
          {attachments.length > 0 ? (
            // Render from metadata (structured data)
            attachments.map((att, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-2 rounded-md border px-2 py-1.5 ${
                  role === 'user'
                    ? 'border-cyber-400/20 bg-cyber-400/5'
                    : 'border-robot-border/30 bg-robot-darker/50'
                }`}
              >
                {att.category === 'image' ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-purple-500/10 border border-purple-500/20">
                    <Image className="h-5 w-5 text-purple-400" />
                  </div>
                ) : att.category === 'audio' ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-neon-green/10 border border-neon-green/20">
                    <Mic className="h-5 w-5 text-neon-green" />
                  </div>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-400/10 border border-blue-400/20">
                    <FileText className="h-5 w-5 text-blue-400" />
                  </div>
                )}
                <div>
                  <p className="font-mono text-[10px] text-gray-300 max-w-[120px] truncate">{att.filename}</p>
                  <p className="font-mono text-[8px] text-gray-600 uppercase">{att.category}</p>
                </div>
              </div>
            ))
          ) : (
            // Render from parsed text references (fallback for optimistic messages)
            attachmentRefs.map((ref, idx) => {
              const filename = ref.replace(/^\[📎\s/, '').replace(/\]$/, '').replace(/^\[Attached\s\w+:\s/, '').replace(/\s\(.+\)\]$/, '');
              const isImage = ref.toLowerCase().includes('image') || /\.(png|jpg|jpeg|gif|webp|svg)/.test(ref.toLowerCase());
              const isAudio = ref.toLowerCase().includes('audio') || /\.(mp3|wav|ogg|m4a)/.test(ref.toLowerCase());

              return (
                <div
                  key={idx}
                  className={`flex items-center gap-2 rounded-md border px-2 py-1.5 ${
                    role === 'user'
                      ? 'border-cyber-400/20 bg-cyber-400/5'
                      : 'border-robot-border/30 bg-robot-darker/50'
                  }`}
                >
                  {isImage ? (
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-purple-500/10 border border-purple-500/20">
                      <Image className="h-4 w-4 text-purple-400" />
                    </div>
                  ) : isAudio ? (
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neon-green/10 border border-neon-green/20">
                      <Mic className="h-4 w-4 text-neon-green" />
                    </div>
                  ) : (
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-400/10 border border-blue-400/20">
                      <FileText className="h-4 w-4 text-blue-400" />
                    </div>
                  )}
                  <span className="font-mono text-[10px] text-gray-300 max-w-[100px] truncate">{filename}</span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

// ─── Analysis Animation Step ──────────────────────────────────

function AnalysisStep({ label, delay }: { label: string; delay: number }) {
  return (
    <motion.div
      className="flex items-center gap-2"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3 }}
    >
      <motion.div
        className="w-1.5 h-1.5 rounded-full bg-neon-blue"
        animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
        transition={{ delay, duration: 1.2, repeat: Infinity }}
      />
      <motion.span
        className="font-mono text-[10px] text-gray-400"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ delay, duration: 1.5, repeat: Infinity }}
      >
        {label}
      </motion.span>
      <motion.div
        className="flex-1 h-[1px] bg-gradient-to-r from-robot-border/30 to-transparent"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: delay + 0.2, duration: 0.5 }}
        style={{ transformOrigin: 'left' }}
      />
    </motion.div>
  );
}

// ─── Smart Title Generation ───────────────────────────────────

/**
 * Generates a concise session title from the user's message.
 * Extracts the core topic/intent rather than just truncating.
 * Target: 20-25 chars max to fit sidebar width.
 */
function generateSessionTitle(message: string): string {
  const maxLen = 24;

  // Remove filler words and clean up
  const fillers = /^(hey|hi|hello|please|can you|could you|i want to|i need to|help me|tell me|show me|what is|what are|how to|how do i|how can i)\s+/i;
  let cleaned = message.trim().replace(fillers, '');

  // If it's a question, extract the subject
  const questionMatch = cleaned.match(/(?:what|how|why|when|where|which|who)\s+(.+?)(?:\?|$)/i);
  if (questionMatch && questionMatch[1]) {
    cleaned = questionMatch[1].trim();
  }

  // Remove trailing punctuation
  cleaned = cleaned.replace(/[?.!,;:]+$/, '').trim();

  // Capitalize first letter
  if (cleaned.length > 0) {
    cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }

  // Truncate at word boundary
  if (cleaned.length > maxLen) {
    const truncated = cleaned.slice(0, maxLen);
    const lastSpace = truncated.lastIndexOf(' ');
    if (lastSpace > maxLen * 0.5) {
      cleaned = truncated.slice(0, lastSpace) + '...';
    } else {
      cleaned = truncated + '...';
    }
  }

  // Fallback if empty after cleaning
  if (!cleaned || cleaned.length < 3) {
    return message.slice(0, maxLen).trim() + (message.length > maxLen ? '...' : '');
  }

  return cleaned;
}

// ─── Main Chat Page ───────────────────────────────────────────

export default function ChatPage() {
  const toast = useToast();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadSessions(); }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Close menu on outside click
  useEffect(() => {
    function handleClick() { setMenuOpenId(null); }
    if (menuOpenId !== null) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [menuOpenId]);

  async function loadSessions() {
    setIsLoadingSessions(true);
    try {
      const response = await listSessions();
      setSessions(response.sessions);
      if (response.sessions.length > 0 && response.sessions[0]) {
        await selectSession(response.sessions[0].id);
      }
    } catch { /* empty state */ }
    finally { setIsLoadingSessions(false); }
  }

  async function selectSession(sessionId: number) {
    setActiveSessionId(sessionId);
    try {
      const response = await getMessages(sessionId);
      setMessages(response.messages);
    } catch { setMessages([]); }
  }

  async function handleNewSession() {
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch { /* non-critical */ }
  }

  async function handleSend() {
    if ((!input.trim() && attachments.length === 0) || !activeSessionId) return;

    const content = input.trim();
    const filesToSend = [...attachments];
    setInput('');
    setAttachments([]);
    setIsSending(true);

    // Optimistic user message
    const attachmentText = filesToSend.length > 0
      ? filesToSend.map(f => `[📎 ${f.name}]`).join(' ')
      : '';
    const displayContent = [content, attachmentText].filter(Boolean).join('\n');

    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: displayContent,
      metadata: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      // Use multimodal endpoint if files attached, otherwise standard
      if (filesToSend.length > 0) {
        await sendMultimodalMessage(activeSessionId, content, filesToSend);
      } else {
        await sendMessage(activeSessionId, content);
      }
      const response = await getMessages(activeSessionId);
      setMessages(response.messages);

      // Auto-rename session: generate a short summary title from the conversation
      const activeSession = sessions.find(s => s.id === activeSessionId);
      if (activeSession && activeSession.title === 'New Chat' && response.messages.length <= 2) {
        const summary = generateSessionTitle(content);
        try {
          const updated = await renameSession(activeSessionId, summary);
          setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
        } catch { /* non-critical */ }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'assistant', content: 'ERROR: Processing failed. Please retry.', metadata: null, created_at: new Date().toISOString() },
      ]);
    } finally { setIsSending(false); }
  }

  async function handleRename(sessionId: number) {
    if (!renameValue.trim()) { setRenamingId(null); return; }
    try {
      const updated = await renameSession(sessionId, renameValue.trim());
      setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
      toast.success('Renamed', `Session renamed to "${renameValue.trim()}"`);
    } catch { toast.error('Rename failed'); }
    setRenamingId(null);
  }

  async function handleDelete(sessionId: number) {
    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0 && remaining[0]) {
          await selectSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
      toast.success('Deleted', 'Session removed');
    } catch { toast.error('Delete failed'); }
  }

  async function handlePin(sessionId: number) {
    try {
      const updated = await pinSession(sessionId);
      setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
      toast.info('Pinned', 'Session pinned to top');
    } catch { toast.warning('Pin failed', 'Max 5 pinned sessions'); }
  }

  async function handleUnpin(sessionId: number) {
    try {
      const updated = await unpinSession(sessionId);
      setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
      toast.info('Unpinned');
    } catch { toast.error('Unpin failed'); }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  // Split sessions into pinned and regular
  const pinnedSessions = sessions.filter(s => s.is_pinned).sort((a, b) => a.pin_order - b.pin_order);
  const regularSessions = sessions.filter(s => !s.is_pinned);

  // ─── Render Session Item ──────────────────────────────────────
  function renderSessionItem(session: ChatSession) {
    const isActive = activeSessionId === session.id;
    const isRenaming = renamingId === session.id;

    return (
      <li key={session.id} className="relative">
        {isRenaming ? (
          <div className="flex items-center gap-1 px-2 py-1.5">
            <input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRename(session.id); if (e.key === 'Escape') setRenamingId(null); }}
              className="flex-1 rounded-md bg-robot-panel border border-cyber-400/30 px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-neon-blue"
            />
            <button onClick={() => handleRename(session.id)} className="p-1 text-neon-green hover:text-white"><Check className="h-3 w-3" /></button>
            <button onClick={() => setRenamingId(null)} className="p-1 text-gray-500 hover:text-white"><X className="h-3 w-3" /></button>
          </div>
        ) : (
          <div className="group flex items-center">
            <button
              onClick={() => selectSession(session.id)}
              className={`flex flex-1 items-center gap-2 rounded-lg px-3 py-2 text-left text-xs transition-all duration-200 ${
                isActive
                  ? 'bg-cyber-400/10 text-white border border-cyber-400/30'
                  : 'text-gray-400 border border-transparent hover:text-gray-200 hover:bg-white/5 hover:border-robot-border/30'
              }`}
            >
              {session.is_pinned && <Pin className="h-3 w-3 text-neon-blue/60 flex-shrink-0" />}
              <MessageSquare className={`h-3 w-3 flex-shrink-0 ${isActive ? 'text-neon-blue' : 'text-gray-600'}`} />
              <span className="truncate flex-1">{session.title}</span>
            </button>
            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === session.id ? null : session.id); }}
                className="p-1.5 text-gray-600 opacity-0 group-hover:opacity-100 hover:text-white transition-all"
              >
                <MoreVertical className="h-3 w-3" />
              </button>
              <AnimatePresence>
                {menuOpenId === session.id && (
                  <SessionMenu
                    session={session}
                    onRename={() => { setRenamingId(session.id); setRenameValue(session.title); }}
                    onDelete={() => handleDelete(session.id)}
                    onPin={() => handlePin(session.id)}
                    onUnpin={() => handleUnpin(session.id)}
                    onClose={() => setMenuOpenId(null)}
                  />
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </li>
    );
  }

  return (
    <div className={clsx(
      'flex h-[calc(100vh-7rem)] rounded-xl overflow-hidden border',
      isDark ? 'border-robot-border/30' : 'border-gray-200 shadow-lg'
    )}>
      {/* Sessions sidebar */}
      <div className={clsx(
        'flex w-64 flex-col border-r',
        isDark ? 'border-robot-border/30 bg-robot-darker' : 'border-gray-100 bg-white/80 backdrop-blur-sm'
      )}>
        <div className={clsx(
          'flex items-center justify-between border-b px-4 py-3',
          isDark ? 'border-robot-border/30' : 'border-gray-100'
        )}>
          <div className="flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Sessions</span>
          </div>
          <motion.button
            onClick={handleNewSession}
            className="rounded-md p-1.5 text-gray-500 hover:text-neon-blue hover:bg-cyber-400/10 border border-transparent hover:border-cyber-400/30 transition-all"
            aria-label="New chat"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <Plus className="h-4 w-4" />
          </motion.button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoadingSessions ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-cyber-400/50" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="px-3 py-8 text-center font-mono text-[10px] text-gray-600 uppercase">
              No sessions initialized
            </div>
          ) : (
            <>
              {/* Pinned sessions */}
              {pinnedSessions.length > 0 && (
                <div className="mb-2">
                  <div className="flex items-center gap-1.5 px-3 py-1.5">
                    <Pin className="h-2.5 w-2.5 text-neon-blue/50" />
                    <span className="font-mono text-[8px] uppercase tracking-widest text-gray-600">
                      Pinned ({pinnedSessions.length}/5)
                    </span>
                  </div>
                  <ul className="space-y-0.5">
                    {pinnedSessions.map(renderSessionItem)}
                  </ul>
                  <div className="mx-3 my-2 h-[1px] bg-gradient-to-r from-transparent via-robot-border/30 to-transparent" />
                </div>
              )}

              {/* Regular sessions */}
              {regularSessions.length > 0 && (
                <div>
                  {pinnedSessions.length > 0 && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5">
                      <MessageSquare className="h-2.5 w-2.5 text-gray-600" />
                      <span className="font-mono text-[8px] uppercase tracking-widest text-gray-600">Recent</span>
                    </div>
                  )}
                  <ul className="space-y-0.5">
                    {regularSessions.map(renderSessionItem)}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className={clsx('flex flex-1 flex-col', isDark ? 'bg-robot-dark' : 'bg-gradient-to-b from-slate-50/50 to-white')}>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {!activeSessionId && (
            <div className="flex h-full items-center justify-center text-center">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <div className="relative mx-auto h-16 w-16 flex items-center justify-center">
                  <Bot className="h-8 w-8 text-cyber-400/50" />
                  <span className="absolute inset-0 rounded-full border border-cyber-400/20 animate-pulse-ring" />
                </div>
                <p className="mt-4 text-sm font-medium text-gray-400">AI Communication Hub</p>
                <p className="mt-1 font-mono text-[10px] text-gray-600 uppercase tracking-wider">
                  Initialize a session to begin
                </p>
                <motion.button onClick={handleNewSession} className="btn-cyber-filled mt-4" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  New Session
                </motion.button>
              </motion.div>
            </div>
          )}

          {activeSessionId && messages.length === 0 && !isSending && (
            <div className="flex h-full items-center justify-center text-center">
              <div>
                <Cpu className="mx-auto h-8 w-8 text-cyber-400/30" />
                <p className="mt-3 text-sm text-gray-500">Ask a business question about your data, documents, or models.</p>
                <p className="mt-1 font-mono text-[10px] text-gray-600">e.g. &quot;What were the top selling products?&quot;</p>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.02 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="max-w-[75%]">
                <div className="flex items-start gap-2">
                  {msg.role === 'assistant' && (
                    <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-cyber-400/10 border border-cyber-400/20">
                      <Bot className="h-3.5 w-3.5 text-neon-blue" />
                    </div>
                  )}
                  <div className={clsx('rounded-xl px-4 py-3',
                    msg.role === 'user'
                      ? isDark
                        ? 'bg-cyber-600/20 border border-cyber-400/20 text-white'
                        : 'bg-gradient-to-br from-cyan-500 to-teal-500 text-white border-0 shadow-md'
                      : isDark
                        ? 'bg-robot-panel border border-robot-border/30 text-gray-200'
                        : 'bg-white border border-gray-100 text-gray-700 shadow-sm'
                  )}>
                    <MessageContent content={msg.content} metadata={msg.metadata} role={msg.role} />
                  </div>
                  {msg.role === 'user' && (
                    <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-purple-500/10 border border-purple-500/20">
                      <User className="h-3.5 w-3.5 text-purple-400" />
                    </div>
                  )}
                </div>

                {/* Thinking panel for assistant messages */}
                {msg.role === 'assistant' && msg.metadata && (
                  <div className="ml-9">
                    <ThinkingPanel metadata={msg.metadata} />
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {isSending && (
            <motion.div
              className="flex justify-start"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="rounded-xl bg-robot-panel border border-cyber-400/20 p-4 w-80 overflow-hidden relative">
                {/* Animated scan line across the card */}
                <motion.div
                  className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-neon-blue/60 to-transparent"
                  animate={{ top: ['0%', '100%', '0%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                />

                {/* Header */}
                <div className="flex items-center gap-2 mb-3">
                  <div className="relative">
                    <Brain className="h-5 w-5 text-neon-blue animate-glow-pulse" />
                    <span className="absolute -inset-1 rounded-full border border-cyber-400/30 animate-pulse-ring" />
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-cyber-400">
                    Neural Processing Active
                  </span>
                </div>

                {/* Animated analysis steps */}
                <div className="space-y-2">
                  <AnalysisStep label="Analyzing query" delay={0} />
                  <AnalysisStep label="Planning execution" delay={0.8} />
                  <AnalysisStep label="Running agents" delay={1.6} />
                  <AnalysisStep label="Synthesizing response" delay={2.4} />
                </div>

                {/* Bottom progress bar */}
                <div className="mt-3 h-[2px] w-full rounded-full bg-robot-border/30 overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-neon-blue via-neon-purple to-neon-blue rounded-full"
                    animate={{ x: ['-100%', '100%'] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ width: '50%' }}
                  />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        {activeSessionId && (
          <div
            className={clsx(
              'border-t px-6 py-4 transition-colors',
              isDark ? 'border-robot-border/30 bg-robot-darker/50' : 'border-gray-100 bg-white/60 backdrop-blur-sm',
              isDragOver && (isDark ? 'bg-cyber-400/5 border-t-neon-blue/50' : 'bg-cyan-50/50 border-t-cyan-300')
            )}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              const droppedFiles = Array.from(e.dataTransfer.files);
              setAttachments(prev => [...prev, ...droppedFiles]);
            }}
          >
            {/* Attachment preview bar */}
            {attachments.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {attachments.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="relative rounded-lg border border-robot-border/40 bg-robot-panel/50 overflow-hidden group"
                  >
                    {file.type.startsWith('image/') ? (
                      /* Image thumbnail preview */
                      <div className="relative w-20 h-20">
                        <img
                          src={URL.createObjectURL(file)}
                          alt={file.name}
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                        <span className="absolute bottom-1 left-1 font-mono text-[8px] text-white/80 max-w-[70px] truncate">
                          {file.name}
                        </span>
                      </div>
                    ) : (
                      /* File/audio preview */
                      <div className="flex items-center gap-2 px-3 py-2">
                        {file.type.startsWith('audio/') ? (
                          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neon-green/10 border border-neon-green/30">
                            <Mic className="h-4 w-4 text-neon-green" />
                          </div>
                        ) : (
                          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-400/10 border border-blue-400/30">
                            <FileText className="h-4 w-4 text-blue-400" />
                          </div>
                        )}
                        <div className="flex flex-col">
                          <span className="font-mono text-[10px] text-gray-300 max-w-[100px] truncate">{file.name}</span>
                          <span className="font-mono text-[8px] text-gray-600">{(file.size / 1024).toFixed(0)}KB</span>
                        </div>
                      </div>
                    )}
                    {/* Remove button */}
                    <button
                      onClick={() => setAttachments(prev => prev.filter((_, i) => i !== idx))}
                      className="absolute top-1 right-1 rounded-full bg-black/60 p-0.5 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Input row */}
            <div className="flex items-end gap-2">
              {/* Attachment buttons */}
              <div className="flex items-center gap-1 pb-1">
                <button
                  onClick={() => imageInputRef.current?.click()}
                  className="rounded-md p-2 text-gray-500 hover:text-purple-400 hover:bg-purple-400/10 border border-transparent hover:border-purple-400/30 transition-all"
                  title="Attach image"
                  type="button"
                >
                  <Image className="h-4 w-4" />
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-md p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-400/10 border border-transparent hover:border-blue-400/30 transition-all"
                  title="Attach file"
                  type="button"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  onClick={() => audioInputRef.current?.click()}
                  className="rounded-md p-2 text-gray-500 hover:text-neon-green hover:bg-neon-green/10 border border-transparent hover:border-neon-green/30 transition-all"
                  title="Attach audio"
                  type="button"
                >
                  <Mic className="h-4 w-4" />
                </button>
              </div>

              {/* Text input */}
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  placeholder={attachments.length > 0 ? "Add a message about the files..." : "Enter command..."}
                  className="input-cyber w-full pr-4 resize-none"
                  disabled={isSending}
                />
              </div>

              {/* Send button */}
              <motion.button
                onClick={handleSend}
                disabled={isSending || (!input.trim() && attachments.length === 0)}
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyber-600 text-white hover:bg-cyber-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-neon/50 hover:shadow-neon"
                aria-label="Send message"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Send className="h-4 w-4" />
              </motion.button>
            </div>

            {/* Hidden file inputs - outside flex for reliable DOM access */}
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              multiple
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                  setAttachments(prev => [...prev, ...Array.from(files)]);
                }
                e.target.value = '';
              }}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.json"
              multiple
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                  setAttachments(prev => [...prev, ...Array.from(files)]);
                }
                e.target.value = '';
              }}
            />
            <input
              ref={audioInputRef}
              type="file"
              accept="audio/*"
              multiple
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                  setAttachments(prev => [...prev, ...Array.from(files)]);
                }
                e.target.value = '';
              }}
            />

            {/* Hints */}
            <div className="mt-2 flex items-center justify-between">
              <p className="font-mono text-[9px] text-gray-700">
                {isDragOver ? '↓ DROP FILES HERE' : 'Drag & drop files or use buttons'}
              </p>
              <p className="font-mono text-[9px] text-gray-700">
                SHIFT+ENTER new line // ENTER send
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
