import SignRecognizer from "@/components/SignRecognizer";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-white sm:text-3xl">
          amertasign
          <span className="text-violet-400"> — pengenalan isyarat</span>
        </h1>
        <p className="mt-2 text-zinc-400">
          Arahkan tangan ke kamera. Sistem mengenali isyarat{" "}
          <span className="text-zinc-200">BISINDO</span> &amp;{" "}
          <span className="text-zinc-200">SIBI</span> lalu menampilkan teksnya.
        </p>
      </header>

      <SignRecognizer />

      <footer className="mt-12 text-xs text-zinc-600">
        Landmark diproses di browser (MediaPipe). Video mentah tidak dikirim ke
        server.
      </footer>
    </main>
  );
}
