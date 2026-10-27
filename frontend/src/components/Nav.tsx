"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import clsx from "clsx";
import {
  Briefcase,
  FileText,
  House,
  Info,
  LogOut,
  Menu,
  MailWarning,
  MessageCircle,
  Plane,
  Settings,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { clearSession, setSession, type Role } from "@/lib/auth";
import { useSession } from "@/lib/useSession";
import { Footer } from "@/components/Footer";

const links: { href: string; label: string; icon: LucideIcon; roles: Role[] }[] = [
  { href: "/admin", label: "Home", icon: House, roles: ["admin", "recruiter"] },
  { href: "/recruiter", label: "Hiring", icon: Briefcase, roles: ["admin", "recruiter"] },
  { href: "/team", label: "Team & payroll", icon: Users, roles: ["admin"] },
  { href: "/employee", label: "Time off & payslips", icon: Plane, roles: ["admin", "recruiter", "employee"] },
  { href: "/candidate", label: "My applications", icon: FileText, roles: ["candidate"] },
  { href: "/chat", label: "Ask HR", icon: MessageCircle, roles: ["admin", "recruiter", "employee", "candidate"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["admin", "recruiter", "employee", "candidate"] },
];

const ROLE_NAMES: Record<Role, string> = {
  admin: "HR manager", recruiter: "Recruiter", employee: "Employee", candidate: "Job seeker",
};

// Public pages keep the marketing layout even for signed-in visitors.
const MARKETING = [
  /^\/$/, /^\/trust/, /^\/careers\//, /^\/login/, /^\/signup/, /^\/accept-invite/,
  /^\/forgot-password/, /^\/reset-password/, /^\/verify-email/,
];

function VerifyEmailBanner({ email }: { email: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  async function resend() {
    setState("sending");
    try {
      await api.resendVerification();
      setState("sent");
    } catch {
      setState("error");
    }
  }
  return (
    <div className="flex flex-col gap-3 rounded-2xl bg-warning-soft px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="flex gap-3 text-[0.95rem] text-warning">
        <MailWarning className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <span>
          <b>Confirm your email.</b> We sent a link to {email}.{" "}
          {state === "sent" && "A new link is on its way."}
          {state === "error" && "Couldn't send it. Try again in a minute."}
        </span>
      </p>
      {state !== "sent" && (
        <button type="button" onClick={resend} disabled={state === "sending"}
          className="shrink-0 text-sm font-semibold text-warning underline underline-offset-4">
          {state === "sending" ? "Sending…" : "Send it again"}
        </button>
      )}
    </div>
  );
}

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand">
        <svg viewBox="0 0 20 20" className="h-4.5 w-4.5" fill="var(--color-accent)">
          <circle cx="10" cy="6.5" r="3.2" />
          <path d="M3.5 17c.6-3.6 3.3-5.8 6.5-5.8s5.9 2.2 6.5 5.8z" />
        </svg>
      </span>
      <span className={clsx("font-display text-xl", inverted ? "text-white" : "text-ink")}>AI-HR</span>
    </Link>
  );
}

function MarketingNav({ signedIn, home }: { signedIn: boolean; home: string }) {
  return (
    <header className="sticky top-0 z-30 bg-canvas/95">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Logo />
        <nav className="flex items-center gap-1">
          <Link href="/#product" className="btn-ghost hidden text-ink sm:inline-flex">Product</Link>
          <Link href="/trust" className="btn-ghost hidden text-ink sm:inline-flex">How scoring works</Link>
          {signedIn ? (
            <Link href={home} className="btn-dark ml-2 px-4 py-2 text-sm">Open my workspace</Link>
          ) : (
            <>
              <Link href="/login" className="btn-ghost text-ink">Sign in</Link>
              <Link href="/signup" className="btn-dark ml-1 px-4 py-2 text-sm">Try it free</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

function Sidebar({ role, onNavigate, dark = false }: { role: Role; onNavigate?: () => void; dark?: boolean }) {
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
                "flex items-center gap-3 rounded-lg px-3 py-2 text-[0.92rem] font-medium transition",
                dark
                  ? active ? "bg-white/10 text-canvas" : "text-[#a39b8b] hover:bg-white/5 hover:text-white"
                  : active ? "bg-brand-soft font-semibold text-brand" : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              <Icon className={clsx("h-[1.15rem] w-[1.15rem]", dark && active && "text-brand")} aria-hidden />
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
  const userId = user?.id;

  // The cached user is only a hint; confirm the session with the server once per load (and pick up changes).
  useEffect(() => {
    if (userId) api.me().then((u) => setSession({ user: u })).catch(() => undefined);
  }, [userId]);

  if (!user || MARKETING.some((re) => re.test(pathname))) {
    return (
      <>
        <MarketingNav signedIn={!!user} home={home} />
        <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-10 sm:px-6">{children}</main>
        <Footer />
      </>
    );
  }

  const signOut = async () => {
    await api.logout().catch(() => undefined);
    clearSession();
    router.push("/");
  };

  const initials = user.full_name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const userCard = (dark: boolean) => (
    <div className={clsx("flex items-center justify-between gap-2 rounded-xl p-2", dark ? "bg-white/5" : "border border-line bg-surface")}>
      <Link href="/settings" className="flex min-w-0 items-center gap-3 hover:opacity-80" title="Your settings">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-semibold text-brand">
          {initials}
        </span>
        <span className="min-w-0">
          <span className={clsx("block truncate text-sm font-medium", dark ? "text-white" : "text-ink")}>{user.full_name}</span>
          <span className={clsx("block truncate text-xs", dark ? "text-white/50" : "text-subtle")}>{ROLE_NAMES[user.role]}</span>
        </span>
      </Link>
      <button type="button" onClick={signOut} aria-label="Sign out" title="Sign out"
        className={clsx("rounded-lg p-2 transition", dark ? "text-white/50 hover:bg-white/10 hover:text-white" : "text-muted hover:bg-surface-2 hover:text-ink")}>
        <LogOut className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );

  const isDemo = user.email.endsWith("@aihr.demo");

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <div className="hidden border-r border-line bg-surface lg:block">
      <aside className="sticky top-0 flex h-screen flex-col gap-8 px-3 py-5">
        <div className="px-2"><Logo /></div>
        <Sidebar role={user.role} />
        <div className="mt-auto">{userCard(false)}</div>
      </aside>
      </div>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-canvas px-4 lg:hidden">
        <Logo />
        <button type="button" className="btn-ghost px-2" onClick={() => setOpen((v) => !v)}
          aria-expanded={open} aria-label={open ? "Close menu" : "Open menu"}>
          {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
        </button>
      </header>
      {open && (
        <div className="space-y-4 border-b border-line bg-surface px-4 py-4 lg:hidden">
          <Sidebar role={user.role} onNavigate={() => setOpen(false)} />
          {userCard(false)}
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-8 lg:px-12 lg:py-8">
        <div className="mx-auto max-w-5xl space-y-8">
          {isDemo && (
            <div className="flex flex-col gap-2 rounded-xl border border-brand/15 bg-brand-soft/70 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-center gap-2.5 text-sm text-brand-ink">
                <Info className="h-4 w-4 shrink-0" aria-hidden />
                <span>
                  <b className="font-semibold">Demo workspace</b> · Halcyon Robotics is a sample company with made-up people. Click anything.
                </span>
              </p>
              <button type="button" onClick={signOut} className="shrink-0 text-sm font-semibold text-brand-ink hover:underline">
                Leave demo
              </button>
            </div>
          )}
          {!isDemo && !user.email_verified_at && <VerifyEmailBanner email={user.email} />}
          {children}
        </div>
      </main>
    </div>
  );
}
