import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How scoring works · AI-HR",
  description: "How AI-HR scores candidates, who makes decisions, and how your data is handled.",
};

const sections: { title: string; body: React.ReactNode }[] = [
  {
    title: "How a match score is calculated",
    body: (
      <>
        <p>Each application gets a score from 0 to 100, built from three parts you can see on every candidate:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><b>45%: meaning match.</b> How closely the resume&apos;s content matches the job description, measured with a sentence-embedding language model.</li>
          <li><b>35%: required skills.</b> The share of the job&apos;s required skills found on the resume. Missing skills are listed by name.</li>
          <li><b>20%: experience fit.</b> Years of experience compared with the role&apos;s minimum, capped at 100%.</li>
        </ul>
        <p>
          The score is computed only from the resume&apos;s text and the job posting. AI-HR doesn&apos;t ask for or store
          protected attributes such as age, gender or ethnicity.
        </p>
      </>
    ),
  },
  {
    title: "People make the decisions",
    body: (
      <p>
        AI-HR ranks and explains; it does not reject anyone. Moving a candidate forward, rejecting them, or making an
        offer is always a recruiter&apos;s action, and every such action is recorded in the workspace activity log.
      </p>
    ),
  },
  {
    title: "When a model is unavailable, we say so",
    body: (
      <p>
        If the language model or reranker can&apos;t be reached, AI-HR falls back to rule-based scoring and keeps the
        original order. It never fills the gap with made-up scores or text.
      </p>
    ),
  },
  {
    title: "Your data stays in your workspace",
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li>Every company&apos;s data is isolated: each query is scoped to one workspace, and automated tests check it.</li>
        <li>Access is role-based. Admins, recruiters, employees and candidates each see only what their role needs.</li>
        <li>Every change (status updates, approvals, payroll runs, invites) is written to an activity log admins can review.</li>
        <li>Passwords are hashed with bcrypt. Sign-in and API traffic are rate limited.</li>
      </ul>
    ),
  },
  {
    title: "Outside providers",
    body: (
      <>
        <p>
          Matching runs on AI-HR&apos;s own servers. Two optional features use outside providers, and only when the
          workspace operator turns them on:
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li><b>Written insights and HR assistant answers</b> send the relevant text (for example a policy question, or a candidate&apos;s skills and the job title) to Groq.</li>
          <li><b>Reranking</b> sends the job description and candidate summaries to NVIDIA&apos;s retrieval API.</li>
        </ul>
        <p>Without these, AI-HR still works and labels its results as rule-based.</p>
      </>
    ),
  },
];

export default function TrustPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-10 pb-12">
      <header className="space-y-3">
                <h1 className="text-4xl text-ink">How scoring works</h1>
        <p className="text-lg text-muted">
          Candidates deserve to know how they&apos;re assessed, and you should be able to explain every decision.
          Here&apos;s exactly what the score is and isn&apos;t.
        </p>
      </header>
      {sections.map((s) => (
        <section key={s.title} className="space-y-3 text-ink-soft">
          <h2 className="text-xl text-ink">{s.title}</h2>
          {s.body}
        </section>
      ))}
      <p className="text-sm text-subtle">
        Questions about a specific deployment&apos;s data handling? Contact the company that invited you, or{" "}
        <Link href="/signup" className="text-brand-ink hover:underline">start your own workspace</Link>.
      </p>
    </article>
  );
}
