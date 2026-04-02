"use client";

import { Badge, Box, HStack, Stack, Text } from "@chakra-ui/react";

/**
 * BookBanner — Banner promozionale per il libro "Knowledge Graph: dalla Teoria alla Pratica"
 * con badge "Disponibile su Amazon" conforme alle linee guida KDP.
 *
 * TODO: Aggiornare AMAZON_BOOK_URL con l'URL reale della pagina Amazon.
 */

const AMAZON_BOOK_URL = "#"; // TODO: inserire URL Amazon reale

const BOOK_HIGHLIGHTS = [
  "23 capitoli + 4 appendici",
  "189 pagine a colori",
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
              <HStack gap={2}>
                <Badge
                  colorPalette="orange"
                  variant="solid"
                  size="sm"
                  style={{ fontWeight: 700, letterSpacing: "0.05em" }}
                >
                  NUOVO — 2ª Edizione
                </Badge>
              </HStack>
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
              {/* Amazon arrow logo */}
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M13.958 10.09c0 1.232.029 2.256-.591 3.351-.502.891-1.301 1.438-2.186 1.438-1.214 0-1.922-.924-1.922-2.292 0-2.692 2.415-3.182 4.7-3.182v.685zm3.186 7.705a.66.66 0 01-.753.077c-1.06-.878-1.25-1.287-1.828-2.126-1.748 1.783-2.987 2.316-5.252 2.316-2.68 0-4.764-1.655-4.764-4.97 0-2.587 1.402-4.347 3.398-5.208 1.73-.758 4.147-.893 5.993-1.101v-.412c0-.756.059-1.649-.387-2.304-.387-.579-1.128-.82-1.784-.82-1.213 0-2.293.622-2.557 1.913-.054.284-.263.564-.55.578l-3.083-.332c-.26-.058-.548-.264-.474-.657C5.873 1.665 9.16.5 12.12.5c1.516 0 3.496.403 4.688 1.55 1.516 1.438 1.372 3.355 1.372 5.443v4.93c0 1.482.615 2.132 1.193 2.933.203.286.248.629-.013.84-.651.544-1.811 1.557-2.449 2.123l.233-.024z" fill="#111"/>
                <path d="M21.73 17.693c-1.59 1.175-3.893 1.8-5.877 1.8-2.781 0-5.287-1.028-7.183-2.74-.149-.134-.016-.317.163-.213 2.047 1.191 4.577 1.908 7.19 1.908 1.763 0 3.702-.365 5.485-1.123.269-.115.494.177.222.368z" fill="#f90"/>
                <path d="M22.407 16.881c-.203-.26-1.344-.123-1.856-.062-.156.018-.18-.117-.039-.215.908-.639 2.398-.454 2.572-.24.174.216-.046 1.706-.898 2.418-.131.11-.256.051-.198-.093.192-.48.623-1.548.419-1.808z" fill="#f90"/>
              </svg>
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

          {/* Available at Amazon badge + trademark */}
          <HStack justify="space-between" align="flex-end" flexWrap="wrap" gap={2}>
            <Box>
              <a
                href={AMAZON_BOOK_URL}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: "none" }}
              >
                <Box
                  display="inline-flex"
                  flexDirection="column"
                  alignItems="center"
                  gap="2px"
                  bg="#232f3e"
                  px={4}
                  py={2}
                  borderRadius="6px"
                >
                  <Text fontSize="9px" color="white" opacity={0.7} textTransform="lowercase" letterSpacing="0.05em">
                    disponibile su
                  </Text>
                  <svg width="70" height="21" viewBox="0 0 603 182" fill="white" xmlns="http://www.w3.org/2000/svg">
                    <path d="M374.01 142.02c-34.55 25.49-84.67 39.06-127.8 39.06-60.47 0-114.93-22.37-156.14-59.56-3.24-2.93-.34-6.91 3.54-4.64 44.47 25.86 99.39 41.44 156.17 41.44 38.29 0 80.41-7.93 119.15-24.39 5.84-2.48 10.73 3.84 5.08 8.09z" fill="#f90"/>
                    <path d="M388.56 125.55c-4.41-5.65-29.22-2.67-40.36-1.35-3.39.41-3.91-2.54-.85-4.66 19.76-13.9 52.16-9.89 55.95-5.23 3.79 4.68-.99 37.07-19.54 52.54-2.85 2.38-5.57 1.11-4.3-2.05 4.17-10.43 13.51-33.61 9.1-39.25z" fill="#f90"/>
                    <path d="M349.14 23.31V7.21c0-2.45 1.85-4.08 4.08-4.08h72.15c2.32 0 4.17 1.67 4.17 4.08v13.78c-.04 2.32-1.97 5.36-5.44 10.2l-37.39 53.36c13.9-.34 28.57 1.72 41.14 8.84 2.84 1.59 3.62 3.96 3.83 6.28v17.17c0 2.36-2.6 5.11-5.32 3.69-22.23-11.65-51.76-12.92-76.33.13-2.5 1.35-5.15-1.37-5.15-3.73v-16.31c0-2.63.04-7.13 2.63-11.13l43.3-62.12h-37.69c-2.32 0-4.17-1.63-4.17-4.04zM124.82 108.66h-21.95c-2.1-.15-3.77-1.76-3.91-3.77V7.42c0-2.28 1.89-4.08 4.26-4.08h20.46c2.14.09 3.85 1.76 3.99 3.83v13.44h.41c5.36-13.27 15.38-19.45 28.89-19.45 13.69 0 22.24 6.18 28.39 19.45 5.32-13.27 17.42-19.45 30.39-19.45 9.22 0 19.3 3.79 25.48 12.31 7.01 9.46 5.57 23.23 5.57 35.29l-.04 58.04c0 2.28-1.89 4.13-4.21 4.13h-21.91c-2.18-.15-3.91-1.93-3.91-4.13V55.59c0-4.74.41-16.56-.62-21.04-1.63-7.55-6.52-9.68-12.84-9.68-5.28 0-10.82 3.54-13.07 9.22-2.24 5.69-2.02 15.17-2.02 21.5v49.3c0 2.28-1.89 4.13-4.21 4.13h-21.91c-2.19-.15-3.91-1.93-3.91-4.13l-.04-49.3c0-12.52 2.06-30.93-13.44-30.93-15.72 0-15.09 17.95-15.09 30.93v49.3c0 2.28-1.89 4.13-4.21 4.13zM458.44 1.16c33.13 0 51.04 28.43 51.04 64.56 0 34.92-19.79 62.61-51.04 62.61-32.47 0-50.14-28.43-50.14-63.81 0-35.54 17.87-63.36 50.14-63.36zm.19 23.39c-16.42 0-17.42 22.37-17.42 36.31s-.21 43.82 17.23 43.82c17.21 0 18.04-24.08 18.04-38.77 0-9.68-.41-21.25-3.34-30.47-2.49-8.01-7.45-10.89-14.51-10.89zM552.38 108.66h-21.87c-2.19-.15-3.91-1.93-3.91-4.13l-.04-97.16c.19-2.1 2.01-3.73 4.26-3.73h20.34c1.93.09 3.51 1.42 3.91 3.22v14.86h.41c6.14-13.65 14.77-20.12 29.93-20.12 9.89 0 19.54 3.58 25.72 13.44 5.74 9.14 5.74 24.52 5.74 35.54v54.38c-.26 2.01-2.06 3.62-4.26 3.62h-22.03c-2.01-.15-3.66-1.67-3.85-3.62V54c0-12.31 1.42-30.31-13.65-30.31-5.32 0-10.2 3.54-12.64 8.97-3.08 6.87-3.49 13.69-3.49 21.33v50.54c-.04 2.28-1.93 4.13-4.26 4.13zM30.68 60.72c0 8.53.22 15.63-4.08 23.23-3.49 6.14-9.05 9.93-15.17 9.93-8.42 0-13.36-6.41-13.36-15.89 0-18.7 16.76-22.09 32.61-22.09v4.82zm22.11 53.47c-1.46 1.3-3.56 1.38-5.19.52-7.3-6.06-8.6-8.88-12.59-14.65-12.03 12.27-20.55 15.93-36.14 15.93C-16.38 116-28 106.1-28 87.27c0-14.69 7.97-24.68 19.3-29.55 9.81-4.3 23.52-5.07 34.01-6.24V48.6c0-5.07.38-11.07-2.6-15.46-2.6-3.94-7.55-5.57-11.95-5.57-8.12 0-15.34 4.17-17.12 12.8-.36 1.93-1.76 3.81-3.69 3.91l-21.29-2.28c-1.74-.39-3.66-1.78-3.18-4.43C-29.09 9.4-3.5 1.16 18.4 1.16c11.15 0 25.72 2.97 34.51 11.41 11.15 10.44 10.09 24.39 10.09 39.56v35.83c0 10.77 4.47 15.5 8.68 21.33 1.48 2.08 1.8 4.58-.09 6.14-4.74 3.96-13.15 11.32-17.79 15.46l-.01-.7z" fill="white"/>
                  </svg>
                </Box>
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
