import React from 'react';
import './StatsPanel.css';

function StatsPanel({ stats }) {
  if (!stats) {
    return <div className="stats-panel">Loading stats...</div>;
  }

  return (
    <div className="stats-panel">
      <h3>System Statistics</h3>
      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-label">Total Documents</div>
          <div className="stat-value">{stats.total_documents}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Vector Store Docs</div>
          <div className="stat-value">{stats.vector_store_documents}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Embedding Model</div>
          <div className="stat-value-small">{stats.embedding_model}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Embedding Dimension</div>
          <div className="stat-value">{stats.embedding_dimension}</div>
        </div>
      </div>
    </div>
  );
}

export default StatsPanel;
