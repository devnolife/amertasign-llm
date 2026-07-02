import SignRecognizer from "@/components/SignRecognizer";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="animate-rise mb-10">
        <span className="eyebrow mb-4">
          <span className="dot-live h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Real-time · BISINDO &amp; SIBI
        </span>
        <h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Isyarat jadi <span className="gradient-text">teks</span>,
          <br className="hidden sm:block" /> langsung dari kamera.
        </h1>
        <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-[var(--text-dim)]">
          Arahkan tangan ke kamera — sistem membaca landmark gerakanmu dan
          menerjemahkannya menjadi huruf, kata, hingga kalimat.
        </p>
      </header>

      <div className="animate-rise delay-2">
        <SignRecognizer />
      </div>

      <footer className="animate-rise delay-4 mt-14 flex items-center gap-2 text-xs text-[var(--text-dim)]">
        <span className="chip chip-mono">🔒 privasi</span>
        Landmark diproses di browser (MediaPipe) — video mentah tidak pernah
        meninggalkan perangkatmu.
      </footer>
    </main>
  );
}
