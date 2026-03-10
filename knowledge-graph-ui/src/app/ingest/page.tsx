"use client";

import { useCallback, useRef, useState } from "react";
import { uploadAndIngest, type IngestResult } from "@/lib/api-client";
import { DocumentList } from "@/components/DocumentList";
import { useDropzone } from "react-dropzone";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  HStack,
  IconButton,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  Input,
} from "@chakra-ui/react";

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

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) {
      setResult(null);
      setError(null);
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    disabled: loading,
  });

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
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ingestion failed");
      } finally {
        setLoading(false);
      }
    },
    [selectedFile, threadId, skipExisting],
  );

  return (
    <Stack gap={6}>
      <div>
        <Text fontSize="3xl" fontWeight={700}>Document Ingestion</Text>
        <Text color="gray.500" fontSize="sm" mt={1}>
          Upload documents to the knowledge graph. The pipeline extracts text, generates embeddings,
          and builds entity/relation nodes in Neo4j. Supported formats: PDF, DOCX, TXT.
        </Text>
      </div>

      {/* Upload form */}
      <Box borderWidth="1px" borderRadius="md" p={4}>
        <Text fontWeight={600} mb={4}>Upload a Document</Text>
        <form onSubmit={handleSubmit}>
          <Stack gap={4}>
            <Box
              {...getRootProps()}
              borderWidth={2}
              borderStyle="dashed"
              borderColor={isDragActive ? "blue.400" : "gray.200"}
              borderRadius="md"
              p={6}
              textAlign="center"
              cursor={loading ? "not-allowed" : "pointer"}
              bg={isDragActive ? "blue.50" : "transparent"}
              _hover={{ borderColor: loading ? "gray.200" : "blue.300" }}
            >
              <input {...getInputProps()} />
              <Stack align="center" gap={2}>
                {selectedFile ? (
                  <>
                    <Text fontWeight={500} color="blue.700">{selectedFile.name}</Text>
                    <Text fontSize="xs" color="gray.500">{formatBytes(selectedFile.size)}</Text>
                    <Text fontSize="xs" color="gray.500">Click to change file</Text>
                  </>
                ) : (
                  <>
                    <Text fontSize="2xl">📄</Text>
                    <Text fontSize="sm" fontWeight={500}>Drop a file here or click to browse</Text>
                    <Text fontSize="xs" color="gray.500">PDF, DOCX, TXT supported</Text>
                  </>
                )}
              </Stack>
            </Box>

            <HStack align="flex-end" gap={3}>
              <Box>
                <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Namespace / Thread ID</Box>
                <Input
                  value={threadId}
                  onChange={(e) => setThreadId(e.target.value)}
                  w="160px"
                />
              </Box>
              <Checkbox.Root
                checked={skipExisting}
                onCheckedChange={(e) => setSkipExisting(!!e.checked)}
                alignSelf="center"
                mt={2}
              >
                <Checkbox.HiddenInput />
                <Checkbox.Control />
                <Checkbox.Label fontSize="sm">Skip already-ingested chunks</Checkbox.Label>
              </Checkbox.Root>
              <Button
                type="submit"
                loading={loading}
                disabled={!selectedFile}
                alignSelf="flex-end"
                colorPalette="blue"
              >
                Ingest
              </Button>
            </HStack>
          </Stack>
        </form>
      </Box>

      {loading && (
        <Alert.Root status="info">
          <Alert.Description>
            <HStack gap={2}>
              <Spinner size="sm" />
              <Text fontSize="sm">Uploading and processing document… this may take a minute.</Text>
            </HStack>
          </Alert.Description>
        </Alert.Root>
      )}

      {error && (
        <Alert.Root status="error">
          <Alert.Description>{error}</Alert.Description>
        </Alert.Root>
      )}

      {result && (
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <Text fontWeight={600} color="green.700" mb={4}>Ingestion Complete</Text>
          <SimpleGrid columns={{ base: 2, sm: 4 }} gap={3}>
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
              <Box key={label} borderWidth="1px" borderRadius="md" p={3} textAlign="center">
                <Text fontSize="lg" fontWeight={700}>{value}</Text>
                <Text fontSize="xs" color="gray.500" mt={1}>{label}</Text>
              </Box>
            ))}
          </SimpleGrid>
          {result.errors.length > 0 && (
            <Alert.Root status="warning" mt={4}>
              <Alert.Description>
                <Stack gap={1}>
                  {result.errors.map((e, i) => (
                    <Text key={i} fontSize="sm">• {e}</Text>
                  ))}
                </Stack>
              </Alert.Description>
            </Alert.Root>
          )}
        </Box>
      )}

      {/* Document list */}
      <Box borderWidth="1px" borderRadius="md" p={4}>
        <HStack justify="space-between" mb={4}>
          <Text fontWeight={600}>Documents in namespace &ldquo;{threadId}&rdquo;</Text>
          <IconButton
            aria-label="Refresh"
            variant="ghost"
            size="sm"
            onClick={() => setRefreshTrigger((n) => n + 1)}
          >
            ↻
          </IconButton>
        </HStack>
        <DocumentList namespace={threadId} refreshTrigger={refreshTrigger} />
      </Box>
    </Stack>
  );
}
