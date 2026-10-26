"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { clearSession, type Role } from "@/lib/auth";
import { useSession } from "@/lib/useSession";

const links: { href: string; label: string; roles: Role[] }[] = [
  { href: "/recruiter", label: "Recruiting", roles: ["admin", "recruiter"] },
  { href: "/admin", label: "Analytics", roles: ["admin", "recruiter"] },
  { href: "/team", label: "Team", roles: ["admin"] },
  { href: "/employee", label: "My HR", roles: ["admin", "recruiter", "employee"] },
  { href: "/candidate", label: "My Applications", roles: ["candidate"] },
  { href: "/chat", label: "HR Assistant", roles: ["admin", "recruiter", "employee", "candidate"] },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useSession();
  const role = session?.user.role;

  return (
    <nav className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-bold text-indigo-400">
          AI-HR
        </Link>
        <div className="flex flex-wrap items-center gap-1">
          {role &&
            links
              .filter((l) => l.roles.includes(role))
              .map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className={clsx(
                    "rounded-lg px-3 py-1.5 text-sm transition",
                    pathname === l.href
                      ? "bg-indigo-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white",
                  )}
                >
                  {l.label}
                </Link>
              ))}
          {session ? (
            <button
              type="button"
              className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white"
              onClick={() => {
                clearSession();
                router.push("/");
              }}
            >
              Sign out
            </button>
          ) : (
            <>
              <Link href="/login" className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800">
                Sign in
              </Link>
              <Link href="/signup" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white">
                Start free
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
