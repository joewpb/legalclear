import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export default function AttorneyReferralPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I'm here to help connect you with a Florida attorney. What's your name?" },
  ]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState("greeting");
  const [userId, setUserId] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading || submitted) return;
    setInput("");
    setLoading(true);

    const updated: Message[] = [...messages, { role: "user", content: text }];
    setMessages(updated);

    try {
      const resp = await fetch("/api/attorney-referral/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation: updated, user_id: userId }),
      });
      if (!resp.ok) throw new Error("Intake failed");
      const data = await resp.json();
      setMessages([...updated, { role: "assistant", content: data.content }]);
      setStage(data.stage);
      if (data.user_id) setUserId(data.user_id);
    } catch {
      setMessages([
        ...updated,
        { role: "assistant", content: "I'm having trouble connecting. Please try again, or call the Florida Bar at 800-342-8011 for immediate help." },
      ]);
    }
    setLoading(false);
  };

  const submit = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const resp = await fetch("/api/attorney-referral/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          conversation: messages,
          intake_summary: `Intake completed at stage: ${stage}`,
        }),
      });
      if (resp.ok) {
        setSubmitted(true);
        setStage("done");
      }
    } catch {
      // ignore
    }
    setLoading(false);
  };

  if (submitted) {
    return (
      <main className="page" style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
        <h1 style={{ fontFamily: "var(--font-serif)", marginBottom: 16 }}>
          Submitted — thank you
        </h1>
        <p style={{ lineHeight: 1.6, marginBottom: 16 }}>
          Your case information has been submitted. An attorney will review it and
          reach out within 1-2 business days. If your situation is urgent (court date
          within 72 hours, eviction, or arrest), call the Florida Bar referral line
          immediately at <strong>800-342-8011</strong>.
        </p>
        <a href="/" style={{ color: "var(--accent)" }}>
          ← Back to LegalClear
        </a>
      </main>
    );
  }

  return (
    <main className="page" style={{ maxWidth: 640, margin: "0 auto", padding: "0 16px" }}>
      <h1 style={{ fontFamily: "var(--font-serif)", fontSize: 22, margin: "16px 0 8px" }}>
        Attorney Referral
      </h1>
      <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 16 }}>
        Answer a few questions and we'll connect you with a Florida attorney.
        Free, confidential, no obligation.
      </p>

      {/* Stage indicator */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {["greeting", "case_type", "details", "contact", "summary"].map((s) => (
          <div
            key={s}
            style={{
              flex: 1,
              height: 3,
              borderRadius: 2,
              background: stage === s || stages.indexOf(stage) > stages.indexOf(s)
                ? "var(--accent)"
                : "var(--border)",
            }}
          />
        ))}
      </div>

      {/* Messages */}
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: 12,
          height: 360,
          overflowY: "auto",
          marginBottom: 8,
          background: "var(--bg)",
        }}
      >
        {messages.filter(m => m.role !== "system").map((m, i) => (
          <div
            key={i}
            style={{
              marginBottom: 10,
              textAlign: m.role === "user" ? "right" : "left",
            }}
          >
            <span
              style={{
                display: "inline-block",
                padding: "8px 12px",
                borderRadius: 12,
                maxWidth: "85%",
                fontSize: 14,
                lineHeight: 1.5,
                background: m.role === "user" ? "var(--accent)" : "var(--bg-muted)",
                color: m.role === "user" ? "#fff" : "var(--fg)",
              }}
            >
              {m.content}
            </span>
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: "left", color: "var(--muted)", fontSize: 12 }}>
            Typing...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type your response..."
          disabled={loading}
          style={{
            flex: 1,
            padding: "10px 12px",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 14,
            background: "var(--bg)",
            color: "var(--fg)",
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            padding: "10px 20px",
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          Send
        </button>
      </div>

      {stage === "summary" && userId && (
        <button
          onClick={submit}
          disabled={loading}
          style={{
            display: "block",
            width: "100%",
            marginTop: 12,
            padding: "12px",
            background: "#166534",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 15,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          Submit for Attorney Review
        </button>
      )}

      <p style={{ color: "var(--muted)", fontSize: 11, marginTop: 12, textAlign: "center" }}>
        Your information is confidential. Submitting does not create an
        attorney-client relationship.
      </p>
    </main>
  );
}

const stages = ["greeting", "case_type", "details", "contact", "summary", "done"];
