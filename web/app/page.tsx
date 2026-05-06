import Image from "next/image";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center flex-1 px-6 py-16 text-center">
      <Image
        src="/r-logo.png"
        alt="Rally"
        width={120}
        height={120}
        priority
        className="mb-8"
      />
      <h1 className="text-5xl font-bold tracking-tight">Rally</h1>
      <p className="mt-4 max-w-md text-lg opacity-80">
        Short videos about real projects. Your engagement directs AI agents.
      </p>
      <p className="mt-12 text-sm opacity-50">
        Feed coming online. Day 1 in progress.
      </p>
    </main>
  );
}
