"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import clsx from "clsx";
import {
  BarChart3,
  Briefcase,
  FileText,
  LogOut,
  Menu,
  MessageCircle,
  Sparkles,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { clearSession, type Role } from "@/lib/auth";
import { useSession } from "@/lib/useSession";
import { Footer } from "@/components/Footer";

const links: { href: string; label: string; icon: LucideIcon; roles: Role[] }[] = [
  { href: "/admin", label: "Overview", icon: BarChart3, roles: ["admin", "recruiter"] },
  { href: "/recruiter", label: "Recruiting", icon: Briefcase, roles: ["admin", "recruiter"] },
  { href: "/team", label: "Team & payroll", icon: Users, roles: ["admin"] },
  { href: "/employee", label: "My HR", icon: UserRound, roles: ["admin", "recruiter", "employee"] },
  { href: "/candidate", label: "My applications", icon: FileText, roles: ["candidate"] },
  { href: "/chat", label: "HR assistant", icon: MessageCircle, roles: ["admin", "recruiter", "employee", "candidate"] },
];

// Public pages keep the marketing layout even for signed-in visitors.
const MARKETING = [/^\/$/, /^\/trust/, /^\/careers\//, /^\/login/, /^\/signup/, /^\/accept-invite/];

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white">
        <Sparkles className="h-4 w-4" aria-hidden />
      </span>
      <span className={inverted ? "text-white" : "text-ink"}>AI-HR</span>
    </Link>
  );
}

function MarketingNav({ signedIn, home }: { signedIn: boolean; home: string }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-canvas/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Logo />
        <nav className="flex items-center gap-1">
          <Link href="/trust" className="btn-ghost hidden sm:inline-flex">Trust &amp; AI</Link>
          {signedIn ? (
            <Link href={home} className="btn-primary">Open workspace</Link>
          ) : (
            <>
              <Link href="/login" className="btn-ghost">Sign in</Link>
              <Link href="/signup" className="btn-primary">Start free</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function Sidebar({ role, onNavigate }: { role: Role; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Workspace" className="flex flex-col gap-1">
      {links
        .filter((l) => l.roles.includes(role))
        .map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                active ? "bg-brand-soft text-brand-ink" : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </Link>
          );
        })}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useSession();
  const [open, setOpen] = useState(false);
  const user = session?.user;
  const home = user ? links.find((l) => l.roles.includes(user.role))?.href ?? "/" : "/";

  if (!user || MARKETING.some((re) => re.test(pathname))) {
    return (
      <>
        <MarketingNav signedIn={!!user} home={home} />
        <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-10">{children}</main>
        <Footer />
      </>
    );
  }

  const signOut = () => {
    clearSession();
    router.push("/");
  };

  const userCard = (
    <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-surface p-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{user.full_name}</p>
        <p className="truncate text-xs capitalize text-subtle">{user.role}</p>
      </div>
      <button type="button" onClick={signOut} className="btn-ghost px-2" aria-label="Sign out" title="Sign out">
        <LogOut className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col gap-6 border-r border-line bg-canvas px-4 py-5 lg:flex">
        <Logo />
        <Sidebar role={user.role} />
        <div className="mt-auto">{userCard}</div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-canvas/90 px-4 backdrop-blur lg:hidden">
        <Logo />
        <button type="button" className="btn-ghost px-2" onClick={() => setOpen((v) => !v)}
          aria-expanded={open} aria-label={open ? "Close menu" : "Open menu"}>
          {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
        </button>
      </header>
      {open && (
        <div className="space-y-4 border-b border-line bg-canvas px-4 py-4 lg:hidden">
          <Sidebar role={user.role} onNavigate={() => setOpen(false)} />
          {userCard}
        </div>
      )}

      <main className="min-w-0 px-4 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
