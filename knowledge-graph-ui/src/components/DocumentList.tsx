"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, type DocumentRecord } from "@/lib/api-client";

interface Props {
  namespace: string;
  refreshTrigger?: number;
}

export function DocumentList({ namespace, refreshTrigger }: Props) {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    if (!namespace.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments(namespace);
      setDocs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [namespace]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs, refreshTrigger]);

  const handleDelete = useCallback(async (baseDocumentId: string) => {
    setDeleting(baseDocumentId);
    try {
      await deleteDocument(baseDocumentId);
      setDocs((prev) => prev.filter((d) => d.base_document_id !== baseDocumentId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  }, []);

  if (loading) return <p className="text-sm text-gray-500">Loading documents…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (docs.length === 0)
    return <p className="text-sm text-gray-400">No documents in namespace "{namespace}".</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-3 py-2 border-b">Name</th>
            <th className="px-3 py-2 border-b">Type</th>
            <th className="px-3 py-2 border-b">Pages</th>
            <th className="px-3 py-2 border-b">Chunks</th>
            <th className="px-3 py-2 border-b">Created</th>
            <th className="px-3 py-2 border-b" />
          </tr>
        </thead>
        <tbody>
          {docs.map((doc) => (
            <tr key={doc.base_document_id} className="hover:bg-gray-50 border-b last:border-0">
              <td className="px-3 py-2 font-medium truncate max-w-55" title={doc.name}>
                {doc.name}
              </td>
              <td className="px-3 py-2 text-gray-500">{doc.mime_type || "—"}</td>
              <td className="px-3 py-2 text-gray-500">{doc.total_pages || "—"}</td>
              <td className="px-3 py-2 text-gray-500">{doc.chunk_count}</td>
              <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "—"}
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  onClick={() => handleDelete(doc.base_document_id)}
                  disabled={deleting === doc.base_document_id}
                  className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
                >
                  {deleting === doc.base_document_id ? "Deleting…" : "Delete"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
