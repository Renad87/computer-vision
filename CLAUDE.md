# Poetry Vision — Project Guide for Claude Code

> Shared instructions for every team member who uses Claude Code in this repository.
> Documentation and code: English. End-user UI and descriptions in issues: Arabic.

## 1. What we are building

Upload a photo -> visual analysis -> suggested emotional mood -> user picks an emotion and a focus point -> top 3 real Arabic poems with reasons -> a 3-station historical journey (poet, story, poem) -> verses and sources. Full description: `README.md`. Module interfaces: `docs/integration_contract.md`.

## 2. Non-negotiable rules

- **No fabrication.** Never invent poems, verses, attributions, historical events, dialogues, sources, metrics, test results or human reviews. Unknown stays unknown and is shown as such.
- **Real training.** Each CV component trains or fine-tunes something (transfer learning) and is evaluated on an independent test split. Running a pre-trained model alone does not satisfy the requirement.
- **Separate what is seen from what is interpreted** (visual), **trained classes from semantic suggestions** (emotion), and **facts from narrations and interpretations** (history).
- **The emotion model suggests the mood of the image**, never the user's real psychological state.
- Never pad results: return fewer than 3 poems if fewer are suitable.
- No secrets, tokens or large weights in git. Use `.env` (ignored) and download instructions for weights over ~50 MB.
- No Streamlit. Backend: FastAPI. Frontend: React + Vite, Arabic RTL, responsive.

## 3. Ownership

| Path | Owner | GitHub epic |
|---|---|---|
| `ml/visual/`, `docs/visual_methodology.md` | Shaden | EPIC 01 |
| `ml/emotion/`, `docs/emotion_methodology.md` | Renad | EPIC 02 |
| `nlp/`, `data/poems.json`, `data/poetry_taxonomy.json`, `docs/poetry_methodology.md` | Mohammed | EPIC 03 |
| `history/`, `evaluation/`, `data/stories.json`, `data/historical_sources.json`, `data/evidence.json`, `data/poem_id_mapping.json` | Omar | EPIC 04 |
| `backend/`, `frontend/`, `docs/integration_contract.md`, `tests/` (integration) | Everyone | EPIC 05 |

Do not edit another member's module without coordinating in the related issue.

## 4. Development loop (every issue)

1. Read the issue and the contract; write a short plan (max 5 steps).
2. Ask before assuming a missing fact that would make the result misleading.
3. Write or update a focused test first where feasible.
4. Make the smallest change that passes; keep the module's public function signature as in the contract.
5. Run the tests you touched. Never claim a command ran if it did not.
6. Open a PR from `feature/<area>-<short-name>` with `Closes #N`; a teammate reviews before merge.

## 5. Reporting format

- **Plan** — **Assumptions/gaps** — **Changes** (files and why) — **Verification** (commands actually run and results) — **Next step**.
