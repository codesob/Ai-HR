import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 text-sm text-muted sm:px-6">
        <p>AI-HR · Simple HR for growing teams</p>
        <nav className="flex flex-wrap gap-5 underline underline-offset-4">
          <Link href="/trust" className="hover:text-ink">How scoring works</Link>
          <Link href="/careers/demo" className="hover:text-ink">Careers page</Link>
          <Link href="/signup" className="hover:text-ink">Create a workspace</Link>
          <Link href="/login" className="hover:text-ink">Sign in</Link>
        </nav>
      </div>
    </footer>
  );
}
