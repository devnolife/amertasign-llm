"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Pengenalan" },
  { href: "/collect", label: "Studio data" },
  { href: "/train", label: "Training" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-20 px-4 pt-4 sm:px-6">
      <div
        className="mx-auto flex w-full max-w-6xl items-center gap-1 rounded-2xl px-4 py-2.5"
        style={{
          border: "1px solid var(--border)",
          background: "rgba(9, 11, 18, 0.72)",
          backdropFilter: "blur(18px)",
          boxShadow: "0 12px 40px -18px rgba(0,0,0,0.9)",
        }}
      >
        <Link href="/" className="mr-4 flex items-center gap-2">
          <span
            className="grid h-7 w-7 place-items-center rounded-lg text-sm"
            style={{
              background: "linear-gradient(135deg, #8b5cf6, #22d3ee)",
              boxShadow: "0 4px 16px -4px rgba(139,92,246,0.7)",
            }}
            aria-hidden
          >
            ✋
          </span>
          <span className="font-display text-lg font-bold tracking-tight text-white">
            amerta<span className="gradient-text">sign</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-xl px-3.5 py-1.5 text-sm font-medium transition-all ${active
                    ? "seg--active text-white"
                    : "text-[var(--text-dim)] hover:text-white"
                  }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <span className="ml-auto hidden items-center gap-2 text-xs text-[var(--text-dim)] sm:flex">
          <span className="dot-live h-2 w-2 rounded-full bg-emerald-400" />
          on-device landmark
        </span>
      </div>
    </nav>
  );
}
