"use client";

import { useState } from "react";

const leaveBalance = { annual: 14, sick: 8 };
const goals = [
  { title: "Complete Q2 performance review", progress: 60 },
  { title: "Finish security training", progress: 100 },
  { title: "Lead internal mobility project", progress: 25 },
];

export default function EmployeePage() {
  const [leaveType, setLeaveType] = useState("annual");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Employee Portal</h1>
        <p className="text-slate-400">Leave, goals, learning — HR operations layer (MVP UI)</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Leave Balance</h2>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-800 p-4 text-center">
              <p className="text-2xl font-bold text-indigo-400">{leaveBalance.annual}</p>
              <p className="text-xs text-slate-400">Annual days left</p>
            </div>
            <div className="rounded-lg bg-slate-800 p-4 text-center">
              <p className="text-2xl font-bold text-indigo-400">{leaveBalance.sick}</p>
              <p className="text-xs text-slate-400">Sick days left</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <select
              className="input"
              value={leaveType}
              onChange={(e) => setLeaveType(e.target.value)}
            >
              <option value="annual">Annual leave</option>
              <option value="sick">Sick leave</option>
            </select>
            <button type="button" className="btn-primary w-full">
              Request leave (workflow stub)
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="font-semibold">Goals & Performance</h2>
          <ul className="mt-4 space-y-4">
            {goals.map((g) => (
              <li key={g.title}>
                <p className="text-sm">{g.title}</p>
                <div className="mt-1 h-2 rounded-full bg-slate-800">
                  <div
                    className="h-2 rounded-full bg-emerald-500"
                    style={{ width: `${g.progress}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold">Internal Jobs & Learning</h2>
        <p className="mt-2 text-sm text-slate-400">
          Talent marketplace and AI learning recommendations connect in the enterprise phase.
          Use the HR Copilot for policy questions today.
        </p>
      </div>
    </div>
  );
}
