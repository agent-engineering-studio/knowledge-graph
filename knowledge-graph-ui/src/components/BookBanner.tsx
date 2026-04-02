"use client";

import { Box, HStack, Stack, Text, Badge } from "@chakra-ui/react";
import Image from "next/image";

/**
 * BookBanner — Banner promozionale per il libro "Knowledge Graph: dalla Teoria alla Pratica"
 * con badge ufficiale "Available at Amazon" (immagine PNG).
 *
 * TODO: Aggiornare AMAZON_BOOK_URL con l'URL reale della pagina Amazon.
 */

const AMAZON_BOOK_URL = "#"; // TODO: inserire URL Amazon reale

const BOOK_HIGHLIGHTS = [
  "23 capitoli + 4 appendici",
  "190 pagine a colori",
  "Python 3.11+ & C# .NET 9",
  "Neo4j · Redis · Ollama · MCP",
  "Agent Framework multi-agente",
];

export function BookBanner() {
  return (
    <Box
      borderWidth="1px"
      borderRadius="md"
      overflow="hidden"
      bg="linear-gradient(135deg, #0B3D91 0%, #1A5276 50%, #2471A3 100%)"
      color="white"
      position="relative"
    >
      {/* Top accent */}
      <Box h="3px" bg="#ff9900" />

      <Box p={5}>
        <Stack gap={4}>
          {/* Header */}
          <HStack justify="space-between" align="flex-start" flexWrap="wrap" gap={3}>
            <Stack gap={1}>
              <Text fontSize="xl" fontWeight={700} lineHeight={1.2}>
                Knowledge Graph: dalla Teoria alla Pratica
              </Text>
              <Text fontSize="sm" opacity={0.85}>
                Un percorso completo dalla teoria accademica all&apos;implementazione enterprise
                con Python, MCP e Agent Framework
              </Text>
            </Stack>

            {/* Amazon CTA */}
            <a
              href={AMAZON_BOOK_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 20px",
                background: "#ff9900",
                color: "#111",
                borderRadius: "8px",
                textDecoration: "none",
                fontWeight: 700,
                fontSize: "14px",
                whiteSpace: "nowrap",
                transition: "background 0.2s, transform 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#ffad33";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#ff9900";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              Acquista su Amazon
            </a>
          </HStack>

          {/* Highlights */}
          <HStack gap={2} flexWrap="wrap">
            {BOOK_HIGHLIGHTS.map((h) => (
              <Badge
                key={h}
                variant="outline"
                size="sm"
                style={{
                  color: "rgba(255,255,255,0.9)",
                  borderColor: "rgba(255,255,255,0.25)",
                  fontSize: "11px",
                  fontWeight: 500,
                }}
              >
                {h}
              </Badge>
            ))}
          </HStack>

          {/* Official Amazon badge image + trademark */}
          <HStack justify="space-between" align="flex-end" flexWrap="wrap" gap={2}>
            <Box>
              <a
                href={AMAZON_BOOK_URL}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: "none", display: "inline-block", lineHeight: 0 }}
              >
                <Image
                  src="/badges/available_at_amazon_en_horizontal_drk.png"
                  alt="Available at Amazon"
                  width={180}
                  height={46}
                  style={{ height: "36px", width: "auto" }}
                  priority
                />
              </a>
            </Box>
            <Text fontSize="9px" color="whiteAlpha.400">
              Amazon&apos;s trademark is used under license from Amazon.com, Inc. or its affiliates.
            </Text>
          </HStack>
        </Stack>
      </Box>
    </Box>
  );
}
