# Preview deployment receipt

Date: 2026-07-22 WITA

- Draft PR: [#1](https://github.com/isorabins/alanguagealltheirown/pull/1),
  open and draft; head was `9ede27860d9d20c9e8f77dc26c56040f342471a4` when
  the Preview was deployed.
- Preview: `dpl_F4hbURLyYz6n6AfXV8CG7F9Xd2jA`, target `preview`, status
  Ready, `https://alanguagealltheirown-h1oh9h9q2-isorabins-projects.vercel.app`.
- Preview route checks: `/` 200, `/human` 200, unauthenticated
  `/api/human-session` 401, and `GET /api/preview-cleanup` 405.
- Production re-read after Preview testing: `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS`,
  target `production`, status Ready,
  `https://alanguagealltheirown-jql8ed0jz-isorabins-projects.vercel.app`.

No production deployment, alias, routing, or credential was changed.
