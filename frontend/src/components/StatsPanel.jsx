import React from 'react';
import './StatsPanel.css';

function StatsPanel({ stats }) {
  if (!stats) {
    return (
      <section className="stats-panel">
        <div className="stats-heading">
          <span className="eyebrow">KNOWLEDGE ANALYTICS</span>
          <h3>System insights</h3>
          <p>Your document intelligence, at a glance.</p>
        </div>

        <div className="stats-loading" role="status">
          <span className="stats-loading-spinner" />
          <span>Gathering your system statistics...</span>
        </div>
      </section>
    );
  }

  const totalDocuments = Number(stats.total_documents) || 0;
  const vectorDocuments = Number(stats.vector_store_documents) || 0;
  const embeddingDimension = stats.embedding_dimension ?? '—';
  const embeddingModel = stats.embedding_model || 'Not specified';

  const coverage = totalDocuments > 0
    ? Math.min(100, Math.round((vectorDocuments / totalDocuments) * 100))
    : 0;

  const metrics = [
    {
      id: 'documents',
      label: 'Total documents',
      value: totalDocuments.toLocaleString(),
      description: 'Files in your knowledge base',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M7 3.5h7l5 5v11a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M14 4v5h5M9 13h6M9 16.5h6"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      ),
      className: 'documents'
    },
    {
      id: 'vectors',
      label: 'Vector store documents',
      value: vectorDocuments.toLocaleString(),
      description: 'Documents indexed in the vector store',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <ellipse
            cx="12"
            cy="5"
            rx="7.5"
            ry="3"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M4.5 5v7c0 1.65 3.36 3 7.5 3s7.5-1.35 7.5-3V5M4.5 12v7c0 1.65 3.36 3 7.5 3s7.5-1.35 7.5-3v-7"
            stroke="currentColor"
            strokeWidth="1.6"
          />
        </svg>
      ),
      className: 'vectors'
    },
    {
      id: 'model',
      label: 'Embedding model',
      value: embeddingModel,
      description: 'Model configured for text embeddings',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect
            x="4"
            y="4"
            width="16"
            height="16"
            rx="4"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M9 9h6v6H9zM9 1.5v2.5M15 1.5v2.5M9 20v2.5M15 20v2.5M1.5 9H4M1.5 15H4M20 9h2.5M20 15h2.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      ),
      className: 'model'
    },
    {
      id: 'dimension',
      label: 'Embedding dimensions',
      value: Number.isFinite(Number(embeddingDimension))
        ? Number(embeddingDimension).toLocaleString()
        : String(embeddingDimension),
      description: 'Vector representation size',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 18 10 6l4 8 3-5 3 9H4Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="10" cy="6" r="1.4" fill="currentColor" />
          <circle cx="14" cy="14" r="1.4" fill="currentColor" />
          <circle cx="17" cy="9" r="1.4" fill="currentColor" />
        </svg>
      ),
      className: 'dimension'
    }
  ];

  return (
    <section className="stats-panel">
      <div className="stats-heading">
        <div>
          <span className="eyebrow">KNOWLEDGE ANALYTICS</span>
          <h3>System insights</h3>
          <p>Understand how your document knowledge base is configured.</p>
        </div>

        <div className="stats-live-indicator">
          <span />
          System overview
        </div>
      </div>

      <div className="stats-grid">
        {metrics.map((metric) => (
          <article
            key={metric.id}
            className={`stat-item stat-${metric.className}`}
          >
            <div className="stat-card-top">
              <div className={`stat-icon stat-icon-${metric.className}`}>
                {metric.icon}
              </div>
              <span className="stat-card-mark" aria-hidden="true">↗</span>
            </div>

            <div className="stat-label">{metric.label}</div>

            <div
              className={`stat-value ${
                metric.id === 'model' ? 'stat-value-small' : ''
              }`}
              title={String(metric.value)}
            >
              {metric.value}
            </div>

            <p className="stat-description">{metric.description}</p>
          </article>
        ))}
      </div>

      <div className="stats-index-card">
        <div className="stats-index-top">
          <div>
            <span className="stats-index-kicker">INDEX OVERVIEW</span>
            <h4>Vector store coverage</h4>
            <p>Indexed documents compared with your total document count.</p>
          </div>

          <div className="stats-index-percentage">{coverage}%</div>
        </div>

        <div
          className="stats-progress-track"
          role="progressbar"
          aria-label="Vector store document coverage"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={coverage}
        >
          <div
            className="stats-progress-fill"
            style={{ width: `${coverage}%` }}
          />
        </div>

        <div className="stats-index-footer">
          <span>
            <strong>{vectorDocuments.toLocaleString()}</strong> indexed
          </span>
          <span>
            <strong>{totalDocuments.toLocaleString()}</strong> total documents
          </span>
        </div>
      </div>

      <div className="stats-note">
        <span className="stats-note-icon" aria-hidden="true">✳</span>
        <p>
          <strong>About your setup</strong>
          These figures describe the statistics returned by your backend.
          Vector store coverage is a document-count comparison, not a measure
          of answer accuracy or retrieval quality.
        </p>
      </div>
    </section>
  );
}

export default StatsPanel;