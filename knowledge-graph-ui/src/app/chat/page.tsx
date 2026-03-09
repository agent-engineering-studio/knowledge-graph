"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getAgentRuns,
  postAgentRun,
  type AgentPlanStep,
  type AgentRunRecord,
  type AgentRunResponse,
} from "@/lib/api-client";

interface Message {
  role: "user" | "agent";
  content: string;
  meta?: AgentRunResponse;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState("default");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AgentRunRecord[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadHistory = useCallback(async () => {
    try {
      const runs = await getAgentRuns(20);
      setHistory(runs);
    } catch {
      // history is optional
    }
  }, []);

  useEffect(() => {
    if (showHistory) loadHistory();
  }, [showHistory, loadHistory]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await postAgentRun({ request: text, thread_id: threadId }, ctrl.signal);
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: res.output, meta: res },
      ]);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Agent request failed");
      setMessages((prev) => prev.slice(0, -1)); // remove user bubble on error
    } finally {
      setLoading(false);
    }
  }, [input, threadId, loading]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] space-y-0">
      {/* Header */}
      <div className="flex items-center justify-between pb-4">
        <div>
          <h1 className="text-2xl font-bold">Agent Chat</h1>
          <p className="text-gray-600 text-sm mt-0.5">
            Multi-agent orchestration — queries are routed through specialist agents.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Thread ID</label>
            <input
              value={threadId}
              onChange={(e) => setThreadId(e.target.value)}
              className="border rounded px-2 py-1 text-sm w-32"
            />
          </div>
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="text-xs text-gray-500 hover:text-gray-800 border rounded px-3 py-1.5"
          >
            {showHistory ? "Hide history" : "Run history"}
          </button>
        </div>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Chat area */}
        <div className="flex flex-col flex-1 min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto bg-white rounded-lg border p-4 space-y-4">
            {messages.length === 0 && !loading && (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                Ask the agent anything about the knowledge graph…
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[75%] space-y-2 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                  <div
                    className={`rounded-lg px-4 py-2.5 text-sm whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {/* Agent metadata */}
                  {msg.meta && (
                    <div className="text-xs text-gray-400 space-y-1 w-full">
                      <div className="flex gap-3 flex-wrap">
                        {msg.meta.intent && <span>Intent: <span className="text-gray-600">{msg.meta.intent}</span></span>}
                        <span>Time: <span className="text-gray-600">{msg.meta.duration_ms} ms</span></span>
                        {msg.meta.plan.length > 0 && (
                          <button
                            onClick={() => setExpandedPlan(expandedPlan === msg.meta!.run_id ? null : msg.meta!.run_id)}
                            className="text-blue-500 hover:underline"
                          >
                            {expandedPlan === msg.meta.run_id ? "Hide" : "Show"} plan ({msg.meta.plan.length} steps)
                          </button>
                        )}
                      </div>

                      {expandedPlan === msg.meta.run_id && msg.meta.plan.length > 0 && (
                        <div className="bg-gray-50 rounded p-2 space-y-1 border">
                          {msg.meta.plan.map((step: AgentPlanStep, si: number) => (
                            <div key={si} className="flex gap-2">
                              <span className="text-gray-400 w-4 shrink-0">{si + 1}.</span>
                              <div>
                                <span className="font-medium text-gray-600">{step.action ?? "step"}</span>
                                {step.agent && <span className="ml-2 text-gray-400">({step.agent})</span>}
                                {step.result && <p className="text-gray-500 mt-0.5">{String(step.result).slice(0, 120)}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {msg.meta.error && (
                        <p className="text-red-500">Error: {msg.meta.error}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-2.5 text-sm text-gray-400 animate-pulse">
                  Agent is thinking…
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Error */}
          {error && (
            <div className="mt-2 bg-red-50 border border-red-200 text-red-700 rounded p-2 text-sm">
              {error}
            </div>
          )}

          {/* Input */}
          <div className="mt-3 flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
              className="flex-1 border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <div className="flex flex-col gap-1">
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "…" : "Send"}
              </button>
              {messages.length > 0 && (
                <button
                  onClick={() => setMessages([])}
                  className="text-xs text-gray-400 hover:text-gray-600 px-2"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Run history sidebar */}
        {showHistory && (
          <div className="w-72 shrink-0 bg-white rounded-lg border p-4 overflow-y-auto">
            <h3 className="font-semibold text-sm mb-3">Recent Runs</h3>
            {history.length === 0 ? (
              <p className="text-xs text-gray-400">No runs yet.</p>
            ) : (
              <ul className="space-y-2">
                {history.map((run) => (
                  <li key={run.run_id} className="text-xs border rounded p-2 space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span
                        className={`font-medium ${run.status === "success" ? "text-green-600" : "text-red-500"}`}
                      >
                        {run.status}
                      </span>
                      <span className="text-gray-400">{run.duration_ms} ms</span>
                    </div>
                    <p className="text-gray-600 truncate" title={run.input_summary}>{run.input_summary}</p>
                    <p className="text-gray-400">Intent: {run.intent}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
