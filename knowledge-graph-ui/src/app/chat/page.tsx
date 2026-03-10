"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  clearConversationHistory,
  getAgentRuns,
  getConversationHistory,
  postAgentRun,
  uploadAndRunAgent,
  type AgentPlanStep,
  type AgentRunRecord,
  type AgentRunResponse,
  type ConversationTurn,
} from "@/lib/api-client";
import {
  Alert,
  Badge,
  Box,
  Button,
  Center,
  HStack,
  IconButton,
  Input,
  Spinner,
  Stack,
  Tabs,
  Text,
  Textarea,
} from "@chakra-ui/react";

interface Message {
  role: "user" | "agent";
  content: string;
  meta?: AgentRunResponse;
}

const ACCEPTED_TYPES = ".pdf,.docx,.txt";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState("default");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AgentRunRecord[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<string>("conversations");
  const [convHistory, setConvHistory] = useState<ConversationTurn[]>([]);
  const [convLoading, setConvLoading] = useState(false);
  const [convClearing, setConvClearing] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadRuns = useCallback(async () => {
    try {
      const runs = await getAgentRuns(20);
      setHistory(runs);
    } catch {
      // history is optional
    }
  }, []);

  const loadConvHistory = useCallback(async (tid: string) => {
    setConvLoading(true);
    try {
      const turns = await getConversationHistory(tid);
      setConvHistory(turns);
    } catch {
      setConvHistory([]);
    } finally {
      setConvLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showHistory && sidebarTab === "conversations") {
      loadConvHistory(threadId);
    }
  }, [showHistory, sidebarTab, threadId, loadConvHistory]);

  useEffect(() => {
    if (showHistory && sidebarTab === "runs") loadRuns();
  }, [showHistory, sidebarTab, loadRuns]);

  const handleClearConv = useCallback(async () => {
    if (!window.confirm("Eliminare la cronologia conversazione per il thread " + JSON.stringify(threadId) + "?")) return;
    setConvClearing(true);
    try {
      await clearConversationHistory(threadId);
      setConvHistory([]);
    } catch {
      // best-effort
    } finally {
      setConvClearing(false);
    }
  }, [threadId]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if ((!text && !attachedFile) || loading) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const fileName = attachedFile?.name ?? "";
    const userContent = attachedFile
      ? "[" + fileName + "]" + (text ? "\n" + text : "")
      : text;

    setInput("");
    setAttachedFile(null);
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: userContent }]);
    setLoading(true);

    try {
      let res: AgentRunResponse;
      if (attachedFile) {
        res = await uploadAndRunAgent(attachedFile, threadId, text || undefined, ctrl.signal);
      } else {
        res = await postAgentRun({ request: text, thread_id: threadId }, ctrl.signal);
      }
      setMessages((prev) => [...prev, { role: "agent", content: res.output, meta: res }]);
      if (showHistory && sidebarTab === "conversations") {
        loadConvHistory(threadId);
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Agent request failed");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [input, attachedFile, threadId, loading, showHistory, sidebarTab, loadConvHistory]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setAttachedFile(f);
    e.target.value = "";
  };

  return (
    <Stack gap={0} style={{ height: "calc(100vh - 80px)" }}>
      <HStack justify="space-between" pb={4}>
        <div>
          <Text fontSize="3xl" fontWeight={700}>Agent Chat</Text>
          <Text color="gray.500" fontSize="sm">Multi-agent orchestration — queries are routed through specialist agents.</Text>
        </div>
        <HStack gap={3}>
          <Box>
            <Box as="label" fontSize="xs" fontWeight={500} mb={1} display="block">Thread ID</Box>
            <Input
              value={threadId}
              onChange={(e) => setThreadId(e.target.value)}
              size="sm"
              w="130px"
            />
          </Box>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowHistory((v) => !v)}
            alignSelf="flex-end"
          >
            {showHistory ? "Nascondi" : "Cronologia"}
          </Button>
        </HStack>
      </HStack>

      <HStack gap={4} align="stretch" style={{ flex: 1, minHeight: 0 }}>
        <Stack gap={3} style={{ flex: 1, minHeight: 0 }}>
          <Box style={{ flex: 1, overflowY: "auto" }}>
            <Box borderWidth="1px" borderRadius="md" p={4} minH="200px">
              {messages.length === 0 && !loading && (
                <Center h="120px">
                  <Text color="gray.500" fontSize="sm">Ask the agent anything, or attach a document (PDF/DOCX/TXT) to ingest it</Text>
                </Center>
              )}
              <Stack gap={3}>
                {messages.map((msg, i) => (
                  <Box key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                    <Stack gap={1} style={{ maxWidth: "75%", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
                      <Box px={3} py={2} borderRadius="md" bg={msg.role === "user" ? "blue.600" : "gray.100"}>
                        <Text fontSize="sm" style={{ whiteSpace: "pre-wrap", color: msg.role === "user" ? "white" : "#2d3748" }}>
                          {msg.content}
                        </Text>
                      </Box>
                      {msg.meta && (
                        <Stack gap={1}>
                          <HStack gap={3}>
                            {msg.meta.intent && (
                              <Text fontSize="xs" color="gray.500">Intent: <Text as="span" color="gray.700">{msg.meta.intent}</Text></Text>
                            )}
                            <Text fontSize="xs" color="gray.500">Time: <Text as="span" color="gray.700">{msg.meta.duration_ms} ms</Text></Text>
                            {msg.meta.plan.length > 0 && (
                              <Text
                                fontSize="xs"
                                color="blue.400"
                                cursor="pointer"
                                onClick={() => setExpandedPlan(expandedPlan === msg.meta!.run_id ? null : msg.meta!.run_id)}
                              >
                                {expandedPlan === msg.meta.run_id ? "Hide" : "Show"} plan ({msg.meta.plan.length} steps)
                              </Text>
                            )}
                          </HStack>
                          {expandedPlan === msg.meta.run_id && msg.meta.plan.length > 0 && (
                            <Box borderWidth="1px" borderRadius="md" p={2}>
                              <Stack gap={1}>
                                {msg.meta.plan.map((step: AgentPlanStep, si: number) => (
                                  <HStack key={si} gap={2} align="flex-start">
                                    <Text fontSize="xs" color="gray.500" w={4}>{si + 1}.</Text>
                                    <Box>
                                      <Text fontSize="xs" fontWeight={500} color="gray.700">{step.action ?? "step"}</Text>
                                      {step.agent && <Text as="span" fontSize="xs" color="gray.500"> ({step.agent})</Text>}
                                      {step.result && <Text fontSize="xs" color="gray.500">{String(step.result).slice(0, 120)}</Text>}
                                    </Box>
                                  </HStack>
                                ))}
                              </Stack>
                            </Box>
                          )}
                          {msg.meta.error && (
                            <Text fontSize="xs" color="red.400">Error: {msg.meta.error}</Text>
                          )}
                        </Stack>
                      )}
                    </Stack>
                  </Box>
                ))}
                {loading && (
                  <Box style={{ display: "flex", justifyContent: "flex-start" }}>
                    <Box px={3} py={2} borderRadius="md" bg="gray.100">
                      <HStack gap={2}>
                        <Spinner size="xs" />
                        <Text fontSize="sm" color="gray.500">{attachedFile ? "Ingesting document" : "Agent is thinking"}</Text>
                      </HStack>
                    </Box>
                  </Box>
                )}
                <div ref={bottomRef} />
              </Stack>
            </Box>
          </Box>

          {error && (
            <Alert.Root status="error">
              <Alert.Description>{error}</Alert.Description>
            </Alert.Root>
          )}

          {attachedFile && (
            <Alert.Root status="info">
              <Alert.Description>
                <HStack justify="space-between">
                  <Text fontSize="sm" style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {attachedFile.name}
                  </Text>
                  <IconButton aria-label="Remove attachment" size="xs" variant="ghost" colorPalette="blue" onClick={() => setAttachedFile(null)}>
                    x
                  </IconButton>
                </HStack>
              </Alert.Description>
            </Alert.Root>
          )}

          <HStack gap={3} align="flex-end">
            <input ref={fileInputRef} type="file" accept={ACCEPTED_TYPES} onChange={handleFileChange} style={{ display: "none" }} />
            <IconButton aria-label="Attach document (PDF, DOCX, TXT)" variant="outline" size="lg" disabled={loading} onClick={() => fileInputRef.current?.click()}>
              📎
            </IconButton>
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder={attachedFile ? "Optional message (Enter to ingest)" : "Ask a question (Enter to send, Shift+Enter for newline)"}
              style={{ flex: 1 }}
            />
            <Stack gap={1}>
              <Button onClick={handleSend} loading={loading} disabled={!input.trim() && !attachedFile} colorPalette="blue">
                {attachedFile ? "Ingest" : "Send"}
              </Button>
              {messages.length > 0 && (
                <Button variant="ghost" colorPalette="gray" size="xs" onClick={() => setMessages([])}>
                  Clear
                </Button>
              )}
            </Stack>
          </HStack>
        </Stack>

        {showHistory && (
          <Box borderWidth="1px" borderRadius="md" w="300px" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
            <Tabs.Root value={sidebarTab} onValueChange={(e) => setSidebarTab(e.value)} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
              <Tabs.List>
                <Tabs.Trigger value="conversations" style={{ flex: 1 }}>Conversazioni</Tabs.Trigger>
                <Tabs.Trigger value="runs" style={{ flex: 1 }}>Run History</Tabs.Trigger>
              </Tabs.List>

              <Tabs.Content value="conversations" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                <HStack justify="space-between" px={3} py={2} borderBottomWidth="1px">
                  <Text fontSize="xs" color="gray.500">
                    Thread: <Text as="span" fontWeight={500} color="gray.800">{threadId}</Text>
                  </Text>
                  <HStack gap={1}>
                    <IconButton aria-label="Refresh" size="xs" variant="ghost" loading={convLoading} onClick={() => loadConvHistory(threadId)}>
                      ↻
                    </IconButton>
                    {convHistory.length > 0 && (
                      <Button size="xs" variant="ghost" colorPalette="red" loading={convClearing} onClick={handleClearConv}>
                        Cancella
                      </Button>
                    )}
                  </HStack>
                </HStack>
                <Box style={{ flex: 1, overflowY: "auto" }} p={2}>
                  {convLoading ? (
                    <Center py={6}><Spinner size="sm" /></Center>
                  ) : convHistory.length === 0 ? (
                    <Center py={6}>
                      <Stack align="center" gap={1}>
                        <Text fontSize="xl">💬</Text>
                        <Text fontSize="xs" color="gray.500">Nessuna conversazione salvata</Text>
                        <Text fontSize="xs" color="gray.500">per il thread &ldquo;{threadId}&rdquo;</Text>
                      </Stack>
                    </Center>
                  ) : (
                    <Stack gap={2}>
                      {convHistory.map((turn, i) => (
                        <Box key={i} style={{ display: "flex", justifyContent: turn.role === "user" ? "flex-end" : "flex-start" }}>
                          <Box px={2} py={1} borderRadius="md" maxW="85%" bg={turn.role === "user" ? "blue.50" : "gray.50"} borderWidth="1px" borderColor={turn.role === "user" ? "blue.100" : "gray.200"}>
                            <Text fontSize="xs" fontWeight={600} color={turn.role === "user" ? "blue.400" : "gray.500"} mb={1}>
                              {turn.role === "user" ? "Tu" : "Agente"}
                            </Text>
                            <Text fontSize="xs" style={{ whiteSpace: "pre-wrap" }}>
                              {turn.content}
                            </Text>
                          </Box>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Box>
              </Tabs.Content>

              <Tabs.Content value="runs" style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
                <Box p={3}>
                  <HStack justify="space-between" mb={3}>
                    <Text fontSize="xs" fontWeight={600} color="gray.700">Esecuzioni recenti</Text>
                    <IconButton aria-label="Refresh" size="xs" variant="ghost" onClick={loadRuns}>↻</IconButton>
                  </HStack>
                  {history.length === 0 ? (
                    <Text fontSize="xs" color="gray.500">Nessun run ancora.</Text>
                  ) : (
                    <Stack gap={2}>
                      {history.map((run) => (
                        <Box key={run.run_id} borderWidth="1px" borderRadius="md" p={2}>
                          <HStack justify="space-between" mb={1}>
                            <Badge size="xs" colorPalette={run.status === "success" ? "green" : "red"} variant="subtle">{run.status}</Badge>
                            <Text fontSize="xs" color="gray.500">{run.duration_ms} ms</Text>
                          </HStack>
                          <Text fontSize="xs" color="gray.700" overflow="hidden" textOverflow="ellipsis" whiteSpace="nowrap" title={run.input_summary}>{run.input_summary}</Text>
                          <HStack gap={2} mt={1}>
                            <Text fontSize="xs" color="gray.500">Intent: {run.intent}</Text>
                            {run.tool_calls.length > 0 && (
                              <Text fontSize="xs" color="gray.500" title={run.tool_calls.join(", ")}>
                                - {run.tool_calls.length} tool{run.tool_calls.length !== 1 ? "s" : ""}
                              </Text>
                            )}
                          </HStack>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Box>
              </Tabs.Content>
            </Tabs.Root>
          </Box>
        )}
      </HStack>
    </Stack>
  );
}
