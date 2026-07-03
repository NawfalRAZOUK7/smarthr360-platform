# ADR-007: Shared skill taxonomy (canonical skill codes)

Date: 2026-07-02 · Status: Accepted

## Context

Three services speak about skills — core-hr (catalog + evaluations),
career-sim (position requirements + gap analysis), future-skills
(demand predictions) — and each grew its own vocabulary. Cross-service
matching relied on lowercased display names, which breaks on the first
"Python 3" vs "Python" mismatch.

## Decision

**core-hr's `Skill.code` is the platform's canonical skill identifier.**

- core-hr already enforces uniqueness on `code`; the catalog is the
  system of record.
- career-sim's `Competence` gained a `code` field; the skills-gap
  engine matches by `code` first and falls back to lowercased name
  only for data predating the taxonomy. API responses expose
  `skill_code` next to the display name.
- Demo/seed data uses one catalog (PY, DJ, K8S, SQL, COMM, ML, PM)
  loaded identically into core-hr and career-sim.
- future-skills alignment (mapping its taxonomy onto the codes) is a
  follow-up; its demand signals remain name-keyed best-effort until
  then.

## Consequences

- Renaming a skill for display no longer breaks cross-service joins.
- New requirements/evaluations should always carry a code; name-only
  entries still work but are flagged as legacy.
- A future "taxonomy sync" job (core-hr -> career-sim/future-skills)
  becomes trivial: codes are stable keys.
