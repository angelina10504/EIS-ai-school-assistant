import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "XYZ AI — School Assistant",
  description: "A human-like school assistant for students, parents, teachers and management.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
