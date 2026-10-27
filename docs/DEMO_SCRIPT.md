# AI-HR live demo script (about 3 minutes)

The demo workspace is **Halcyon Robotics**, a sample company seeded automatically in development
(`SEED_DEMO_DATA`, on by default when `ENVIRONMENT=development`). Every match score you show was produced
by the real matching engine when it started. Nothing on screen is mocked.

## Before you present

```bash
docker compose up -d --build      # first build takes a while; later starts are fast
```

Open http://localhost:3000. If you want AI-written analysis and chat answers, set `GROQ_API_KEY` in `.env`;
without it the product still works and says when it is using rule-based results.

To reset the demo to its starting state: `docker compose down -v && docker compose up -d`
(this deletes the local demo database).

## The flow

| # | Who | Do this | Say this |
|---|-----|---------|----------|
| 1 | Anyone | On the home page, click **Try the live demo**, then **Recruiter**. | "One click, no sign-up. This is a 5-person robotics company hiring for five roles." |
| 2 | Recruiter | Under **Roles**, pick **Senior ML Engineer**. Look at **Ranked candidates**. | "Every applicant is ranked against the role. Priya is first, and here's why: every required skill matched, seven years against five required." |
| 3 | Recruiter | Point to a lower-ranked candidate's skill gaps. | "No black box. The recruiter sees the gaps, and a person decides. That's what the EU AI Act and NYC Local Law 144 expect from hiring AI." |
| 4 | Recruiter | Change a candidate's **Application status** to *interview*. | "The pipeline moves with one click; candidates and interviewers are notified." |
| 5 | Anyone | Open `/careers/demo` in a new tab. | "Every company gets a public careers page. Candidates apply here and are scored the moment they do." |
| 6 | Admin | Sign out, **Try the live demo**, then **HR admin**. Show **Hiring Funnel** and **Source Effectiveness**. | "Funnel, time to hire and source quality come from the real pipeline, not a spreadsheet." |
| 7 | Admin | Go to **My HR** and find **Pending approvals**. **Approve** a leave request. | "The same workspace runs leave, onboarding and payroll after the hire." |
| 8 | Employee | Sign in as **Employee** and open **HR Assistant**. Ask *"How many days of annual leave do I get?"* | "Employees get policy answers with the source document cited." |

## Demo accounts

All passwords are `demo12345`.

| Role | Email |
|------|-------|
| HR admin | admin@aihr.demo |
| Recruiter | recruiter@aihr.demo |
| Employee | employee@aihr.demo |
| Candidate | candidate@aihr.demo |

## Turning the demo off for a real deployment

Set `ENVIRONMENT=production` (the demo seed stays off) and `NEXT_PUBLIC_DEMO_MODE=false` (hides the
one-click demo buttons), then rebuild the frontend image.
