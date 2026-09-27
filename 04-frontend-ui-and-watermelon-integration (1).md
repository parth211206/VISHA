# Part 5 of 5 — Frontend, Watermelon UI MCP & Main UI Experience

**India Snakebite Clinical Decision-Support + Epidemiological Surveillance System**

> Maps to Phases 1–2 in the Master Priority Order (see `00-foundation-and-status.md`, Appendix A), and also touches the epidemiology UI referenced under Phase 9. This is usually the earliest phase to pick up after the initial repository inspection, since frontend routing/build health blocks almost everything else being demonstrable end-to-end.

---

## 1. Watermelon UI MCP

The Watermelon UI MCP is already connected to this Claude environment. **Use it actively for the frontend.**

**First inspect what Watermelon UI MCP capabilities/components are actually available. Do NOT assume component names or APIs.** Use the MCP according to its actual installed tools/documentation.

The final interface should feel like a **polished modern clinical AI workstation**, not a generic dashboard.

**Design goals:**

- professional medical/research appearance
- beautiful but restrained
- high information density without clutter
- responsive desktop layout
- excellent dark/light mode if supported
- accessible contrast
- clear status hierarchy
- subtle animations only where useful
- no distracting gradients
- no gimmicky AI effects
- clear emergency/clinical information hierarchy
- consistent spacing and typography
- strong empty/loading/error states
- excellent image-analysis presentation
- interactive map for epidemiology (Leaflet + PostGIS — see Section 2's stack table)
- clean charts (Recharts — see Section 2)
- clear confidence visualization
- evidence/source panels
- audit trail visualization

These last two design goals are the reason Watermelon UI alone can't finish this UI — it doesn't ship charting or mapping components, hence the additional libraries in Section 2 immediately below.

---

## 2. Full Frontend Technology Stack

**No — Watermelon UI by itself is not enough to build this whole UI, and that's expected, not a gap in the plan.**

Based on what Watermelon UI actually is (verified, not assumed — see the inspection-first rule): it's an open-source React component registry built on **Tailwind + Radix**, offering 600+ components, ~100+ built-in animations, and dashboard/block/page templates, exposed to Claude via a hosted MCP server (`mcp.watermelon.sh`) with search/retrieval/inspiration/category/page-composition tools. That makes it a **styled-component and layout base** — it is not a charting library and not a mapping library. So the proposed additions are the right call, not redundant:

| Layer | Tool | Role in this project |
|---|---|---|
| Styled components / design system | **Watermelon UI** | Buttons, forms, cards, layout shells, dashboard blocks, page templates — the visual base for every screen in Part 5, Section 3. |
| Animation | **Framer Motion** | Custom orchestrated transitions (step-by-step New Case wizard, analysis-result reveal, evidence fusion panel). **Check Watermelon's own ~100 built-in animations first** via the MCP's inspiration/search tools before reaching for Framer Motion on something Watermelon may already animate — avoid installing a second animation engine to do a job the component library already does. Use Framer Motion for the custom sequencing Watermelon doesn't cover. |
| Charts | **Recharts** (recommended over Chart.js for this stack) | Epidemiology trends, species/genus distribution, confidence visualization. Recharts is composed as React components, which fits a React/Vite/TypeScript codebase and Tailwind theming far more naturally than Chart.js's imperative canvas API + `react-chartjs-2` wrapper. Reach for Chart.js only if a specific chart type (e.g., very large point counts) genuinely needs canvas-level performance Recharts can't give you — unlikely for aggregated epidemiology views. |
| Maps | **Leaflet** (frontend) + **PostGIS** (backend) | These are two different layers, not two alternatives — Leaflet renders the interactive India map / case-cluster view in the browser; PostGIS is the spatial query engine in your database (per the architecture in Part 1) that Leaflet's GeoJSON/marker data comes from via your backend API. Confirm the backend's PostGIS layer and its API contract (Phase 9, Part 4) before wiring Leaflet to it, so the frontend isn't built against endpoints that don't exist yet. |
| Icons | **Heroicons** | Clean, MIT-licensed, Tailwind-native icon set — pairs naturally with a Tailwind-based system like Watermelon. Check whether Watermelon's components expect a specific icon prop/format (e.g., they may default to Lucide or Radix Icons internally) before swapping icon sets wholesale, so icons don't visually clash with any icons baked into Watermelon's own components. |

**One clarification worth making explicit, since it changes how you'd actually set this up**: only Watermelon UI is an MCP connector — it's the one tool in this table accessed by "connecting to your Claude account" (the hosted MCP server, per Part 5 Section 1). **Framer Motion, Recharts, Leaflet, and Heroicons are not MCP tools and don't get "connected" the same way** — they're ordinary npm packages (`framer-motion`, `recharts`, `leaflet` + `react-leaflet`, `@heroicons/react`) that get added to `package.json` and imported directly in code, the same way any other frontend dependency would be. Claude Code (or whichever agent is doing the implementation) installs and imports them as normal — there's nothing to authenticate or connect for those four.

---

## 3. Main UI Experience

Create the application around a central clinical workspace.

### Suggested structure — Left Sidebar

- Dashboard
- New Case
- Cases
- Snake Analysis
- Antivenom Reference
- Surveillance
- Epidemiology
- Audit Log
- Admin

### Main Dashboard

Show:

- active cases
- pending clinician reviews
- uncertain predictions
- OOD cases
- recent verified cases
- geographic activity
- system health
- dataset/model version

### New Case

Use a clean step-based workflow:

1. Patient/case information
2. Bite information
3. Symptoms/signs
4. Geographic information
5. Optional snake image
6. Analyze
7. Evidence fusion
8. Clinician review
9. Confirm/save

### Analysis View

Show:

- uploaded image
- predicted species
- predicted genus
- alternative candidates
- calibrated confidence
- OOD status
- geographic consistency
- clinical consistency
- dangerous-confusion warning where applicable
- Grad-CAM/explanation
- evidence sources
- model version
- timestamp

**Never display a single probability as if it were medical certainty.** (See Part 4, Clinical Safety, for the full rule set this UI must enforce.)

### Case Review

Clinician should be able to:

- accept prediction
- modify prediction
- mark uncertain
- add clinical notes
- confirm final taxonomy/group
- record reasoning
- save verified case

### Epidemiology

Show:

- India map
- state/district aggregation where privacy allows
- temporal trends
- species/genus distribution
- verified vs. unverified cases
- uncertainty/OOD counts
- filters
- drill-down
- **no unnecessary exposure of personally identifiable information**

### Admin

Show:

- backend health
- ML model version
- dataset version
- taxonomy version
- database status
- audit logs
- disagreement queue
- user/role management
- ingestion status

---

## 4. Watermelon MCP Integration Rule

**Do not redesign the entire application from scratch.**

**Preserve existing backend/API contracts.**

Use Watermelon UI MCP to **improve and complete** the existing frontend.

**Before changing an existing component:** inspect it.
**Before creating a duplicate component:** search the existing frontend.

**Reuse shared components whenever possible.**

---

## Before considering this phase complete

- Re-run the Testing Cadence in `00-foundation-and-status.md`, Appendix C — frontend type checking and frontend build are non-negotiable here, not optional.
- Confirm every sidebar destination above actually routes to a real page (even a stub with a strong empty state), not a dead link — "strong empty/loading/error states" from the design goals applies to every page, not just the ones with data already flowing.
- Update `PROJECT_STATUS.md` per page/route, since different routes will likely be at different statuses (e.g., Dashboard might be `INTEGRATION TESTED` while Epidemiology is still `IMPLEMENTED BUT NOT TESTED`).
