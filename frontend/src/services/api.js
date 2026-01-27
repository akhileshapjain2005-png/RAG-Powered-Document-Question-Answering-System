import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const documentAPI = {
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async () => {
    const response = await api.get('/documents');
    return response.data;
  },

  get: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  delete: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },
};

export const qaAPI = {
  ask: async (question, documentIds = null, topK = 5) => {
    const response = await api.post('/ask', {
      question,
      document_ids: documentIds,
      top_k: topK,
    });
    return response.data;
  },

  askStream: async (question, documentIds = null, topK = 5, onChunk) => {
    const response = await fetch(`${API_BASE_URL}/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        top_k: topK,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data && onChunk) {
            onChunk(data);
          }
        }
      }
    }
  },
};

export const statsAPI = {
  get: async () => {
    const response = await api.get('/stats');
    return response.data;
  },
};

export default api;
