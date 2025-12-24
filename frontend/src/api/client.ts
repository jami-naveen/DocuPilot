import type {
  ChatRequest,
  ChatResponse,
  FileRecord,
  ProcessStatus,
  UploadedFile
} from "../types/api";

const jsonHeaders = {
  "Content-Type": "application/json"
};

export async function uploadDocuments(files: File[]): Promise<UploadedFile[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const res = await fetch("/api/files/upload", {
    method: "POST",
    body: formData
  });
  if (!res.ok) {
    throw new Error("Upload failed");
  }
  return res.json();
}

export async function listRecentFiles(limit = 10): Promise<FileRecord[]> {
  const res = await fetch(`/api/files/recent?limit=${limit}`);
  if (!res.ok) {
    throw new Error("Unable to load files");
  }
  return res.json();
}

export async function startProcessing(limit?: number): Promise<ProcessStatus> {
  const res = await fetch("/api/processing/start", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ limit })
  });
  if (!res.ok) {
    throw new Error("Processing could not start");
  }
  return res.json();
}

export async function getProcessingStatus(jobId: string): Promise<ProcessStatus> {
  const res = await fetch(`/api/processing/${jobId}`);
  if (!res.ok) {
    throw new Error("Job not found");
  }
  return res.json();
}

export async function askQuestion(payload: ChatRequest): Promise<ChatResponse> {
  const res = await fetch("/api/chat/completions", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error("Chat request failed");
  }
  return res.json();
}
