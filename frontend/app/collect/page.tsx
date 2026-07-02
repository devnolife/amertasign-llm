import Recorder from "@/components/Recorder";

export default function CollectPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="animate-rise mb-10">
        <span className="eyebrow mb-4">Dataset builder</span>
        <h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Studio <span className="gradient-text">data</span>
        </h1>
        <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-[var(--text-dim)]">
          Rekam sampel gestur berlabel untuk membangun dataset, lalu latih model
          abjad. Mulai dari beberapa huruf, perbanyak sampel tiap label.
        </p>
      </header>

      <div className="animate-rise delay-2">
        <Recorder />
      </div>

      <section className="card animate-rise delay-4 mt-10 p-6 text-sm text-[var(--text-dim)]">
        <h2 className="font-display mb-3 text-base font-semibold text-white">
          Tips perekaman
        </h2>
        <ul className="list-disc space-y-1.5 pl-5">
          <li>Pencahayaan cukup; tangan terlihat penuh dalam frame.</li>
          <li>
            Kumpulkan ≥ 20–30 sampel per huruf dengan variasi sudut &amp; jarak.
          </li>
          <li>
            BISINDO memakai dua tangan; SIBI (abjad) cukup satu tangan dominan.
          </li>
          <li>Setelah cukup data, tekan &quot;Latih model abjad&quot;.</li>
        </ul>
      </section>
    </main>
  );
}
