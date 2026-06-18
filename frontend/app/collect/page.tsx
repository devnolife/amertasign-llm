import Recorder from "@/components/Recorder";

export default function CollectPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-white sm:text-3xl">
          Studio data
          <span className="text-violet-400"> — rekam & latih</span>
        </h1>
        <p className="mt-2 text-zinc-400">
          Rekam sampel gestur berlabel untuk membangun dataset, lalu latih model
          abjad. Mulai dari beberapa huruf, perbanyak sampel tiap label.
        </p>
      </header>

      <Recorder />

      <section className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 text-sm text-zinc-400">
        <h2 className="mb-2 font-semibold text-zinc-200">Tips perekaman</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Pencahayaan cukup; tangan terlihat penuh dalam frame.</li>
          <li>
            Kumpulkan ≥ 20–30 sampel per huruf dengan variasi sudut & jarak.
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
