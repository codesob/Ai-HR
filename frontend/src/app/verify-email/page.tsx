"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { CircleCheck, CircleX } from "lucide-react";
import { api } from "@/lib/api";
import { getSession, homeFor, setSession } from "@/lib/auth";
import { useSession } from "@/lib/useSession";

function VerifyEmail() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"checking" | "done" | "failed">(token ? "checking" : "failed");
  const [message, setMessage] = useState(token ? "" : "This link is incomplete. Open it from your email again.");
  // The token is single-use; make sure a re-run of the effect (dev Strict Mode) doesn't spend it twice.
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true;
    api
      .verifyEmail(token)
      .then((user) => {
        const current = getSession();
        if (current?.user.id === user.id) setSession({ user });
        setState("done");
      })
      .catch((err) => {
        setMessage(err instanceof Error ? err.message : "This link didn't work.");
        setState("failed");
      });
  }, [token]);

  const { session } = useSession();
  const next = session ? homeFor(session.user.role) : "/login";

  return (
    <div className="mx-auto max-w-md space-y-5 py-10 text-center">
      {state === "checking" && <p className="text-lg text-muted">Confirming your email…</p>}
      {state === "done" && (
        <>
          <CircleCheck className="mx-auto h-12 w-12 text-success" aria-hidden />
          <h1 className="text-3xl">Email confirmed</h1>
          <p className="text-muted">Thanks. Your account is all set.</p>
          <Link href={next} className="btn-primary">{session ? "Continue" : "Sign in"}</Link>
        </>
      )}
      {state === "failed" && (
        <>
          <CircleX className="mx-auto h-12 w-12 text-danger" aria-hidden />
          <h1 className="text-3xl">We couldn&apos;t confirm your email</h1>
          <p className="text-muted">{message}</p>
          <p className="text-muted">Sign in and use <b>Send it again</b> at the top of the page to get a fresh link.</p>
          <Link href={next} className="btn-primary">{session ? "Back to the app" : "Sign in"}</Link>
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <VerifyEmail />
    </Suspense>
  );
}
