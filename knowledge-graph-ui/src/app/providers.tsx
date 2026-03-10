"use client";

import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { Navbar } from "@/components/Navbar";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={defaultSystem}>
      <Navbar />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 16px" }}>
        {children}
      </main>
    </ChakraProvider>
  );
}
