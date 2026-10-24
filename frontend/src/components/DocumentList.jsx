import React from 'react';
import './DocumentList.css';

function DocumentList({
  documents = [],
  selectedDocuments = [],
  onSelectDocuments,
  onDelete
}) {
  const toggleDocument = (documentId) => {
    const isSelected = selectedDocuments.some(
      id => String(id) === String(documentId)
    );

    if (isSelected) {
      onSelectDocuments(
        selectedDocuments.filter(id => String(id) !== String(documentId))
      );
    } else {
      onSelectDocuments([...selectedDocuments, documentId]);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Date unavailable';

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) return 'Date unavailable';

    return date.toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === undefined || bytes === null || Number.isNaN(Number(bytes))) {
      return null;
    }

    const size = Number(bytes);

    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileType = (filename = '') => {
    const extension = filename.split('.').pop()?.toLowerCase();

    const types = {
      pdf: { label: 'PDF', className: 'pdf' },
      doc: { label: 'DOC', className: 'doc' },
      docx: { label: 'DOCX', className: 'doc' },
      txt: { label: 'TXT', className: 'text' },
      md: { label: 'MD', className: 'text' },
      markdown: { label: 'MD', className: 'text' }
    };

    return types[extension] || { label: 'FILE', className: 'other' };
  };

  const allSelected =
    documents.length > 0 &&
    documents.every(doc =>
      selectedDocuments.some(id => String(id) === String(doc.id))
    );

  const toggleAll = () => {
    if (allSelected) {
      const documentIds = new Set(documents.map(doc => String(doc.id)));

      onSelectDocuments(
        selectedDocuments.filter(id => !documentIds.has(String(id)))
      );
    } else {
      const selectedIds = new Set(selectedDocuments.map(String));
      const merged = [...selectedDocuments];

      documents.forEach(doc => {
        if (!selectedIds.has(String(doc.id))) {
          merged.push(doc.id);
        }
      });

      onSelectDocuments(merged);
    }
  };

  if (documents.length === 0) {
    return (
      <section className="document-list">
        <div className="document-list-heading">
          <div>
            <span className="eyebrow">YOUR KNOWLEDGE BASE</span>
            <h3>Your documents</h3>
            <p className="document-list-subtitle">
              Your uploaded files will appear here.
            </p>
          </div>

          <div className="document-heading-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M7 3.75h7l5 5v11.5H7a2 2 0 0 1-2-2v-12a2.5 2.5 0 0 1 2-2.5Z"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <path
                d="M14 4v5h5M9 13h6M9 16.5h6"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>

        <div className="document-empty-state">
          <div className="document-empty-icon" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none">
              <rect
                x="8"
                y="5"
                width="25"
                height="32"
                rx="4"
                stroke="currentColor"
                strokeWidth="1.8"
              />
              <path
                d="M15 15h11M15 21h11M15 27h6"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <path
                d="M33 29v13m-6.5-6.5H39.5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <h4>A little quiet in here.</h4>
          <p>
            Upload your first document to build your knowledge base.
            You can then select files and ask questions about their contents.
          </p>

          <div className="document-empty-tip">
            <span aria-hidden="true">✳</span>
            <span>PDF, DOCX, Markdown and text files are supported.</span>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="document-list">
      <div className="document-list-heading">
        <div>
          <span className="eyebrow">YOUR KNOWLEDGE BASE</span>
          <h3>Your documents</h3>
          <p className="document-list-subtitle">
            Manage your files and choose what the AI should reference.
          </p>
        </div>

        <div className="document-count-badge">
          <span>{documents.length}</span>
          <span>{documents.length === 1 ? 'FILE' : 'FILES'}</span>
        </div>
      </div>

      <div className="document-toolbar">
        <label className="document-select-all">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            aria-label="Select all documents"
          />
          <span>{allSelected ? 'Deselect all' : 'Select all'}</span>
        </label>

        <span className="document-toolbar-hint">
          {selectedDocuments.length > 0
            ? `${selectedDocuments.length} selected for AI`
            : 'Select files to focus your answers'}
        </span>
      </div>

      <div className="document-items">
        {documents.map((doc) => {
          const isSelected = selectedDocuments.some(
            id => String(id) === String(doc.id)
          );

          const fileType = getFileType(doc.filename);
          const fileSize = formatFileSize(doc.file_size ?? doc.size);

          return (
            <article
              key={doc.id}
              className={`document-item ${isSelected ? 'selected' : ''}`}
            >
              <label className="document-select-control">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleDocument(doc.id)}
                  className="document-checkbox"
                  aria-label={`Select ${doc.filename || 'document'}`}
                />
              </label>

              <div
                className={`document-file-icon ${fileType.className}`}
                aria-hidden="true"
              >
                <svg viewBox="0 0 32 36" fill="none">
                  <path
                    d="M5 2.75h13l9 9v21a1.5 1.5 0 0 1-1.5 1.5h-19A1.5 1.5 0 0 1 5 32.75v-28.5A1.5 1.5 0 0 1 6.5 2.75Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M18 3v9h9"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M10 20h12M10 24h12M10 28h8"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>

                <span>{fileType.label}</span>
              </div>

              <div className="document-info">
                <div
                  className="document-name"
                  title={doc.filename || 'Untitled document'}
                >
                  {doc.filename || 'Untitled document'}
                </div>

                <div className="document-meta">
                  <span>{formatDate(doc.uploaded_at)}</span>
                  <span className="document-meta-separator">·</span>
                  <span>
                    {doc.chunk_count ?? 0}{' '}
                    {(doc.chunk_count ?? 0) === 1 ? 'chunk' : 'chunks'}
                  </span>

                  {fileSize && (
                    <>
                      <span className="document-meta-separator">·</span>
                      <span>{fileSize}</span>
                    </>
                  )}
                </div>
              </div>

              <div className="document-item-actions">
                <span
                  className={`document-status ${isSelected ? 'active' : ''}`}
                  title={isSelected ? 'Included in AI context' : 'Not specifically selected'}
                >
                  <span className="document-status-dot" />
                  {isSelected ? 'Selected' : 'Available'}
                </span>

                <button
                  type="button"
                  className="delete-button"
                  onClick={() => onDelete(doc.id)}
                  title={`Delete ${doc.filename || 'document'}`}
                  aria-label={`Delete ${doc.filename || 'document'}`}
                >
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M4 7h16M9 7V4.5h6V7m3 0-.8 12H6.8L6 7m4 4v4m4-4v4"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {selectedDocuments.length > 0 && (
        <div className="selection-info">
          <span className="selection-info-icon" aria-hidden="true">✓</span>
          <span>
            <strong>{selectedDocuments.length}</strong>{' '}
            {selectedDocuments.length === 1 ? 'document' : 'documents'} selected
            for focused answers.
          </span>

          <button
            type="button"
            onClick={() => onSelectDocuments([])}
            className="clear-selection-button"
          >
            Clear selection
          </button>
        </div>
      )}
    </section>
  );
}

export default DocumentList;