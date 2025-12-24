import { useState } from "react";
import { askQuestion } from "../api/client";
import type { ChatResponse } from "../types/api";

export function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [isLoading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const payload = {
        question,
        history: conversation,
        top_k: 5
      };
      const answer = await askQuestion(payload);
      setConversation((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: answer.answer }]);
      setResponse(answer);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>Ask the AI Analyst</h2>
      <div className="chat-window">
        {conversation
          .filter((msg) => msg.role === "user")
          .map((msg, index) => (
            <div key={index} className="chat-bubble user">
              <strong>You</strong>
              <p>{msg.content}</p>
            </div>
          ))}
        {response && (
          <div className="chat-bubble bot">
            <div className="answer-header">
              <strong>Answer</strong>
              <small className="muted">
                Latency {(response.latency_ms / 1000).toFixed(2)}s · Confidence {(response.confidence * 100).toFixed(0)}%
              </small>
            </div>
            <p>{response.answer}</p>
            <details className="reference-panel">
              <summary>References & supporting snippets ({response.citations.length})</summary>
              <div className="citations">
                {response.citations.map((c) => (
                  <span key={c.chunk_id} className="citation-chip">
                    {c.source_document} · {c.score.toFixed(2)}
                  </span>
                ))}
              </div>
              {response.citations.map((c) => (
                <div key={`snippet-${c.chunk_id}`} className="citation-card">
                  <strong>{c.source_document}</strong>
                  <p>{c.snippet}</p>
                </div>
              ))}
            </details>
          </div>
        )}
      </div>
      <textarea
        placeholder="Ask about the indexed knowledge..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={3}
        style={{ width: "100%", marginTop: "1rem", background: "rgba(255,255,255,0.05)", borderRadius: "14px", border: "1px solid rgba(255,255,255,0.08)", color: "var(--text)", padding: "0.8rem" }}
      />
      <button className="button" onClick={submit} disabled={isLoading}>
        {isLoading ? "Thinking..." : "Ask"}
      </button>
      {error && <p className="muted" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
}
