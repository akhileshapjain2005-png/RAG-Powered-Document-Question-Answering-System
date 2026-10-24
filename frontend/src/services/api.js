import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL.replace(/\/+$/, ""),
  timeout: 120000,
  headers: {
    Accept: "application/json",
  },
});

// Attach optional API credentials if configured.
api.interceptors.request.use(
  (config) => {
    const token = import.meta.env.VITE_API_TOKEN;
    const apiKey = import.meta.env.VITE_API_KEY;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (apiKey) {
      config.headers["X-API-Key"] = apiKey;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Normalize API errors for the UI.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED") {
      error.message = "The request timed out. Please try again.";
    } else if (!error.response) {
      error.message =
        "Cannot connect to the backend. Check that FastAPI is running and the API URL is correct.";
    } else {
      const detail =
        error.response.data?.detail ||
        error.response.data?.message;

      if (typeof detail === "string") {
        error.message = detail;
      } else if (Array.isArray(detail)) {
        error.message = detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(", ");
      }
    }

    return Promise.reject(error);
  }
);

// ------------------------------
// DOCUMENT API
// ------------------------------

export const documentAPI = {
  // Upload a PDF, DOCX, TXT, or another supported document.
  async upload(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/documents/upload", formData, {
      timeout: 180000,
    });

    return response.data;
  },

  // Get all uploaded documents.
  async list() {
    const response = await api.get("/documents");
    return response.data;
  },

  // Get a document by ID.
  async get(id) {
    const response = await api.get(
      `/documents/${encodeURIComponent(id)}`
    );
    return response.data;
  },

  // Delete a document by ID.
  async delete(id) {
    const response = await api.delete(
      `/documents/${encodeURIComponent(id)}`
    );
    return response.data;
  },
};

// ------------------------------
// QUESTION ANSWERING API
// ------------------------------

export const qaAPI = {
  // Ask a question using the RAG backend.
  async ask(payload) {
    const response = await api.post("/ask", payload, {
      timeout: 120000,
    });

    return response.data;
  },

  // Stream an answer from a Server-Sent Events endpoint.
  // Expected signature: askStream(payload, onChunk)
  async askStream(payload, onChunk) {
    const baseURL = api.defaults.baseURL;
    const url = `${baseURL}/ask/stream`;

    const headers = {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    };

    const token = import.meta.env.VITE_API_TOKEN;
    const apiKey = import.meta.env.VITE_API_KEY;

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const controller = new AbortController();
    let response;

    try {
      response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
        credentials: "same-origin",
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("The streaming request was cancelled.");
      }
      throw new Error(
        "Could not connect to the streaming endpoint. Check your backend URL."
      );
    }

    if (!response.ok) {
      let message = `Streaming request failed (${response.status}).`;

      try {
        const body = await response.json();
        message = body.detail || body.message || message;
      } catch {
        // Keep the fallback message if the response is not JSON.
      }

      throw new Error(message);
    }

    if (!response.body) {
      throw new Error("The browser does not support response streaming.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;

    const processEvent = (rawEvent) => {
      const lines = rawEvent.split(/\r?\n/);
      const dataLines = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart());

      if (dataLines.length === 0) return;

      const data = dataLines.join("\n");

      if (data === "[DONE]") return;

      let parsed;

      try {
        parsed = JSON.parse(data);
      } catch {
        parsed = data;
      }

      if (
        parsed &&
        typeof parsed === "object" &&
        !Array.isArray(parsed)
      ) {
        finalResult = { ...(finalResult || {}), ...parsed };
      }

      if (typeof onChunk === "function") {
        onChunk(parsed);
      }
    };

    try {
      while (true) {
        const { value, done } = await reader.read();

        buffer += decoder.decode(value || new Uint8Array(), {
          stream: !done,
        });

        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() || "";

        for (const event of events) {
          processEvent(event);
        }

        if (done) break;
      }

      if (buffer.trim()) {
        processEvent(buffer);
      }

      return finalResult;
    } finally {
      reader.releaseLock();
    }
  },
};

// ------------------------------
// STATISTICS API
// ------------------------------

export const statsAPI = {
  async get() {
    const response = await api.get("/stats");
    return response.data;
  },
};

// Default export for components that prefer importing the whole API client.
export default api;