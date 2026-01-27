import React, { useState } from 'react';
import './DocumentUpload.css';

function DocumentUpload({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  };

  const uploadFile = async (file) => {
    // Validate file type
    const validExtensions = ['.pdf', '.docx', '.doc', '.md', '.txt', '.markdown'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
      setMessage({ type: 'error', text: 'Unsupported file type. Please upload PDF, DOCX, Markdown, or TXT files.' });
      setTimeout(() => setMessage(null), 5000);
      return;
    }

    setUploading(true);
    setMessage(null);

    try {
      const result = await onUpload(file);
      if (result.success) {
        setMessage({ type: 'success', text: `Document "${file.name}" uploaded successfully!` });
        setTimeout(() => setMessage(null), 3000);
      } else {
        setMessage({ type: 'error', text: result.error || 'Upload failed' });
        setTimeout(() => setMessage(null), 5000);
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error uploading file: ' + error.message });
      setTimeout(() => setMessage(null), 5000);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-upload">
      <h3>Upload Document</h3>
      <div
        className={`upload-area ${dragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {uploading ? (
          <div className="upload-status">
            <div className="spinner"></div>
            <p>Uploading...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">📄</div>
            <p>Drag and drop a file here, or click to select</p>
            <p className="upload-hint">Supports: PDF, DOCX, Markdown, TXT</p>
            <input
              type="file"
              id="file-input"
              onChange={handleFileSelect}
              accept=".pdf,.docx,.doc,.md,.txt,.markdown"
              style={{ display: 'none' }}
            />
            <label htmlFor="file-input" className="upload-button">
              Choose File
            </label>
          </>
        )}
      </div>
      {message && (
        <div className={`upload-message ${message.type}`}>
          {message.text}
        </div>
      )}
    </div>
  );
}

export default DocumentUpload;
