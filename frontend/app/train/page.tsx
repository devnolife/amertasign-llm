import TrainingStudio from "@/components/TrainingStudio";

export default function TrainPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="animate-rise mb-10">
        <span className="eyebrow mb-4">Guided capture</span>
        <h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Training <span className="gradient-text">terpandu</span>
        </h1>
        <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-[var(--text-dim)]">
          Pilih huruf, arahkan tangan ke kamera, dan sistem menangkap sampel
          berlabel secara otomatis. Setelah data cukup, latih model langsung
          dari halaman ini.
        </p>
      </header>

      <div className="animate-rise delay-2">
        <TrainingStudio />
      </div>

      <section className="card animate-rise delay-4 mt-10 p-6 text-sm text-[var(--text-dim)]">
        <h2 className="font-display mb-3 text-base font-semibold text-white">
          Cara pakai
        </h2>
        <ol className="list-decimal space-y-1.5 pl-5">
          <li>Nyalakan kamera dan pilih mode (BISINDO dua tangan, SIBI satu tangan).</li>
          <li>Klik huruf yang mau dilatih, lalu tekan tombol ambil sampel.</li>
          <li>Tahan gestur selama hitung mundur &amp; sesi tangkapan — variasikan sudut/jarak sedikit.</li>
          <li>Ulangi untuk huruf lain sampai indikator hijau (target tercapai).</li>
          <li>Tekan &quot;Latih model&quot; — model baru langsung dipakai halaman Pengenalan.</li>
        </ol>
      </section>
    </main>
  );
}
