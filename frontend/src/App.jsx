import React, { useState, useEffect } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import DocumentList from './components/DocumentList';
import ChatInterface from './components/ChatInterface';
import StatsPanel from './components/StatsPanel';
import { documentAPI, statsAPI } from './services/api';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    try {
      const docs = await documentAPI.list();
      setDocuments(docs);
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await statsAPI.get();
      setStats(statsData);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleDocumentUpload = async (file) => {
    try {
      const newDoc = await documentAPI.upload(file);
      setDocuments([...documents, newDoc]);
      await loadStats();
      return { success: true };
    } catch (error) {
      console.error('Error uploading document:', error);
      return { success: false, error: error.message };
    }
  };

  const handleDocumentDelete = async (documentId) => {
    try {
      await documentAPI.delete(documentId);
      setDocuments(documents.filter(doc => doc.id !== documentId));
      setSelectedDocuments(selectedDocuments.filter(id => id !== documentId));
      await loadStats();
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>📚 RAG-DocQA</h1>
        <p>AI-Powered Document Question Answering System</p>
        <p className="subtitle">Ask questions about your documents using RAG (Retrieval-Augmented Generation)</p>
      </header>

      <div className="app-container">
        <div className="sidebar">
          <div className="tab-buttons">
            <button
              className={activeTab === 'chat' ? 'active' : ''}
              onClick={() => setActiveTab('chat')}
            >
              💬 Chat
            </button>
            <button
              className={activeTab === 'documents' ? 'active' : ''}
              onClick={() => setActiveTab('documents')}
            >
              📄 Documents
            </button>
            <button
              className={activeTab === 'stats' ? 'active' : ''}
              onClick={() => setActiveTab('stats')}
            >
              📊 Stats
            </button>
          </div>

          {activeTab === 'documents' && (
            <div className="sidebar-content">
              <DocumentUpload onUpload={handleDocumentUpload} />
              <DocumentList
                documents={documents}
                selectedDocuments={selectedDocuments}
                onSelectDocuments={setSelectedDocuments}
                onDelete={handleDocumentDelete}
              />
            </div>
          )}

          {activeTab === 'stats' && stats && (
            <div className="sidebar-content">
              <StatsPanel stats={stats} />
            </div>
          )}
        </div>

        <div className="main-content">
          {activeTab === 'chat' && (
            <ChatInterface
              selectedDocuments={selectedDocuments}
              documents={documents}
            />
          )}
          {activeTab === 'documents' && (
            <div className="documents-view">
              <h2>Document Management</h2>
              <p>Upload and manage your documents from the sidebar.</p>
            </div>
          )}
          {activeTab === 'stats' && (
            <div className="stats-view">
              <h2>System Statistics</h2>
              <p>View system statistics in the sidebar.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
