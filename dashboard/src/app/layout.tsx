import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { UnitsProvider } from "@/components/UnitsProvider";
import { RegionalProvider } from "@/components/RegionalProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "California Power Demand Forecast",
  description: "Real-time ML-powered electricity demand predictions for California",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <UnitsProvider>
            <RegionalProvider>
              {children}
            </RegionalProvider>
          </UnitsProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
