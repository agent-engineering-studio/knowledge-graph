import type { Metadata } from "next";
import { Providers } from "./providers";
import { BuyMeACoffee } from "../components/BuyMeACoffee";
import "./globals.css";

export const metadata: Metadata = {
  title: "Knowledge Graph Lab",
  description: "Knowledge Graph UI — search, query, and visualize",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
        <BuyMeACoffee />
      </body>
    </html>
  );
}
