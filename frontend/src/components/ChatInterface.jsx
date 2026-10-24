import React, { useEffect, useRef, useState } from "react";
import { qaAPI } from "../services/api";
import "./ChatInterface.css";

const SUGGESTED_QUESTIONS = [
  {
    icon: "✦",
    title: "Summarize my documents",
    question: "Summarize the key points in my selected documents.",
  },
  {
    icon: "⌕",
    title: "Find important details",
    question: "What are the most important details in my documents?",
  },
  {
    icon: "⇄",
    title: "Compare information",
    question: "Compare the main ideas and differences in my documents.",
  },
  {
    icon: "▤",
    title: "Explain a concept",
    question: "Explain the main concepts in my documents in simple terms.",
  },
];

function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Something went wrong. Please try again."
  );
}

function getAnswerText(response) {
  if (typeof response === "string") return response;

  return (
    response?.answer ||
    response?.response ||
    response?.result ||
    response?.message ||
    response?.data?.answer ||
    "No answer was returned. Please try asking another question."
  );
}

function getSources(response) {
  if (!response || typeof response !== "object") return [];

  const sources =
    response.sources ||
    response.source_documents ||
    response.retrieved_documents ||
    response.data?.sources ||
    [];

  return Array.isArray(sources) ? sources : [];
}

function getSourceName(source, index) {
  if (typeof source === "string") return source;

  return (
    source?.filename ||
    source?.file_name ||
    source?.document_name ||
    source?.metadata?.filename ||
    source?.metadata?.source ||
    source?.source ||
    `Source ${index + 1}`
  );
}

function ChatInterface({
  selectedDocuments = [],
  documents = [],
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(false);
  const [error, setError] = useState("");
  const [showSources, setShowSources] = useState(true);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const requestIdRef = useRef(0);

  const selectedIds = selectedDocuments.map(String);

  const selectedFiles = documents.filter((doc) =>
    selectedIds.includes(String(doc.id))
  );

  const sourceDocuments = selectedFiles.length
    ? selectedFiles
    : documents;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      // Prevent an earlier request from updating a discarded component.
      requestIdRef.current += 1;
    };
  }, []);

  const updateMessage = (id, updates) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === id ? { ...message, ...updates } : message
      )
    );
  };

  const handleAsk = async (text = question, useStreaming = streamingEnabled) => {
    const cleanedQuestion = text.trim();

    if (!cleanedQuestion || isLoading) return;

    if (documents.length === 0) {
      setError("Upload a document first, then ask a question.");
      return;
    }

    const requestId = ++requestIdRef.current;
    const userMessageId = `user-${requestId}`;
    const assistantMessageId = `assistant-${requestId}`;

    setError("");
    setQuestion("");
    setIsLoading(true);

    setMessages((current) => [
      ...current,
      {
        id: userMessageId,
        role: "user",
        content: cleanedQuestion,
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        sources: [],
        pending: true,
      },
    ]);

    try {
      const payload = {
        question: cleanedQuestion,
      };

      // Send document IDs only when the user has selected sources.
      if (selectedIds.length > 0) {
        payload.document_ids = selectedIds;
      }

      if (useStreaming && typeof qaAPI.askStream === "function") {
        let accumulatedAnswer = "";
        let streamedSources = [];

        const result = await qaAPI.askStream(
          payload,
          (chunk) => {
            if (requestIdRef.current !== requestId) return;

            if (typeof chunk === "string") {
              accumulatedAnswer += chunk;
            } else if (chunk && typeof chunk === "object") {
              const token =
                chunk.token ||
                chunk.content ||
                chunk.delta ||
                chunk.text ||
                "";

              if (typeof token === "string") {
                accumulatedAnswer += token;
              }

              if (Array.isArray(chunk.sources)) {
                streamedSources = chunk.sources;
              }

              if (chunk.answer && !token) {
                accumulatedAnswer = chunk.answer;
              }
            }

            updateMessage(assistantMessageId, {
              content: accumulatedAnswer,
              sources: streamedSources,
              pending: true,
            });
          }
        );

        if (requestIdRef.current !== requestId) return;

        if (result && typeof result === "object") {
          const finalAnswer = getAnswerText(result);

          if (
            finalAnswer &&
            finalAnswer !==
              "No answer was returned. Please try asking another question."
          ) {
            accumulatedAnswer = finalAnswer;
          }

          streamedSources = getSources(result).length
            ? getSources(result)
            : streamedSources;
        }

        updateMessage(assistantMessageId, {
          content:
            accumulatedAnswer ||
            "The response finished without returning answer text.",
          sources: streamedSources,
          pending: false,
        });
      } else {
        const response = await qaAPI.ask(payload);

        if (requestIdRef.current !== requestId) return;

        updateMessage(assistantMessageId, {
          content: getAnswerText(response),
          sources: getSources(response),
          pending: false,
        });
      }
    } catch (err) {
      if (requestIdRef.current !== requestId) return;

      const message = getErrorMessage(err);

      updateMessage(assistantMessageId, {
        content: "",
        sources: [],
        pending: false,
        failed: true,
      });

      setError(message);
    } finally {
      if (requestIdRef.current === requestId) {
        setIsLoading(false);
        textareaRef.current?.focus();
      }
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    handleAsk();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent?.isComposing) {
      event.preventDefault();
      handleAsk();
    }
  };

  const clearChat = () => {
    if (isLoading) return;
    setMessages([]);
    setError("");
  };

  const copyAnswer = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      setError("Could not copy the answer. Check your browser permissions.");
    }
  };

  const hasConversation = messages.length > 0;

  return (
    <div className="rag-chat">
      <div className="rag-chat-toolbar">
        <div className="rag-chat-status">
          <span className="rag-chat-status-icon">✳</span>
          <div>
            <strong>RAG Assistant</strong>
            <span>
              {selectedIds.length > 0
                ? `${selectedIds.length} selected source${
                    selectedIds.length === 1 ? "" : "s"
                  }`
                : "Using your document library"}
            </span>
          </div>
        </div>

        <div className="rag-chat-actions">
          <label className="rag-stream-toggle" title="Stream the response as it arrives">
            <input
              type="checkbox"
              checked={streamingEnabled}
              onChange={(event) => setStreamingEnabled(event.target.checked)}
              disabled={isLoading}
            />
            <span>Stream</span>
          </label>

          {hasConversation && (
            <button
              type="button"
              className="rag-chat-clear"
              onClick={clearChat}
              disabled={isLoading}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {selectedIds.length > 0 && (
        <div className="rag-chat-selected-sources">
          <span className="rag-chat-source-label">SOURCES</span>
          <div className="rag-chat-source-chips">
            {selectedFiles.map((doc) => (
              <span className="rag-chat-source-chip" key={doc.id}>
                ▤ {doc.filename || doc.name || "Document"}
              </span>
            ))}
          </div>
        </div>
      )}

      <div
        className={`rag-chat-conversation ${
          hasConversation ? "has-messages" : "is-empty"
        }`}
        aria-live="polite"
      >
        {!hasConversation ? (
          <div className="rag-chat-welcome">
            <div className="rag-chat-welcome-icon">✳</div>
            <h3>What would you like to know?</h3>
            <p>
              Ask a question about your documents. The assistant will use your
              indexed content to help find an answer.
            </p>

            <div className="rag-chat-suggestions">
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  type="button"
                  className="rag-chat-suggestion"
                  key={item.title}
                  onClick={() => handleAsk(item.question)}
                  disabled={isLoading || documents.length === 0}
                >
                  <span className="rag-chat-suggestion-icon">{item.icon}</span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.question}</small>
                  </span>
                  <span className="rag-chat-suggestion-arrow">↗</span>
                </button>
              ))}
            </div>

            {documents.length === 0 && (
              <p className="rag-chat-upload-hint">
                Upload a document on the left to get started.
              </p>
            )}
          </div>
        ) : (
          <div className="rag-chat-messages">
            {messages.map((message) => (
              <div
                className={`rag-chat-message ${
                  message.role === "user"
                    ? "rag-chat-user-message"
                    : "rag-chat-assistant-message"
                }`}
                key={message.id}
              >
                <div className="rag-chat-avatar">
                  {message.role === "user" ? "You" : "✳"}
                </div>

                <div className="rag-chat-message-body">
                  <div className="rag-chat-message-meta">
                    <strong>
                      {message.role === "user" ? "You" : "RAG Assistant"}
                    </strong>
                    {message.pending && (
                      <span className="rag-chat-thinking">Generating…</span>
                    )}
                  </div>

                  {message.pending && !message.content ? (
                    <div className="rag-chat-typing">
                      <span />
                      <span />
                      <span />
                    </div>
                  ) : message.failed ? (
                    <p className="rag-chat-failed">
                      The response could not be generated. Please try again.
                    </p>
                  ) : (
                    <div className="rag-chat-answer">
                      {message.content}
                    </div>
                  )}

                  {message.role === "assistant" &&
                    !message.pending &&
                    !message.failed &&
                    message.content && (
                      <div className="rag-chat-message-actions">
                        <button
                          type="button"
                          onClick={() => copyAnswer(message.content)}
                        >
                          Copy answer
                        </button>

                        {message.sources?.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setShowSources((current) => !current)}
                          >
                            {showSources ? "Hide sources" : "Show sources"}
                          </button>
                        )}
                      </div>
                    )}

                  {message.role === "assistant" &&
                    showSources &&
                    message.sources?.length > 0 && (
                      <div className="rag-chat-citations">
                        <strong>Sources used</strong>
                        {message.sources.map((source, index) => (
                          <div
                            className="rag-chat-citation"
                            key={`${getSourceName(source, index)}-${index}`}
                          >
                            <span>▤</span>
                            <span>{getSourceName(source, index)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="rag-chat-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>
            ×
          </button>
        </div>
      )}

      <form className="rag-chat-composer" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents..."
          rows={2}
          disabled={isLoading || documents.length === 0}
          aria-label="Ask a question about your documents"
        />

        <div className="rag-chat-composer-footer">
          <span className="rag-chat-input-hint">
            Enter to send · Shift + Enter for a new line
          </span>

          <button
            type="submit"
            className="rag-chat-send"
            disabled={!question.trim() || isLoading || documents.length === 0}
          >
            {isLoading ? "Thinking…" : "Ask question"}
            {!isLoading && <span>↑</span>}
          </button>
        </div>
      </form>
    </div>
  );
}

export default ChatInterface;