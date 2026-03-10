"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Box, HStack, Text } from "@chakra-ui/react";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/query", label: "Search / Query" },
  { href: "/graph", label: "Graph View" },
  { href: "/ingest", label: "Ingest" },
  { href: "/chat", label: "Agent Chat" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <Box as="header" borderBottomWidth="1px" borderColor="gray.200" bg="white">
      <Box maxW="1200px" mx="auto" px={4} h="56px">
        <HStack h="100%" gap={8}>
          <Text fontWeight={700} fontSize="lg" color="blue.700">KG Lab</Text>
          <HStack gap={1}>
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                style={{
                  textDecoration: "none",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  fontWeight: pathname === l.href ? 600 : 400,
                  backgroundColor: pathname === l.href ? "#ebf8ff" : "transparent",
                  color: pathname === l.href ? "#1a5276" : "#4a5568",
                  fontSize: "14px",
                }}
              >
                {l.label}
              </Link>
            ))}
          </HStack>
        </HStack>
      </Box>
    </Box>
  );
}
