import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';
import { qaAPI } from '../services/api';

function ChatInterface({ selectedDocuments, documents }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [currentStream, setCurrentStream] = useState('');
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStream]);

  const handleSend = async (useStream = false) => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    if (useStream) {
      setStreaming(true);
      setCurrentStream('');

      try {
        let fullAnswer = '';
        await qaAPI.askStream(
          input,
          selectedDocuments.length > 0 ? selectedDocuments : null,
          5,
          (chunk) => {
            fullAnswer += chunk;
            setCurrentStream(fullAnswer);
          }
        );

        const assistantMessage = {
          role: 'assistant',
          content: fullAnswer,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setCurrentStream('');
      } catch (error) {
        console.error('Error streaming answer:', error);
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error while generating the answer.',
          error: true,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setStreaming(false);
        setLoading(false);
      }
    } else {
      try {
        const response = await qaAPI.ask(
          input,
          selectedDocuments.length > 0 ? selectedDocuments : null,
          5
        );

        const assistantMessage = {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Error getting answer:', error);
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error while generating the answer.',
          error: true,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getDocumentName = (documentId) => {
    const doc = documents.find((d) => d.id === documentId);
    return doc ? doc.filename : 'Unknown';
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>💬 Chat with Documents</h2>
        {selectedDocuments.length > 0 ? (
          <div className="selected-docs-info">
            Searching in {selectedDocuments.length} selected document{selectedDocuments.length !== 1 ? 's' : ''}
          </div>
        ) : (
          <div className="selected-docs-info">
            Searching in all documents
          </div>
        )}
      </div>

      <div className="chat-messages" ref={chatContainerRef}>
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>👋 Welcome!</h3>
            <p>Ask questions about your uploaded documents.</p>
            <p className="hint">Try asking: "What is this document about?" or "Summarize the main points"</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-content">
              {message.role === 'user' ? (
                <div className="user-message">
                  <strong>You:</strong> {message.content}
                </div>
              ) : (
                <div className={`assistant-message ${message.error ? 'error' : ''}`}>
                  <strong>Assistant:</strong>
                  <div className="answer-text">{message.content}</div>
                  {message.sources && message.sources.length > 0 && (
                    <div className="sources">
                      <strong>Sources:</strong>
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="source-item">
                          📄 {getDocumentName(source.document_id)} ({source.chunks.length} chunks)
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {streaming && currentStream && (
          <div className="message assistant">
            <div className="message-content">
              <div className="assistant-message">
                <strong>Assistant:</strong>
                <div className="answer-text streaming">{currentStream}</div>
                <div className="streaming-indicator">●</div>
              </div>
            </div>
          </div>
        )}

        {loading && !streaming && (
          <div className="message assistant">
            <div className="message-content">
              <div className="assistant-message">
                <div className="loading-indicator">
                  <div className="spinner-small"></div>
                  <span>Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question about your documents..."
          rows="2"
          disabled={loading}
        />
        <div className="chat-actions">
          <button
            className="send-button"
            onClick={() => handleSend(false)}
            disabled={loading || !input.trim()}
          >
            {loading ? '⏳' : '📤'} Send
          </button>
          <button
            className="send-button stream"
            onClick={() => handleSend(true)}
            disabled={loading || !input.trim()}
            title="Stream response"
          >
            {streaming ? '⏳' : '🌊'} Stream
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
