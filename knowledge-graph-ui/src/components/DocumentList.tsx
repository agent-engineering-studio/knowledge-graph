"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, type DocumentRecord } from "@/lib/api-client";
import { Alert, IconButton, Spinner, Table, Text } from "@chakra-ui/react";

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

  if (loading) return <Spinner size="sm" />;
  if (error) return <Alert.Root status="error"><Alert.Description>{error}</Alert.Description></Alert.Root>;
  if (docs.length === 0) {
    return <Text fontSize="sm" color="gray.500">No documents in namespace &ldquo;{namespace}&rdquo;.</Text>;
  }

  return (
    <Table.Root striped>
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>Name</Table.ColumnHeader>
          <Table.ColumnHeader>Type</Table.ColumnHeader>
          <Table.ColumnHeader>Pages</Table.ColumnHeader>
          <Table.ColumnHeader>Chunks</Table.ColumnHeader>
          <Table.ColumnHeader>Created</Table.ColumnHeader>
          <Table.ColumnHeader />
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {docs.map((doc) => (
          <Table.Row key={doc.base_document_id}>
            <Table.Cell>
              <Text
                fontSize="sm"
                fontWeight={500}
                maxW="220px"
                overflow="hidden"
                textOverflow="ellipsis"
                whiteSpace="nowrap"
                title={doc.name}
              >
                {doc.name}
              </Text>
            </Table.Cell>
            <Table.Cell><Text fontSize="sm" color="gray.500">{doc.mime_type || "—"}</Text></Table.Cell>
            <Table.Cell><Text fontSize="sm" color="gray.500">{doc.total_pages || "—"}</Text></Table.Cell>
            <Table.Cell><Text fontSize="sm" color="gray.500">{doc.chunk_count}</Text></Table.Cell>
            <Table.Cell>
              <Text fontSize="sm" color="gray.500" whiteSpace="nowrap">
                {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "—"}
              </Text>
            </Table.Cell>
            <Table.Cell>
              <IconButton
                aria-label="Delete document"
                colorPalette="red"
                variant="ghost"
                size="sm"
                loading={deleting === doc.base_document_id}
                onClick={() => handleDelete(doc.base_document_id)}
              >
                ✕
              </IconButton>
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}
