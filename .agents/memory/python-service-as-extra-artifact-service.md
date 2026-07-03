---
name: Python service alongside pnpm monorepo
description: How a non-JS backend (e.g. a Twilio/FastAPI voice service) can be added when no createArtifact type fits.
---

When a request needs a backend technology outside the artifact type list (e.g. plain Python
FastAPI/websockets for a Twilio phone integration), it doesn't need its own `createArtifact` call.
Instead, add it as an additional `[[services]]` entry inside an existing artifact's
`.replit-artifact/artifact.toml` (edited via `verifyAndReplaceArtifactToml`, never in place),
with its own `localPort` and `paths` prefix. The platform auto-creates a matching workflow for it.

**Why:** `createArtifact` only supports a fixed set of types (expo, react-vite, data-visualization,
mockup-sandbox, slides, video-js) — there's no generic "backend service" type, but artifact.toml
itself supports multiple services per artifact.

**How to apply:**
- Install the needed runtime/packages via the package-management skill (e.g. `python-3.11` + pip packages) — this is independent of the pnpm workspace.
- Put the source in its own top-level directory (not inside `artifacts/`, not part of any pnpm package).
- The service's routes must all be prefixed with its `paths` entry (e.g. `/voice/...`) since the shared proxy does not rewrite paths.
- Dev `run` commands execute with cwd = the *host* artifact's directory (e.g. `artifacts/api-server`), so relative paths need `../../` to reach a top-level sibling directory; production `run.args` paths are relative to the repo root instead — mirror the pattern already used by the host artifact's own production args.
