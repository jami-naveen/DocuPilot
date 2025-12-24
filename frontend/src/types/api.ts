export type UploadedFile = {
  blob_name: string;
  original_name: string;
  size_bytes: number;
  container: string;
};

export type FileRecord = {
  name: string;
  size_bytes: number;
  uploaded_at: string;
  container: string;
  status: string;
};

export type ProcessStep = {
  step: string;
  current: number;
  total: number;
};

export type ProcessStatus = {
  job_id: string;
  state: "queued" | "running" | "completed" | "failed";
  steps: ProcessStep[];
  errors: string[];
};

export type ChatRequest = {
  question: string;
  history: { role: string; content: string }[];
  top_k: number;
};

export type Citation = {
  chunk_id: string;
  source_document: string;
  score: number;
  snippet: string;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  latency_ms: number;
  confidence: number;
};
