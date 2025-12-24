import { useRef, useState } from "react";
import { uploadDocuments } from "../api/client";
import type { UploadedFile } from "../types/api";

interface Props {
  onComplete: (files: UploadedFile[]) => void;
}

export function FileUploadPanel({ onComplete }: Props) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    setSelectedFiles(Array.from(files));
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) return;
    setUploading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await uploadDocuments(selectedFiles);
      onComplete(response);
      setSelectedFiles([]);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
      setSuccessMessage(`Uploaded ${response.length} file${response.length === 1 ? "" : "s"} to storage.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="panel">
      <h2>Upload Knowledge</h2>
      <p className="muted">PDF, Markdown, or TXT up to 25 docs.</p>
      <div className="upload-controls">
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.md,.txt"
          onChange={handleChange}
        />
        <button className="button" disabled={!selectedFiles.length || isUploading} onClick={handleUpload}>
          {isUploading ? "Uploading..." : "Send to Storage"}
        </button>
      </div>
      {successMessage && <p className="muted success-message">{successMessage}</p>}
      {error && <p className="muted" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
}
