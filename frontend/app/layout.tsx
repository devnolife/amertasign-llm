import type { Metadata } from "next";
import {
  Bricolage_Grotesque,
  JetBrains_Mono,
  Plus_Jakarta_Sans,
} from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
});

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "amertasign — pengenalan isyarat BISINDO & SIBI",
  description:
    "Pengenalan bahasa isyarat Indonesia (BISINDO & SIBI) real-time berbasis kamera.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="id"
      className={`${jakarta.variable} ${bricolage.variable} ${jetbrains.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <div className="bg-stage" aria-hidden>
          <div className="bg-aurora bg-aurora--violet" />
          <div className="bg-aurora bg-aurora--cyan" />
          <div className="bg-aurora bg-aurora--magenta" />
        </div>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
