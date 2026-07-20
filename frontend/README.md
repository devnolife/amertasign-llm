This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Deploy terpisah dari server AI

Frontend ini TIDAK dijalankan di server AI (hpc-ai). Server AI hanya menyajikan
API FastAPI di `https://amertasign.lab-if.tech`. Deploy frontend di mesin/platform
lain (Vercel, VPS, dsb.) dengan env build:

```bash
NEXT_PUBLIC_API_URL=https://amertasign.lab-if.tech
NEXT_PUBLIC_WS_URL=wss://amertasign.lab-if.tech
```

Nilai di atas sudah tersedia di `.env.production` (dipakai otomatis oleh
`next build`) dan menjadi default `--build-arg` pada `Dockerfile`:

```bash
# Docker
docker build -t amertasign-frontend .
docker run -p 3000:3000 amertasign-frontend

# Tanpa Docker
pnpm install && pnpm build && node .next/standalone/server.js
```

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3030](http://localhost:3030) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
