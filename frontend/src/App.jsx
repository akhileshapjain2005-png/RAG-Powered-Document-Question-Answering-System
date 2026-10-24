
import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API = "/api";

const authHeaders = () => {
  const key = import.meta.env.VITE_API_KEY;
  return key ? { "X-API-Key": key } : {};
};

const sameId = (a, b) => String(a) === String(b);

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState([]);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dark, setDark] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const fileRef = useRef(null);
  const chatEndRef = useRef(null);

  const loadDocuments = useCallback(async () => {
    try {
      const response = await fetch(`${API}/documents`, {
        headers: authHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Could not load documents (${response.status}).`);
      }

      const result = await response.json();
      const list = Array.isArray(result)
        ? result
        : result.documents || result.items || [];

      setDocuments(list);

      const validIds = new Set(list.map((doc) => String(doc.id)));
      setSelected((current) =>
        current.filter((id) => validIds.has(String(id)))
      );
    } catch (err) {
      setError(
        err.message ||
          "Cannot connect to the backend. Check that FastAPI is running."
      );
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const filteredDocuments = documents.filter((doc) =>
    (doc.filename || doc.name || "")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const isSelected = (id) =>
    selected.some((selectedId) => sameId(selectedId, id));

  // Clear the conversation only. Do not delete documents or change selection.
  function clearChat() {
    setMessages([]);
    setQuestion("");
    setError("");
  }

  function toggleDocument(id) {
    setSelected((current) =>
      current.some((item) => sameId(item, id))
        ? current.filter((item) => !sameId(item, id))
        : [...current, id]
    );

    clearChat();
  }

  function selectAllDocuments() {
    const allSelected =
      documents.length > 0 &&
      documents.every((doc) => isSelected(doc.id));

    setSelected(allSelected ? [] : documents.map((doc) => doc.id));
    clearChat();
  }

  async function uploadFiles(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setUploading(true);
    setError("");

    const newlyUploadedIds = [];

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API}/documents/upload`, {
          method: "POST",
          headers: authHeaders(),
          body: formData,
        });

        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            result.detail || `Failed to upload ${file.name}.`
          );
        }

        if (result.id !== undefined && result.id !== null) {
          newlyUploadedIds.push(result.id);
        }
      }

      await loadDocuments();

      // Select only the newly uploaded documents.
      setSelected(newlyUploadedIds);
      clearChat();

      if (newlyUploadedIds.length === 0) {
        setError(
          "Upload completed, but the server did not return document IDs. Select the document from your library."
        );
      }
    } catch (err) {
      setError(err.message || "Document upload failed.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function deleteDocument(doc) {
    const filename = doc.filename || doc.name || "this document";

    if (!window.confirm(`Delete "${filename}"?`)) return;

    setError("");

    try {
      const response = await fetch(
        `${API}/documents/${encodeURIComponent(doc.id)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Could not delete the document.");
      }

      setDocuments((current) =>
        current.filter((item) => !sameId(item.id, doc.id))
      );

      setSelected((current) =>
        current.filter((id) => !sameId(id, doc.id))
      );

      clearChat();
    } catch (err) {
      setError(err.message || "Could not delete the document.");
    }
  }

  async function askQuestion(text = question) {
    const prompt = text.trim();

    if (!prompt || loading) return;

    if (selected.length === 0) {
      setError(
        "Please select at least one document before asking a question."
      );
      return;
    }

    // Send only the IDs selected by the user.
    const selectedIds = [...selected];

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: prompt,
      },
    ]);

    setQuestion("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({
          question: prompt,
          document_ids: selectedIds,
          top_k: 5,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Question answering failed.");
      }

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.answer || "No answer was returned.",
          sources: result.sources || [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Could not get an answer.");
    } finally {
      setLoading(false);
    }
  }

  const suggestions = [
    {
      icon: "✦",
      title: "Summarize documents",
      subtitle: "Get the key points from your files",
      prompt: "Summarize the key points in my selected documents.",
    },
    {
      icon: "⌕",
      title: "Find important details",
      subtitle: "Locate facts and essential information",
      prompt: "What are the most important details in my selected documents?",
    },
    {
      icon: "⇄",
      title: "Compare information",
      subtitle: "Discover similarities and differences",
      prompt: "Compare the main ideas and differences in my selected documents.",
    },
    {
      icon: "▤",
      title: "Explain a concept",
      subtitle: "Understand difficult topics simply",
      prompt: "Explain the main concepts in my selected documents in simple terms.",
    },
  ];

  return (
    <div className={`app-shell ${dark ? "theme-dark" : "theme-light"}`}>
      <aside className="sidebar">
        <a className="brand" href="#workspace">
          <span className="brand-icon">R</span>
          <span className="brand-copy">
            <strong>RAG-DocQA</strong>
            <small>DOCUMENT INTELLIGENCE</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className="nav-item active"
          onClick={() =>
            document.getElementById("documents-panel")?.scrollIntoView({
              behavior: "smooth",
              block: "center",
            })
          }
        >
          <span>▤</span> Document workspace
        </button>

        <div className="sidebar-label library-label">
          YOUR LIBRARY
          <span>{documents.length}</span>
        </div>

        <div className="sidebar-documents">
          {documents.slice(0, 10).map((doc) => (
            <button
              className={`sidebar-document ${
                isSelected(doc.id) ? "selected" : ""
              }`}
              key={String(doc.id)}
              onClick={() => toggleDocument(doc.id)}
              title={doc.filename || doc.name}
              aria-pressed={isSelected(doc.id)}
            >
              <span className="mini-file">FILE</span>
              <span className="sidebar-document-name">
                {doc.filename || doc.name || "Untitled document"}
              </span>
            </button>
          ))}

          {!documents.length && (
            <p className="empty-small">
              Your documents will appear here.
            </p>
          )}

          {documents.length > 10 && (
            <button
              className="nav-item"
              onClick={() =>
                document.getElementById("documents-panel")?.scrollIntoView({
                  behavior: "smooth",
                  block: "center",
                })
              }
            >
              View all {documents.length} documents
            </button>
          )}
        </div>

        <div className="sidebar-footer">
          <span className="status-dot" />
          <span>
            <strong>Local AI engine</strong>
            <small>Private workspace</small>
          </span>
          <span className="live-tag">LIVE</span>
        </div>
      </aside>

      <main className="main-area" id="workspace">
        <header className="topbar">
          <div className="breadcrumbs">
            Workspace <span>/</span>{" "}
            <strong>Document intelligence</strong>
          </div>

          <div className="topbar-actions">
            <span className="connection">
              <i /> Assistant ready
            </span>

            <button
              className="secondary-button"
              onClick={() => setDark((value) => !value)}
            >
              {dark ? "☼ Light mode" : "☾ Dark mode"}
            </button>

            <button
              className="primary-button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "+ Add documents"}
            </button>
          </div>

          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.docx"
            multiple
            hidden
            onChange={uploadFiles}
          />
        </header>

        <section className="welcome-section">
          <div className="welcome-copy">
            <div className="eyebrow">
              <span className="sparkle">✳</span>
              YOUR KNOWLEDGE, REIMAGINED
            </div>

            <h1>
              Think deeper.
              <br />
              <span>Find your answers.</span>
            </h1>

            <p>
              Explore your documents with AI that understands your knowledge
              and helps you uncover what matters.
            </p>
          </div>

          <div className="welcome-art" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="art-core">
              <span>R</span>
            </div>
            <div className="art-chip chip-one">AI</div>
            <div className="art-chip chip-two">⌘</div>
            <div className="art-chip chip-three">✧</div>
          </div>
        </section>

        {error && (
          <div className="error-banner">
            <span>!</span>
            <p>{error}</p>
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}

        <section className="workspace-grid">
          <aside className="panel documents-panel" id="documents-panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">KNOWLEDGE BASE</div>
                <h2>My Documents</h2>
                <p>Upload, select and manage your files.</p>
              </div>
              <span className="document-count">
                {String(documents.length).padStart(2, "0")}
              </span>
            </div>

            <button
              className="upload-zone"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
            >
              <span className="upload-icon">
                {uploading ? "…" : "↑"}
              </span>
              <span className="upload-copy">
                <strong>
                  {uploading ? "Uploading documents..." : "Upload documents"}
                </strong>
                <small>Click to browse PDF, TXT or DOCX files</small>
              </span>
              <span className="upload-plus">+</span>
            </button>

            <div className="document-stats">
              <div>
                <span className="stats-icon">▤</span>
                <span>
                  <strong>{documents.length}</strong>
                  <small>Documents</small>
                </span>
              </div>
              <div>
                <span className="stats-icon">✓</span>
                <span>
                  <strong>{selected.length}</strong>
                  <small>Selected</small>
                </span>
              </div>
            </div>

            <div className="document-toolbar">
              <label className="search-box">
                <span>⌕</span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search documents..."
                  aria-label="Search documents"
                />
              </label>

              <button
                className="text-button"
                onClick={selectAllDocuments}
                disabled={!documents.length}
              >
                {documents.length > 0 &&
                documents.every((doc) => isSelected(doc.id))
                  ? "Clear"
                  : "Select all"}
              </button>
            </div>

            <div className="document-list">
              {filteredDocuments.map((doc) => {
                const filename =
                  doc.filename || doc.name || "Untitled document";
                const extension = filename.split(".").pop().toLowerCase();
                const fileType =
                  extension === "pdf"
                    ? "PDF"
                    : extension === "docx"
                      ? "DOC"
                      : "TXT";
                const active = isSelected(doc.id);

                return (
                  <article
                    key={String(doc.id)}
                    className={`document-card ${
                      active ? "document-selected" : ""
                    }`}
                  >
                    <button
                      type="button"
                      className="document-main"
                      onClick={() => toggleDocument(doc.id)}
                      title={active ? "Deselect document" : "Select document"}
                      aria-pressed={active}
                    >
                      <span className="file-icon">
                        <span>{fileType}</span>
                      </span>
                      <span className="document-info">
                        <strong>{filename}</strong>
                        <small>
                          {doc.uploaded_at
                            ? new Date(doc.uploaded_at).toLocaleDateString()
                            : "In your library"}
                          {doc.chunk_count != null
                            ? ` · ${doc.chunk_count} chunks`
                            : ""}
                        </small>
                      </span>
                    </button>

                    <div className="document-actions">
                      <span
                        className={`selection-indicator ${
                          active ? "is-selected" : ""
                        }`}
                      >
                        {active ? "✓" : "+"}
                      </span>
                      <button
                        type="button"
                        className="delete-button"
                        onClick={() => deleteDocument(doc)}
                        title={`Delete ${filename}`}
                        aria-label={`Delete ${filename}`}
                      >
                        ×
                      </button>
                    </div>
                  </article>
                );
              })}

              {filteredDocuments.length === 0 && (
                <div className="empty-state">
                  <span className="empty-icon">▤</span>
                  <strong>
                    {documents.length
                      ? "No matching documents"
                      : "Your library is empty"}
                  </strong>
                  <p>
                    {documents.length
                      ? "Try another search term."
                      : "Upload a PDF, TXT, or DOCX file to start asking questions."}
                  </p>
                  {!documents.length && (
                    <button
                      className="primary-button"
                      onClick={() => fileRef.current?.click()}
                      disabled={uploading}
                    >
                      + Add your first document
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="library-footer">
              <span className="status-dot" />
              Documents indexed in your knowledge base
            </div>
          </aside>

          <section className="panel chat-panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">AI ASSISTANT</div>
                <h2>What would you like to know?</h2>
                <p>
                  {selected.length
                    ? `Answers focused on ${selected.length} selected document(s).`
                    : "Select a document from your library to get started."}
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <button
                  type="button"
                  className="secondary-button"
                  onClick={clearChat}
                  disabled={messages.length === 0 && !question && !error}
                  title="Clear questions and answers without deleting documents"
                >
                  Clear Chat
                </button>
                <span className="assistant-avatar">✳</span>
              </div>
            </div>

            {messages.length === 0 ? (
              <div className="suggestion-grid">
                {suggestions.map((item) => (
                  <button
                    className="suggestion-card"
                    key={item.title}
                    onClick={() => askQuestion(item.prompt)}
                    disabled={loading}
                  >
                    <span className="suggestion-icon">{item.icon}</span>
                    <span className="suggestion-copy">
                      <strong>{item.title}</strong>
                      <small>{item.subtitle}</small>
                    </span>
                    <span className="suggestion-arrow">↗</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="chat-history">
                {messages.map((message) => (
                  <article
                    className={`message ${
                      message.role === "user" ? "user-message" : ""
                    }`}
                    key={message.id}
                  >
                    <div className="message-avatar">
                      {message.role === "user" ? "U" : "R"}
                    </div>
                    <div className="message-body">
                      <div className="message-author">
                        {message.role === "user" ? "You" : "RAG-DocQA"}
                      </div>
                      <div className="message-text">{message.content}</div>

                      {!!message.sources?.length && (
                        <div className="source-list">
                          <div className="source-heading">SOURCES USED</div>
                          {message.sources.map((source, index) => (
                            <div
                              className="source-item"
                              key={`${source.document_id || source.filename || "source"}-${index}`}
                            >
                              <span className="mini-file">FILE</span>
                              <span>
                                {source.filename || "Document source"}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </article>
                ))}

                {loading && (
                  <div className="thinking">
                    <span className="assistant-avatar">R</span>
                    <span>Searching your selected documents...</span>
                    <span className="thinking-dots">•••</span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}

            <form
              className="composer"
              onSubmit={(event) => {
                event.preventDefault();
                askQuestion();
              }}
            >
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  selected.length
                    ? `Ask about ${selected.length} selected document(s)...`
                    : "Select a document first, then ask a question..."
                }
                rows={3}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    askQuestion();
                  }
                }}
              />

              <div className="composer-footer">
                <span>
                  <kbd>Enter</kbd> to ask · <kbd>Shift + Enter</kbd> for a
                  new line
                </span>
                <button
                  className="primary-button ask-button"
                  type="submit"
                  disabled={loading || !question.trim()}
                >
                  {loading ? "Thinking..." : "Ask question"}
                  {!loading && <span>↗</span>}
                </button>
              </div>
            </form>
          </section>
        </section>

        <footer className="app-footer">
          <span>
            RAG-DocQA <span className="footer-dot">·</span> DOCUMENT
            INTELLIGENCE
          </span>
          <span>Powered by your indexed knowledge</span>
        </footer>
      </main>
    </div>
  );
}
