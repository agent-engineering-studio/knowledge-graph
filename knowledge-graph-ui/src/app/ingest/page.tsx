"use client";

import { useCallback, useRef, useState } from "react";
import { uploadAndIngest, type IngestResult } from "@/lib/api-client";
import { DocumentList } from "@/components/DocumentList";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function IngestPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [threadId, setThreadId] = useState("default");
  const [skipExisting, setSkipExisting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResult(null);
    setError(null);
    setSelectedFile(e.target.files?.[0] ?? null);
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setResult(null);
      setError(null);
      setSelectedFile(file);
    }
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedFile) return;
      setLoading(true);
      setResult(null);
      setError(null);
      try {
        const res = await uploadAndIngest(selectedFile, threadId, skipExisting);
        setResult(res);
        setRefreshTrigger((n) => n + 1);
        setSelectedFile(null);
        if (inputRef.current) inputRef.current.value = "";
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ingestion failed");
      } finally {
        setLoading(false);
      }
    },
    [selectedFile, threadId, skipExisting],
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Document Ingestion</h1>
        <p className="text-gray-600 mt-1 text-sm">
          Upload documents to the knowledge graph. The pipeline extracts text, generates embeddings,
          and builds entity/relation nodes in Neo4j. Supported formats: PDF, DOCX, TXT.
        </p>
      </div>

      {/* Upload form */}
      <section className="bg-white rounded-lg border p-5">
        <h2 className="font-semibold mb-4">Upload a Document</h2>
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              selectedFile
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              className="hidden"
            />
            {selectedFile ? (
              <div className="space-y-1">
                <p className="font-medium text-blue-700">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">{formatBytes(selectedFile.size)}</p>
                <p className="text-xs text-gray-400">Click to change file</p>
              </div>
            ) : (
              <div className="space-y-1 text-gray-400">
                <p className="text-2xl">📄</p>
                <p className="text-sm font-medium">Drop a file here or click to browse</p>
                <p className="text-xs">PDF, DOCX, TXT supported</p>
              </div>
            )}
          </div>

          <div className="flex gap-4 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Namespace / Thread ID</label>
              <input
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                className="border rounded px-2 py-1 text-sm w-40"
              />
            </div>
            <label className="flex items-center gap-2 text-sm select-none cursor-pointer">
              <input
                type="checkbox"
                checked={skipExisting}
                onChange={(e) => setSkipExisting(e.target.checked)}
                className="rounded"
              />
              Skip already-ingested chunks
            </label>
            <button
              type="submit"
              disabled={loading || !selectedFile}
              className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Ingesting…" : "Ingest"}
            </button>
          </div>
        </form>
      </section>

      {/* Progress */}
      {loading && (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-700 flex items-center gap-2">
          <span className="animate-spin inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full" />
          Uploading and processing document… this may take a minute.
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>
      )}

      {/* Result */}
      {result && (
        <section className="bg-white rounded-lg border p-5">
          <h2 className="font-semibold mb-4 text-green-700">Ingestion Complete</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Chunks processed", value: result.chunks_processed },
              { label: "Chunks skipped", value: result.chunks_skipped },
              { label: "Entities extracted", value: result.entities_extracted },
              { label: "Relations extracted", value: result.relations_extracted },
              { label: "Nodes created", value: result.nodes_created },
              { label: "Edges created", value: result.edges_created },
              { label: "Processing time", value: `${result.processing_time_ms.toFixed(0)} ms` },
              { label: "Document ID", value: result.document_id.slice(0, 8) + "…" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-50 rounded p-3 text-center">
                <p className="text-lg font-bold text-gray-800">{value}</p>
                <p className="text-xs text-gray-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
          {result.errors.length > 0 && (
            <div className="mt-4 text-sm text-red-600 space-y-1">
              <p className="font-medium">Warnings / Errors:</p>
              {result.errors.map((e, i) => (
                <p key={i} className="ml-2">• {e}</p>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Document list */}
      <section className="bg-white rounded-lg border p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Documents in namespace "{threadId}"</h2>
          <button
            onClick={() => setRefreshTrigger((n) => n + 1)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Refresh
          </button>
        </div>
        <DocumentList namespace={threadId} refreshTrigger={refreshTrigger} />
      </section>
    </div>
  );
}
