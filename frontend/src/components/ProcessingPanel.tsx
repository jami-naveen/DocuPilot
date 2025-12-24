import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listRecentFiles, startProcessing } from "../api/client";
import type { FileRecord, ProcessStatus } from "../types/api";
import { useProcessingPoll } from "../hooks/useProcessingPoll";
import { ProgressMeter } from "./ProgressMeter";

export function ProcessingPanel() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [statusSnapshot, setStatusSnapshot] = useState<ProcessStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: files, refetch } = useQuery<FileRecord[]>({
    queryKey: ["files"],
    queryFn: () => listRecentFiles(10),
    refetchInterval: 5000
  });
  const { status } = useProcessingPoll(jobId);
  const isBusy = (status ?? statusSnapshot)?.state === "running";

  const runProcessing = async () => {
    try {
      setError(null);
      const response = await startProcessing();
      setJobId(response.job_id);
      setStatusSnapshot(response);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start processing");
    }
  };

  const processedStatus = status ?? statusSnapshot;

  return (
    <div className="panel">
      <h2>Process Documents</h2>
      <p className="muted">Chunk, embed, and index everything recently uploaded.</p>
      <button className="button secondary" onClick={runProcessing} disabled={isBusy}>
        {isBusy ? "Processing..." : "Launch Processing Run"}
      </button>
      <div style={{ marginTop: "1rem" }}>
        <ProgressMeter status={processedStatus} />
      </div>
      {error && (
        <p className="muted" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      <div style={{ marginTop: "1.5rem" }}>
        <h3>Recent uploads</h3>
        {files && files.length > 0 ? (
          <div style={{ maxHeight: "220px", overflowY: "auto" }}>
            {files.map((file) => (
              <div key={file.name} className="progress-row">
                <span>{file.name}</span>
                <span>{(file.size_bytes / 1024).toFixed(1)} KB</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No files yet.</p>
        )}
      </div>
    </div>
  );
}
