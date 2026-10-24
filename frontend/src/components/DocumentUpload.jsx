import React, { useRef, useState } from "react";
import "./DocumentUpload.css";

const ACCEPTED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".doc",
  ".md",
  ".txt",
  ".markdown",
];

function DocumentUpload({ onUpload }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [fileSize, setFileSize] = useState("");
  const [message, setMessage] = useState(null);

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const uploadFile = async (file) => {
    if (!file || uploading) return;

    const extension = `.${file.name.split(".").pop().toLowerCase()}`;

    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setMessage({
        type: "error",
        text: "Unsupported format. Choose PDF, DOCX, DOC, MD or TXT.",
      });
      return;
    }

    setFileName(file.name);
    setFileSize(formatSize(file.size));
    setMessage(null);
    setUploading(true);

    try {
      const result = await onUpload(file);

      if (result?.success) {
        setMessage({
          type: "success",
          text: "Your document has been added to the knowledge base.",
        });
      } else {
        setMessage({
          type: "error",
          text:
            result?.message ||
            result?.error ||
            "Upload failed. Please try again.",
        });
      }
    } catch (error) {
      setMessage({
        type: "error",
        text:
          error?.response?.data?.detail ||
          error?.message ||
          "Upload failed. Please try again.",
      });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleFileSelect = (event) => {
    uploadFile(event.target.files?.[0]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    uploadFile(event.dataTransfer.files?.[0]);
  };

  return (
    <section className="document-upload">
      <div className="du-heading">
        <div>
          <span className="du-eyebrow">BUILD YOUR KNOWLEDGE BASE</span>
          <h3>Add your documents</h3>
          <p>Give your AI a source to think from.</p>
        </div>

        <div className="du-heading-symbol" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path
              d="M12 16V4m0 0L7 9m5-5 5 5M5 15v4a1 1 0 001 1h12a1 1 0 001-1v-4"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      <div
        className={[
          "du-dropzone",
          dragging ? "is-dragging" : "",
          uploading ? "is-uploading" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!uploading) setDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!uploading) setDragging(true);
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) {
            setDragging(false);
          }
        }}
        onDrop={handleDrop}
        aria-busy={uploading}
      >
        {uploading ? (
          <div className="du-progress-content" role="status">
            <div className="du-spinner" />
            <h4>Adding your document...</h4>
            <p className="du-selected-name">{fileName}</p>
            <div className="du-progress-track">
              <span />
            </div>
            <span className="du-muted">Please wait while the file is processed.</span>
          </div>
        ) : (
          <>
            <div className="du-upload-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" fill="none">
                <path
                  d="M14 5.5h14l9 9V39a3.5 3.5 0 01-3.5 3.5h-19A3.5 3.5 0 0111 39V9a3.5 3.5 0 013-3.5z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
                <path
                  d="M28 6v9h9M24 33V21m-5 5 5-5 5 5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            <h4>{dragging ? "Drop your file here" : "Drop files to get started"}</h4>
            <p className="du-drop-description">
              Drag and drop your document here, or browse your device.
            </p>

            <button
              type="button"
              className="du-browse-button"
              onClick={() => inputRef.current?.click()}
            >
              <span aria-hidden="true">＋</span>
              Browse files
              <span className="du-button-arrow" aria-hidden="true">↗</span>
            </button>

            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              onChange={handleFileSelect}
              className="du-hidden-input"
              aria-label="Choose a document to upload"
              disabled={uploading}
            />

            <div className="du-format-row">
              <span>PDF</span>
              <span>DOCX</span>
              <span>DOC</span>
              <span>MD</span>
              <span>TXT</span>
            </div>
          </>
        )}
      </div>

      <div className="du-privacy-note">
        <span className="du-privacy-icon" aria-hidden="true">✳</span>
        <span>Your files become searchable in your knowledge base.</span>
      </div>

      {fileName && !uploading && (
        <div className="du-file-preview">
          <div className="du-file-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M6 2.75h8l5 5V21H6a2 2 0 01-2-2V4.75a2 2 0 012-2z"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <path
                d="M14 3v5h5M8 13h8M8 16.5h6"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <div className="du-file-info">
            <strong title={fileName}>{fileName}</strong>
            <span>{fileSize}</span>
          </div>

          <span
            className={`du-file-status ${
              message?.type === "success"
                ? "is-success"
                : message?.type === "error"
                  ? "is-error"
                  : ""
            }`}
          >
            {message?.type === "success"
              ? "Added"
              : message?.type === "error"
                ? "Failed"
                : "Selected"}
          </span>
        </div>
      )}

      {message && (
        <div
          className={`du-message ${message.type}`}
          role={message.type === "error" ? "alert" : "status"}
        >
          <span className="du-message-icon" aria-hidden="true">
            {message.type === "success" ? "✓" : "!"}
          </span>
          <span>{message.text}</span>
          <button
            type="button"
            onClick={() => setMessage(null)}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}
    </section>
  );
}

export default DocumentUpload;