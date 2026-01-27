import React from 'react';
import './DocumentList.css';

function DocumentList({ documents, selectedDocuments, onSelectDocuments, onDelete }) {
  const toggleDocument = (documentId) => {
    if (selectedDocuments.includes(documentId)) {
      onSelectDocuments(selectedDocuments.filter(id => id !== documentId));
    } else {
      onSelectDocuments([...selectedDocuments, documentId]);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (documents.length === 0) {
    return (
      <div className="document-list">
        <h3>Documents</h3>
        <p className="empty-message">No documents uploaded yet.</p>
      </div>
    );
  }

  return (
    <div className="document-list">
      <h3>Documents ({documents.length})</h3>
      <div className="document-items">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`document-item ${selectedDocuments.includes(doc.id) ? 'selected' : ''}`}
          >
            <div className="document-header">
              <input
                type="checkbox"
                checked={selectedDocuments.includes(doc.id)}
                onChange={() => toggleDocument(doc.id)}
                className="document-checkbox"
              />
              <div className="document-info">
                <div className="document-name" title={doc.filename}>
                  {doc.filename}
                </div>
                <div className="document-meta">
                  {doc.chunk_count} chunks • {formatDate(doc.uploaded_at)}
                </div>
              </div>
            </div>
            <button
              className="delete-button"
              onClick={() => onDelete(doc.id)}
              title="Delete document"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>
      {selectedDocuments.length > 0 && (
        <div className="selection-info">
          {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
        </div>
      )}
    </div>
  );
}

export default DocumentList;
