# Launch-First Production Deployment

Date: 2026-07-24 WITA

Status: **PASS**

- Deployment id: `dpl_CzgAomaSfG5j7V1ikcjve5W6gDz6`.
- Deployment URL:
  `https://alanguagealltheirown-j9jm5ud31-isorabins-projects.vercel.app`.
- Production alias: `https://alanguagealltheirown.com`.
- Created: 2026-07-24 09:35:42 WITA.
- Status readback: Ready.
- Root deployed: `viewer/`.
- Source metadata: reviewed `main`
  `0cc16b5f21ad9c3a0d872755ac63675925ac1fa4`.
- Rollback deployment retained:
  `dpl_5AEUyzhuuHaZ6rxJzgFaGN8S6XVM`.

## Route and journey checks

- `/`: HTTP 200.
- `/human`: HTTP 200.
- Unauthenticated `GET /api/human-session`: HTTP 401 `unauthorized`.
- Empty `POST /api/suggestion`: HTTP 400 `invalid_input`, proving the route
  without adding a queue record.
- Human-session lifecycle: 204 login, 200 authenticated read, 204 logout, 401
  after logout.
- Live Try It: encode 200, decode 200, judge 200 on the same
  `adopted-cbd9f1aee46e` version; the smoke message scored 100% fidelity with
  all 4 required facts surviving and no corruption or missing facts.
