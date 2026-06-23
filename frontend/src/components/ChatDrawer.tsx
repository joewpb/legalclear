/**
 * ChatDrawer.tsx — LegalClear Chat System
 *
 * Modal drawer that slides in over explainer content.
 *   - Mobile: 100% screen width
 *   - Desktop: 50% screen width (from right)
 *   - 5-message limit per session
 *   - localStorage persistence (survives page reload)
 *   - SSE streaming from /api/chat/{module}
 *   - Paywall overlay inside drawer at 5 messages
 */

import { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Module label mapping — used for display text
// ---------------------------------------------------------------------------

const MODULE_LABELS: Record<string, string> = {
  small_claims: "Small Claims Court",
  criminal_procedure: "Criminal Procedure",
  police_report: "Police Reports",
  discovery_motion: "Discovery Rules & Motions",
  property_casualty: "Property & Casualty Law",
  wills_trusts: "Wills, Trusts & Probate",
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  id: string;
  role: "user" | "expert";
  content: string;
  disclaimer?: string;
  timestamp: number;
}

interface ChatDrawerProps {
  module: string;
  isOpen?: boolean;
  onClose: () => void;
  language?: "en" | "es";
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function getSessionKey(module: string): string {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return `legalclear_chat_${module}_${today}`;
}

function loadMessages(module: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(getSessionKey(module));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(module: string, messages: ChatMessage[]): void {
  localStorage.setItem(getSessionKey(module), JSON.stringify(messages));
}

function clearMessages(module: string): void {
  localStorage.removeItem(getSessionKey(module));
}

// ---------------------------------------------------------------------------
// SSE reader
// ---------------------------------------------------------------------------

async function* readSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<string, void, unknown> {
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        yield line.slice(6);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const isMobile = typeof window !== "undefined" && window.innerWidth < 768;

const css = {
  /* ── Overlay ── */
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0, 0, 0, 0.5)",
    zIndex: 1000,
    display: "flex",
    justifyContent: "flex-end",
  } as React.CSSProperties,

  /* ── Drawer ── */
  drawer: {
    width: "100%",
    maxWidth: "50%",
    background: "#fff",
    display: "flex",
    flexDirection: "column",
    boxShadow: "-4px 0 24px rgba(0,0,0,0.12)",
    animation: "slideIn 0.3s ease-out",
  } as React.CSSProperties,

  drawerMobile: {
    maxWidth: "100%",
  } as React.CSSProperties,

  /* ── Header ── */
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 20px",
    borderBottom: "1px solid #E5E5E0",
    background: "linear-gradient(135deg, #1E40AF, #3B82F6)",
    color: "#fff",
  } as React.CSSProperties,

  headerTitle: {
    fontSize: 16,
    fontWeight: 600,
    fontFamily: "var(--font-serif, Georgia)",
  } as React.CSSProperties,

  closeBtn: {
    background: "none",
    border: "none",
    color: "#fff",
    fontSize: 20,
    cursor: "pointer",
    padding: "4px 8px",
    borderRadius: 4,
    opacity: 0.8,
  } as React.CSSProperties,

  /* ── New chat button in header ── */
  newChatBtn: {
    background: "rgba(255,255,255,0.2)",
    border: "1px solid rgba(255,255,255,0.3)",
    color: "#fff",
    fontSize: 12,
    cursor: "pointer",
    padding: "4px 10px",
    borderRadius: 4,
    marginRight: 8,
  } as React.CSSProperties,

  /* ── Message list ── */
  messageList: {
    flex: 1,
    overflowY: "auto",
    padding: "16px 20px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  } as React.CSSProperties,

  /* ── Message bubbles ── */
  messageRow: (role: "user" | "expert"): React.CSSProperties => ({
    display: "flex",
    justifyContent: role === "user" ? "flex-end" : "flex-start",
  }),

  messageBubble: (role: "user" | "expert"): React.CSSProperties => ({
    maxWidth: "85%",
    padding: "10px 14px",
    borderRadius: 12,
    fontSize: 14,
    lineHeight: 1.6,
    background: role === "user" ? "#4361EE" : "#F5F7FA",
    color: role === "user" ? "#fff" : "#1A1A1A",
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
    borderTopRightRadius: role === "user" ? 4 : 12,
    borderTopLeftRadius: role === "expert" ? 4 : 12,
  }),

  disclaimer: {
    marginTop: 8,
    padding: "8px 12px",
    background: "#f5f5f5",
    borderLeft: "3px solid #6B6B66",
    fontSize: 11,
    lineHeight: 1.5,
    color: "#6B6B66",
  } as React.CSSProperties,

  /* ── Loading ── */
  loadingBubble: {
    maxWidth: "85%",
    padding: "10px 14px",
    borderRadius: 12,
    fontSize: 14,
    background: "#F5F7FA",
    color: "#6B6B66",
    fontStyle: "italic",
  } as React.CSSProperties,

  /* ── Input area ── */
  inputArea: {
    borderTop: "1px solid #E0E7FF",
    padding: "12px 20px",
    display: "flex",
    gap: 8,
    alignItems: "flex-end",
  } as React.CSSProperties,

  textarea: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    padding: "10px 14px",
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    fontSize: 14,
    resize: "none" as const,
    fontFamily: "inherit",
    lineHeight: 1.5,
  } as React.CSSProperties,

  sendBtn: {
    padding: "10px 20px",
    border: "none",
    borderRadius: 16,
    background: "linear-gradient(135deg, #4361EE, #3A0CA3)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  } as React.CSSProperties,

  sendBtnDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  } as React.CSSProperties,

  /* ── Counter ── */
  counter: {
    fontSize: 12,
    color: "#6B7280",
    textAlign: "center" as const,
    padding: "4px 0",
  } as React.CSSProperties,

  /* ── Paywall overlay inside drawer ── */
  paywallOverlay: {
    position: "absolute" as const,
    inset: 0,
    background: "rgba(255,255,255,0.95)",
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10,
    padding: "40px 20px",
    textAlign: "center" as const,
  } as React.CSSProperties,

  paywallTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: "#1A1A2E",
    marginBottom: 8,
  } as React.CSSProperties,

  paywallText: {
    fontSize: 14,
    color: "#6B7280",
    marginBottom: 20,
    lineHeight: 1.6,
  } as React.CSSProperties,

  paywallBtn: {
    padding: "12px 28px",
    border: "none",
    borderRadius: 16,
    background: "linear-gradient(135deg, #635BFF, #7C3AED)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 15,
    cursor: "pointer",
    marginBottom: 10,
    boxShadow: "0 4px 16px rgba(99,91,255,0.3)",
  } as React.CSSProperties,

  paywallCloseBtn: {
    padding: "8px 20px",
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    background: "#fff",
    color: "#6B7280",
    fontWeight: 500,
    fontSize: 14,
    cursor: "pointer",
  } as React.CSSProperties,

  /* ── Floating chat button ── */
  floatingBtn: {
    position: "fixed",
    bottom: 24,
    right: 24,
    padding: "12px 20px",
    border: "none",
    borderRadius: 28,
    background: "linear-gradient(135deg, #4361EE, #3A0CA3)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(67,97,238,0.35)",
    zIndex: 500,
    display: "flex",
    alignItems: "center",
    gap: 8,
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Chat button that floats on explainer pages
// ---------------------------------------------------------------------------

export function ChatButton({
  module,
  onClick,
}: {
  module: string;
  onClick: () => void;
}) {
  return (
    <button
      style={css.floatingBtn}
      onClick={onClick}
      aria-label={`Chat with ${MODULE_LABELS[module] || module} expert`}
    >
      {/* Chat bubble icon */}
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
      </svg>
      Chat with the Expert
    </button>
  );
}

// ---------------------------------------------------------------------------
// ChatDrawer component
// ---------------------------------------------------------------------------

export default function ChatDrawer({
  module,
  isOpen = true,
  onClose,
  language = "en",
}: ChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadMessages(module),
  );
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [paywalled, setPaywalled] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const MAX_MESSAGES = 5;

  const userMessageCount = messages.filter((m) => m.role === "user").length;
  const atLimit = userMessageCount >= MAX_MESSAGES;

  // Scroll to bottom on new messages
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Save to localStorage on change
  useEffect(() => {
    saveMessages(module, messages);
  }, [messages, module]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── Handle send ──
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming || atLimit) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    // Build placeholder for streaming expert response
    const expertId = crypto.randomUUID();
    const expertMsg: ChatMessage = {
      id: expertId,
      role: "expert",
      content: "",
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, expertMsg]);

    // Build chat_history from existing messages (excluding the ones we just added)
    const chatHistory = messages.map((m) => ({
      role: m.role === "expert" ? "assistant" : "user",
      content: m.content,
    }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(
        `${import.meta.env.VITE_API_URL || ""}/api/chat/${module}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            session_id: crypto.randomUUID(),
            chat_history: chatHistory,
            language,
          }),
          signal: controller.signal,
        },
      );

      if (!resp.ok) {
        throw new Error(`Server error: ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response stream");

      let fullContent = "";

      for await (const raw of readSSE(reader)) {
        try {
          const data = JSON.parse(raw);

          if (data.chunk) {
            fullContent += data.chunk;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === expertId ? { ...m, content: fullContent } : m,
              ),
            );
          }

          if (data.disclaimer) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === expertId ? { ...m, disclaimer: data.disclaimer } : m,
              ),
            );
          }

          if (data.paywall) {
            setPaywalled(true);
          }

          if (data.done) {
            break;
          }

          if (data.error) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === expertId
                  ? {
                      ...m,
                      content: data.message || "Something went wrong. Please try again.",
                      disclaimer: data.disclaimer,
                    }
                  : m,
              ),
            );
            break;
          }
        } catch {
          // Skip unparseable chunks
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === expertId
            ? {
                ...m,
                content: "Connection lost. Please try again.",
              }
            : m,
        ),
      );
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, atLimit, messages, module, language]);

  // ── Handle Enter key ──
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  // ── Start new chat ──
  const handleNewChat = useCallback(() => {
    clearMessages(module);
    setMessages([]);
    setPaywalled(false);
    setInput("");
  }, [module]);

  // ── Don't render if not open ──
  if (!isOpen) return null;

  return (
    <div style={css.overlay} onClick={onClose}>
      {/* Stop click propagation on drawer */}
      <div
        style={{
          ...css.drawer,
          ...(isMobile ? css.drawerMobile : {}),
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={css.header}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={css.headerTitle}>Chat with the Expert</span>
          </div>
          <div style={{ display: "flex", alignItems: "center" }}>
            <button
              style={css.newChatBtn}
              onClick={handleNewChat}
              title="Start a new chat"
            >
              Start New Chat
            </button>
            <button style={css.closeBtn} onClick={onClose} aria-label="Close chat">
              ✕
            </button>
          </div>
        </div>

        {/* Message list */}
        <div style={css.messageList} ref={listRef}>
          {messages.length === 0 && (
            <p style={{ color: "#6B7280", fontSize: 14, textAlign: "center", marginTop: 24 }}>
              Ask a question about{" "}
              {MODULE_LABELS[module] || module}.
            </p>
          )}
          {messages.map((msg) => (
            <div key={msg.id}>
              <div style={css.messageRow(msg.role)}>
                <div style={css.messageBubble(msg.role)}>{msg.content}</div>
              </div>
              {msg.disclaimer && (
                <div style={css.messageRow(msg.role)}>
                  <div style={css.disclaimer}>{msg.disclaimer}</div>
                </div>
              )}
            </div>
          ))}
          {streaming && messages[messages.length - 1]?.content === "" && (
            <div style={css.messageRow("expert")}>
              <div style={css.loadingBubble}>Thinking…</div>
            </div>
          )}
        </div>

        {/* Counter */}
        <div style={css.counter}>
          {userMessageCount} of {MAX_MESSAGES} questions used
        </div>

        {/* Paywall overlay inside drawer */}
        {paywalled && (
          <div style={css.paywallOverlay}>
            <div style={css.paywallTitle}>
              You've used all 5 expert questions.
            </div>
            <div style={css.paywallText}>
              Unlock unlimited questions for $9.99
            </div>
            <button
              style={css.paywallBtn}
              onClick={() => (window.location.href = "/upgrade")}
            >
              Unlock for $9.99
            </button>
            <button style={css.paywallCloseBtn} onClick={onClose}>
              Close
            </button>
          </div>
        )}

        {/* Input area (hidden behind paywall) */}
        {!paywalled && (
          <div style={css.inputArea}>
            <textarea
              style={css.textarea}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask about ${MODULE_LABELS[module] || module}...`}
              disabled={atLimit || streaming}
              rows={1}
            />
            <button
              style={{
                ...css.sendBtn,
                ...(atLimit || streaming || !input.trim()
                  ? css.sendBtnDisabled
                  : {}),
              }}
              onClick={handleSend}
              disabled={atLimit || streaming || !input.trim()}
            >
              {streaming ? "..." : "Send"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
