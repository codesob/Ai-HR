"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { api, type Analytics } from "@/lib/api";

function Dashboard() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.analytics().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p role="alert" className="text-red-400">{error}</p>;
  if (!data) return <p className="text-slate-400">Loading analytics…</p>;

  const funnelEntries = Object.entries(data.funnel).filter(([, v]) => v > 0);

  return (
    <div className="space-y-8">
      <PageHeader
        title="HR Analytics Dashboard"
        subtitle="Hiring funnel, match quality, source effectiveness"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Open Jobs", value: data.open_jobs },
          { label: "Total Applications", value: data.total_applications },
          { label: "Avg Match Score", value: data.avg_match_score?.toFixed(2) ?? "—" },
          { label: "Avg Time-to-Hire (days)", value: data.avg_time_to_hire_days?.toFixed(0) ?? "—" },
        ].map((m) => (
          <div key={m.label} className="card text-center">
            <p className="text-3xl font-bold text-indigo-400">{m.value}</p>
            <p className="mt-1 text-sm text-slate-400">{m.label}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 font-semibold">Hiring Funnel</h2>
          <div className="space-y-3">
            {funnelEntries.map(([stage, count]) => (
              <div key={stage}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize">{stage}</span>
                  <span>{count}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-800">
                  <div
                    className="h-2 rounded-full bg-indigo-500"
                    style={{
                      width: `${Math.min(100, (count / Math.max(data.total_applications, 1)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
            {funnelEntries.length === 0 && (
              <p className="text-sm text-slate-500">No applications in pipeline yet</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 font-semibold">Source Effectiveness</h2>
          <ul className="space-y-2 text-sm">
            {Object.keys(data.source_effectiveness).length === 0 && (
              <li className="text-slate-500">No applications yet</li>
            )}
            {Object.entries(data.source_effectiveness).map(([src, n]) => (
              <li key={src} className="flex justify-between">
                <span className="capitalize">{src.replace("_", " ")}</span>
                <span className="text-indigo-300">{n}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

    </div>
  );
}

export default function AdminPage() {
  return (
    <AuthGate title="Analytics" roles={["admin", "recruiter"]} demoEmail="admin@aihr.demo">
      {() => <Dashboard />}
    </AuthGate>
  );
}
