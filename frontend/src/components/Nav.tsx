"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/recruiter", label: "Recruiting" },
  { href: "/candidate", label: "Candidates" },
  { href: "/employee", label: "Employees" },
  { href: "/admin", label: "Analytics" },
  { href: "/chat", label: "AI Agents" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="border-b border-slate-800 bg-slate-900/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold text-indigo-400">
          AI-HR
        </Link>
        <div className="flex flex-wrap gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={clsx(
                "rounded-lg px-3 py-1.5 text-sm transition",
                pathname === l.href
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
