/**
 * ChatDrawer.tsx — LegalClear Chat System
 *
 * Modal drawer that slides in over explainer content.
 *   - Mobile: 100% screen width
 *   - Desktop: 50% screen width (from right)
 *   - 5-message limit per session
 *   - localStorage persistence (survives page reload)
 *   - SSE streaming from /api/chat/{module}
 *   - Paywall stub at message 6
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
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function getSessionKey(module: string): string {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return `chat_${module}_${today}`;
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
    background: role === "user" ? "var(--accent, #1E40AF)" : "#F5F7FA",
    color: role === "user" ? "#fff" : "var(--fg, #1A1A1A)",
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
    borderTop: "1px solid #E5E5E0",
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
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    fontSize: 14,
    resize: "none",
    fontFamily: "inherit",
    lineHeight: 1.5,
  } as React.CSSProperties,

  sendBtn: {
    padding: "10px 20px",
    border: "none",
    borderRadius: "var(--radius, 4px)",
    background: "linear-gradient(135deg, #1E40AF, #3B82F6)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    whiteSpace: "nowrap",
  } as React.CSSProperties,

  sendBtnDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  } as React.CSSProperties,

  /* ── Counter ── */
  counter: {
    fontSize: 12,
    color: "var(--muted, #6B6B66)",
    textAlign: "center",
    padding: "4px 0",
  } as React.CSSProperties,

  /* ── Paywall ── */
  paywall: {
    padding: "20px",
    textAlign: "center",
    background: "linear-gradient(135deg, #F5F7FA, #E8EAF6)",
  } as React.CSSProperties,

  paywallTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "var(--accent, #1E40AF)",
    marginBottom: 8,
  } as React.CSSProperties,

  paywallText: {
    fontSize: 14,
    color: "var(--muted, #6B6B66)",
    marginBottom: 12,
  } as React.CSSProperties,

  paywallBtn: {
    padding: "10px 24px",
    border: "none",
    borderRadius: "var(--radius, 4px)",
    background: "linear-gradient(135deg, #635BFF, #7C3AED)",
    color: "#fff",
    fontWeight: 600,
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
    background: "linear-gradient(135deg, #1E40AF, #3B82F6)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(30,64,175,0.3)",
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
      {/* Chat bubble icon ⬡ */}
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

export default function ChatDrawer({ module, onClose }: ChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadMessages(module),
  );
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const MAX_MESSAGES = 5;

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
    return () => abortRef.current?.abort();
  }, []);

  const messageCount = messages.filter((m) => m.role === "user").length;

  const handleSend = useCallback(async () => {
    if (!input.trim() || messageCount >= MAX_MESSAGES || streaming) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: Date.now(),
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const base = import.meta.env.VITE_API_URL || "http://localhost:8001";

    try {
      const res = await fetch(`${base}/api/chat/${module}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.content,
          session_id: crypto.randomUUID(),
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      let accumulated = "";
      const expertMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "expert",
        content: "",
        timestamp: Date.now(),
      };

      // Add placeholder
      const withPlaceholder = [...updatedMessages, expertMsg];
      setMessages(withPlaceholder);

      for await (const chunk of readSSE(reader)) {
        try {
          const parsed = JSON.parse(chunk);
          if (parsed.error) {
            expertMsg.content = parsed.message;
            break;
          }
          if (parsed.disclaimer) {
            expertMsg.disclaimer = parsed.disclaimer;
          }
          if (parsed.chunk) {
            accumulated += parsed.chunk;
            expertMsg.content = accumulated;
            setMessages([...updatedMessages, { ...expertMsg }]);
          }
          if (parsed.done) {
            break;
          }
        } catch {
          // Partial JSON or non-JSON chunk — accumulate raw
          accumulated += chunk;
          expertMsg.content = accumulated;
          setMessages([...updatedMessages, { ...expertMsg }]);
        }
      }

      // Finalize
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last.role === "expert") {
          last.content = accumulated;
          return [...prev];
        }
        return prev;
      });
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "expert",
        content: "Sorry, something went wrong. Please try again.",
        timestamp: Date.now(),
      };
      setMessages([...updatedMessages, errorMsg]);
    } finally {
      setStreaming(false);
    }
  }, [input, messageCount, messages, module, streaming]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const atLimit = messageCount >= MAX_MESSAGES;

  return (
    <div style={css.overlay} onClick={onClose}>
      <div
        style={{
          ...css.drawer,
          ...(window.innerWidth < 768 ? css.drawerMobile : {}),
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={css.header}>
          <span style={css.headerTitle}>
            Chat with the Expert — {MODULE_LABELS[module] || module}
          </span>
          <button style={css.closeBtn} onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Message list */}
        <div style={css.messageList} ref={listRef}>
          {messages.length === 0 && (
            <div style={css.loadingBubble}>
              Ask a question about {MODULE_LABELS[module] || module} to get started.
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id}>
              <div style={css.messageRow(msg.role)}>
                <div style={css.messageBubble(msg.role)}>
                  {msg.content || (msg.role === "expert" && streaming ? "..." : msg.content)}
                </div>
              </div>
              {msg.disclaimer && (
                <div style={css.disclaimer}>{msg.disclaimer}</div>
              )}
            </div>
          ))}

          {/* Streaming indicator — shows when waiting for first chunk */}
          {streaming && messages.length > 0 && messages[messages.length - 1].content === "" && (
            <div style={css.loadingBubble}>Thinking...</div>
          )}
        </div>

        {/* Counter */}
        <div style={css.counter}>
          {atLimit
            ? `${MAX_MESSAGES} of ${MAX_MESSAGES} questions used`
            : `${messageCount} of ${MAX_MESSAGES} questions used`}
        </div>

        {/* Paywall or input */}
        {atLimit ? (
          <div style={css.paywall}>
            <div style={css.paywallTitle}>Upgrade to Continue Chatting</div>
            <div style={css.paywallText}>
              Unlock unlimited questions for $9.99
            </div>
            <button
              style={css.paywallBtn}
              onClick={() => (window.location.href = "/upgrade")}
            >
              <svg width="14" height="14" viewBox="0 0 256 116" style={{ marginRight: 8, verticalAlign: "middle" }}>
                <path fill="#635BFF" d="M0 0h256v116H0z"/>
                <text x="30" y="78" fontFamily="Arial" fontWeight="bold" fontSize="72" fill="#fff">stripe</text>
              </svg>
              Unlock for $9.99
            </button>
          </div>
        ) : (
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
