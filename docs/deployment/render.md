# Render deployment

`render.yaml` defines the private Render backend for this application. The API gateway is the only public service. The eight feature services and Qdrant use Render's private network. PostgreSQL, Redis, Qdrant vectors, and uploaded resumes use durable storage.

## Estimated monthly cost

The current configuration is about **$158 USD/month**, before bandwidth overages, taxes, and any optional email or AI provider charges. It uses Render's Hobby workspace and keeps the backend services on the smallest plans that fit the current workload assumptions:

| Resource | Plan | Estimated monthly cost |
| --- | --- | ---: |
| API gateway | 0.5 CPU / 512 MB | $7 |
| Resume parsing, matching, chatbot (3 services) | 1 CPU / 2 GB each | $75 |
| Interview, analytics, HR ops, payroll, notifications (5 services) | 0.5 CPU / 512 MB each | $35 |
| Qdrant private service | 0.5 CPU / 512 MB | $7 |
| PostgreSQL | 0.5 CPU / 1 GB | $19 |
| Redis Key Value | 256 MB | $10 |
| Resume uploads and Qdrant disks (10 GB each) | 20 GB total | $5 |
| **Estimated total** |  | **$158/month** |

Render currently includes 5 GB of monthly bandwidth on the Hobby workspace; additional outbound bandwidth is billed separately. Prices can change, so review the Blueprint's resource summary in Render before creating it. The three ML services use 2 GB because they load sentence-transformer models. Increase memory if their deploy or runtime logs show memory pressure.

## Provisioning

1. Push the desired branch to GitHub and wait for CI to pass.
2. In Render, create a Blueprint from `codesob/Ai-HR` and select `feat/production-saas` (or the branch you intend to deploy).
3. Review the resource list and monthly estimate before applying it. Render creates a new PostgreSQL database and new services; it does not replace the existing `hire-ai` service.
4. Render generates the JWT secret and Qdrant API key. The Blueprint connects internal services through private host addresses and runs database migrations before each API deploy.
5. Deploy the Vercel frontend with `API_ORIGIN` set to the public URL of `codesob-aihr-api`. Remove the old `NEXT_PUBLIC_API_URL` value so browser requests use the same-origin Vercel proxy. This keeps the browser's `SameSite=Lax` login cookies working.
6. Add production SMTP settings before relying on invitation, password reset, or email verification flows. Set `GROQ_API_KEY` and/or `NVIDIA_API_KEY` if the corresponding AI features are needed.

The app remains empty on first start. `SEED_DEMO_DATA` is off so the sample account and password are never created in a live environment.

## Data and access

The gateway is public for the Vercel frontend. Feature APIs, Qdrant, Postgres, and Redis are private to the Render workspace network. Resume files are on a persistent disk attached only to the resume service. Postgres data is durable and backed up according to the selected Render plan; review backup and retention settings in the dashboard.
