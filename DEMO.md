# SmartHR360 coherent demo

From the Compose root, seed every service with one command:

```bash
bash scripts/seed_demo.sh
```

The command is idempotent and always runs migrations first. Auth is seeded before analytical services so every service can reuse the fixed auth `user_id` values without cross-service foreign keys.

## Accounts

All accounts use password `Demo#2026!hr360`.

| ID | Email | Role | Extra groups | Demo purpose |
|---:|---|---|---|---|
| 1 | `admin@demo.smarthr360.dev` | ADMIN | — | Platform administration and audit trail |
| 2 | `hr@demo.smarthr360.dev` | HR | — | Full HR demo and the existing E2E account |
| 3 | `manager@demo.smarthr360.dev` | MANAGER | — | Engineering team management |
| 4 | `employee@demo.smarthr360.dev` | EMPLOYEE | — | Employee self-service story |
| 7 | `yasmine.alaoui@demo.smarthr360.dev` | EMPLOYEE | — | Data-science growth and medium attrition risk |
| 8 | `karim.bennis@demo.smarthr360.dev` | EMPLOYEE | — | Platform workload and critical attrition story |
| 27 | `auditor@demo.smarthr360.dev` | EMPLOYEE | AUDITOR | Read-only audit persona |
| 28 | `guest@demo.smarthr360.dev` | EMPLOYEE | AUDITOR | Public read-only live demo |

IDs 5–26 are deliberately not reassigned because existing installations may already contain historical demo users. The seeder refuses to overwrite an occupied canonical ID with another email.

## Demo story

- Dashboard: coherent departments, people, skills, reviews, goals, documents, training, and wellbeing.
- Workload: sustainable, high, and burnout-risk examples with alerts.
- Retention: low/medium/critical forecasts, conversations, completed actions, and measured outcomes.
- Career Simulator: Engineering Lead, Staff Data Scientist, and Platform Engineer mobility/succession paths.
- Policy Generator: populated analytical store and three applied policies with recorded outcomes.
- Future Skills: role-skill predictions, economic reports, and employee capability profiles.

The guest and auditor accounts derive an effective read-only role from the `AUDITOR` JWT group. They must not see write controls, and `/admin` remains blocked.

Read-only is enforced server-side by `AuditorReadOnlyMiddleware`
(`smarthr360-jwt-auth` >= 1.2.0), which rejects every unsafe HTTP method for a
token carrying the `AUDITOR` group. It lives in middleware rather than in
`permission_classes` because services override `permission_classes` on nearly
every view, so a DRF-default rule would cover only the views that happen not to
declare one — and each new endpoint would silently reopen the gap. Admins are
exempt: `is_auditor()` is also true for them.

Any service exposing endpoints to the demo must therefore include the
middleware in `MIDDLEWARE`; it is currently wired into core-hr, workload,
retention, policy-gen and career-sim. Hiding write controls in the UI is a
presentation detail, not the guarantee.
