# Part 4 of 5 — Clinical Knowledge, Antivenom Reference & Clinical Safety Rules

**India Snakebite Clinical Decision-Support + Epidemiological Surveillance System**

> Maps to Phase 8 in the Master Priority Order (see `00-foundation-and-status.md`, Appendix A), plus cross-cutting safety rules that apply to every other part of the system, including the ML outputs from Part 3 and the UI from Part 5.

---

## 1. Clinical Knowledge (Phase 8)

The system needs authoritative clinical references.

Use and cite official/reliable sources such as:

- Government of India Ministry of Health and Family Welfare snakebite Standard Treatment Guidelines
- NCDC National Action Plan for Prevention and Control of Snakebite Envenoming
- WHO snakebite guidelines/resources
- other authoritative toxinology/clinical sources where appropriate

**These are KNOWLEDGE SOURCES, not ML image-training datasets.**

Create a versioned clinical knowledge structure containing, per entry:

- `source`
- `document`
- `publication/update date`
- `clinical topic`
- `symptom/sign`
- `syndrome`
- `evidence`
- `citation`
- `region`
- `notes`

**Never invent medical guidance.**

---

## 2. Antivenom Knowledge (Phase 8)

Create a versioned, auditable antivenom reference structure.

Every medically relevant entry must preserve:

- `snake/taxon`
- `venom category`
- `clinical syndrome`
- `antivenom/product reference`
- `region`
- `manufacturer if relevant`
- `source`
- `source URL`
- `source date`
- `verification status`

**Do not infer treatment merely from an image prediction.**

The application must clearly distinguish, at all times, in the data model and the UI:

- AI prediction
- clinical evidence
- reference information
- clinician decision

---

## 3. Clinical Safety (cross-cutting — applies to ML outputs, UI, and any LLM/RAG layer)

The UI must clearly communicate that this is **clinical decision support, not autonomous diagnosis**.

**Never:**

- claim certainty where there is uncertainty
- prescribe treatment autonomously
- let the LLM override clinical rules
- hide low confidence
- hide OOD/unknown results
- turn species classification into automatic treatment authorization

**Always provide:**

- confidence
- uncertainty
- alternative candidates
- geographic consistency
- clinical consistency
- source citations
- clinician confirmation

---

## 4. LLM/RAG Constraint (Phase 10, but the rule applies from day one)

If an LLM/RAG layer is used anywhere in the system, it must remain strictly an **explanation/evidence-retrieval layer**.

It **MUST NOT**:

- silently override deterministic clinical rules
- silently override clinician confirmation
- silently override verified reference data (the antivenom/clinical knowledge structures above)

The clinician remains the final decision-maker in every configuration of this system, with or without an LLM/RAG layer active.

---

## Before considering this phase complete

- Re-run the Testing Cadence in `00-foundation-and-status.md`, Appendix C.
- Verify in the actual running UI (not just the data model) that the four-way distinction — AI prediction / clinical evidence / reference information / clinician decision — is visually and structurally clear to a clinician using the system, not just present in the backend schema.
- Update `PROJECT_STATUS.md` with the verification status of each antivenom/clinical knowledge entry — a versioned structure with unverified entries is `IMPLEMENTED`, not `REAL-DATA VALIDATED`, until each entry's source has actually been checked.
