import { useState } from "react";
import type { UploadedFile } from "./types/api";
import { FileUploadPanel } from "./components/FileUploadPanel";
import { ProcessingPanel } from "./components/ProcessingPanel";
import { ChatPanel } from "./components/ChatPanel";

export default function App() {
  const [justUploaded, setJustUploaded] = useState<UploadedFile[]>([]);

  return (
    <div className="app-shell">
      <header className="header">
        <p className="muted">Azure Container Apps · Semantic + Hybrid RAG</p>
        <h1>Document Q&A</h1>
        {justUploaded.length > 0 && (
          <small className="muted">
            Uploaded {justUploaded.length} file(s) • Ready for processing
          </small>
        )}
      </header>
      <section className="panels">
        <FileUploadPanel onComplete={setJustUploaded} />
        <ProcessingPanel />
      </section>
      <ChatPanel />
    </div>
  );
}
