import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InfraWise | Cloud Architecture Advisor",
  description: "Diseña una arquitectura Cloud justificable con costo estimado.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
