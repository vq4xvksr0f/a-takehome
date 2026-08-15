# Prompt Log — excerpts from agent-assisted build sessions

These are excerpts from the AI coding-agent sessions where this take-home was built (Kimi Code CLI, 15 Aug). My prompts are verbatim; agent responses and tool outputs are condensed to 1–3 sentence outcomes. Full session transcripts are available on request.

**What I think this shows:** I use the agent as a fast junior pair, not an autopilot. I set the contract first (system design, `.env.example`, ports), delegate well-scoped chunks to subagents in parallel, and spend my own attention on the things agents get wrong — scope creep, security edges, reviewer UX, and whether the tests actually test anything. Most exchanges below are me *stopping* the agent from doing too much, not pushing it to do more.

Sessions ran concurrently — I was testing one change while directing the next on a separate branch/worktree — so the timeline below interleaves.

---

## Session 1 — System design first, then parallel build-out (~09:21–12:07)

I opened by front-loading design before any implementation code:

> **Me:** You are helping me build a take-home interview assignment. Before writing implementation code, create a production-quality system design/documentation plan for the application described below. [pasted full Alma assignment spec: lead-management app, public prospect form with resume upload, confirmation + notification emails, attorney auth to view/update leads]

**Agent:** Produced `docs/system-design.md` — architecture, schema, auth model, email flow, API surface, error handling — which became the contract for everything built after.
→ *Design-before-code: the doc became the spec every later prompt and subagent was checked against.*

> **Me:** wait can we update it so we seed the db upon init with a user admin@tryalma.com and password is password.

**Agent:** Added a startup seeder so a fresh clone is immediately demo-able.
→ *Reviewer UX: optimizing for the person grading it on a fresh machine.*

> **Me:** is boto3 and minio and stuff all fine here? also wdyt about this: Biggest issue: JWT cookie + Next.js architecture. You say frontend POSTs login → FastAPI sets HttpOnly cookie, and then Next.js middleware / server-component checks... [pushed on the auth design]

**Agent:** Walked through the HttpOnly-cookie flow against Next.js server components and confirmed the middleware token check is sound, adjusting cookie settings to match.

> **Me:** is this safe though? i dont want the interviewer to hit a weird cors or cookie issue

**Agent:** Tightened CORS origins and cookie attributes (`SameSite=Lax`, same-origin proxying through Next rewrites) so the reviewer hits no cross-origin friction running it locally.
→ *Security instinct: I didn't accept the first auth answer — pushed on the failure mode the reviewer would actually hit.*

> **Me:** also for email i can provide a real resend api key but could we also add an (Actually, an outbox table would be a really nice production-thinking mention without implementing a queue.) ???? wdyt? im open. also this: I'd NOT hard-code admin@tryalma.com...

**Agent:** Added a simple `email_outbox` table (production-thinking without a real queue), moved seed users to env config instead of hard-coding.

> **Me:** this is the raw interview guideline do u think im overengineering it or any smells? [pasted spec again]

**Agent:** Flagged where the design exceeded the spec and recommended trims — e.g.:

> **Me:** simplify outbound email_outbox pls like the drain n stuff for the takehome

**Agent:** Stripped the outbox down to a minimal table + synchronous drain on write, documented as a deliberate simplification.
→ *Scope discipline: used the spec as a ceiling, not a floor — asked the agent to find my own over-engineering.*

> **Me:** ok can you star building this? u can fan out with subagents.

**Agent:** Fanned out two subagents in parallel — one built the FastAPI backend, one the Next.js frontend, both against the design doc and `.env.example` contract (see "Subagent usage" below). Scaffold landed, tests green.

> **Me:** actually can we change the ports for our stuff to not be the default, i think there is a chance the user will have other stuff running

**Agent:** Remapped host ports to the 3xxx/8xxx range in compose + docs so the reviewer's machine won't collide with existing services.
→ *Reviewer UX again: pre-empting "port already in use" on the grader's laptop.*

> **Me:** ok the Backend pytest stays 13/13 green can u check if these are any value at all? I dont want tests that dont test anything.

**Agent:** Audited all 13 tests, identified the assertion-light ones, and rewrote them to actually verify behavior.
→ *Distrust of green CI: passing tests aren't evidence — made the agent prove the assertions bite.*

> **Me:** raise a stacked pr [...] with correct logging please. dont add comments in the code for this one unless its needed. useless comments are a code smell.

**Agent:** Opened a stacked logging PR. When it started over-engineering (correlation IDs, middleware layers), I stopped it, made it justify what was actually broken, then landed a simple structlog setup instead.
→ *Course-correction: killed the agent's gold-plating mid-flight and made it argue for the simple fix.*

---

## Session 2 — Frontend production structure & design-doc iteration (~10:33–12:23)

> **Me:** can u read the systemdesign md please and look at what im doing. can u also check why i get this error when trying to login: Application error: a server-side exception has occurred... [pasted digest]

**Agent:** Traced the login crash through server logs to the cookie/middleware config and fixed it.

> **Me:** ok the frontend can we start refactoring it into a more prod like folder structure. also the leads board id like 2 swim lanes please with cards that show name email and submitted. think about this from prod like structures and best practice. ask me q[uestions]

**Agent:** Proposed a feature-based `src/` layout (app / features / lib / types), then built the two-lane drag-and-drop leads board with cards.

> **Me:** drag and drop doesnt work when i try and move stuff over.

**Agent:** Debugged the drop handling; when a first fix didn't hold:

> **Me:** it still doesnt drop properly or scale properly. can you do a full audit of the dnd implementation?

**Agent:** Did a full audit of the dnd implementation, replaced the broken scaling/drop logic, verified state transitions persist via the API.
→ *Verification loop: I test every claim by hand; a "fixed" that isn't, gets escalated to a full audit, not another guess.*

> **Me:** wait the current folder structure doesnt sound right either for nextjs best practice. /app /features /lib /types. lets talk first about how we can clean this up. we dont need back compat

**Agent:** Discussed trade-offs first (per my ask), then unified on a clean Next.js structure with no back-compat shims.
→ *Talk-first mode: for structural decisions I make the agent argue options before touching code.*

> **Me:** also what do you think about this? Add `import 'server-only';` to `src/server/api-client.ts`. Do not add route groups or another abstraction layer unless separate layouts are actually needed. u can push back

**Agent:** Agreed on `server-only` guard, pushed back (correctly) on a couple of extra layers I floated — kept structure minimal.
→ *Explicitly inviting pushback keeps the agent honest instead of sycophantic.*

> **Me:** visuals eg tree structure stuff is also fine, the wall of text is not nice. [on the PR description / design doc formatting]

**Agent:** Reworked the doc/PR formatting into tree diagrams and compact tables instead of prose walls.
→ *Reviewer UX extends to the docs themselves: nobody grades a wall of text kindly.*

---

## Session 3 — Attorney/activity schema on an isolated worktree (~13:00–14:16)

> **Me:** can u create a worktree and update the ports so it doesnt clash with my current run and I want to talk about adding a lawyer table and then an activity table.

**Agent:** Created a git worktree with shifted ports so this schema work ran alongside my main stack, then talked through the attorney + activity tables before building.
→ *Parallel workflow: isolated worktree + shifted ports so feature work never blocked the running demo.*

> **Me:** basically keep it simple remember this is a takehome

**Agent:** Cut the schema to essentials: `attorneys` table, leads FK, and an `activity` table recording who moved a lead between states and when.
→ *Scope discipline, stated as a standing rule.*

> **Me:** can we make email fire n forgot but s3 not block please

**Agent:** Made confirmation email async/fire-and-forget while keeping the resume upload synchronous, so form submission latency dropped.
→ *Perf instinct with a correctness boundary: async where it's safe, blocking where the user needs the guarantee.*

> **Me:** can we add a second admin eg attorney@tryalma.com and then a third paralegal@tryalma.com so we can see a fix of activity pls. add them to the seed and password is password pls their updates should be real too.

**Agent:** Seeded three demo users; activity entries attribute state changes to the actual logged-in user, so the demo shows real attribution.
→ *"Their updates should be real too": no fake demo data — the activity feed had to reflect actual auth state.*

> **Me:** backend/app/core/logging_format.py need its own file thats a bit sus [...] also default SEED_DEMO_DATA to true. also is that the best place? what if we give a setup script for them to run for docker/make wdyt? is that a better ux?

**Agent:** Inlined the logging format, defaulted demo seeding on, and added a `make seed` plus a single combined `make setup` so the reviewer runs one command.
→ *Reading code critically (flagging a suspicious one-off file) + one-command setup for the reviewer.*

> **Me:** backend/app/services/email_service.py could we do something about the email failure/ retrying? — wait yeah could do we an email retry but not too complex and async so non blocking

**Agent:** Added a bounded, non-blocking retry in the email service, deliberately simple.
→ *Scoped the fix in the same breath as requesting it: retry yes, but bounded, async, simple.*

> **Me:** dont merge in the port changes [the worktree's shifted ports were about to leak into the PR]

**Agent:** Excluded the local-only port overrides from the PR before merge.
→ *PR hygiene: caught local-only config before it leaked into the reviewer's diff.*

---

## Session 4 — Email integration, UX, tests, linting & final review (~12:09–14:26)

> **Me:** read system design md please im working on this takehome. i want to now test the resend integration and templates. Add another admin seed that is [my gmail] and ill update with a real resend api key. where do our templates live?

**Agent:** Located the email templates, added the seed, and after I dropped a real key into `.env`, restarted and verified sends.

> **Me:** can u check logs why didnt resend send

**Agent:** Found the failure in backend logs (sandbox sender restriction), switched to `onboarding@resend.dev`, confirmed delivery end-to-end.
→ *Debugging direction: gave the agent the failure, pointed it at logs, verified delivery end-to-end — not just "no error thrown".*

> **Me:** do you think the way we're using css is good best practice? [...] lets follow prod patterns for the css stuff

**Agent:** Migrated the monolithic `globals.css` to co-located CSS Modules per component (delegated to a subagent, then a second subagent fixed the bugs the first introduced).
→ *Also honest about delegation failure: the first subagent regressed styling, so a second was dispatched with the bug context.*

> **Me:** ok i think we should add some more tests i think we're missing some wdyt about fe side think about the test pyramid

**Agent:** Assessed coverage against the pyramid; added vitest unit tests for the frontend's bottom layer and backend endpoint tests for the gaps.
→ *Test strategy, not test count: aimed new tests at the pyramid's missing layer.*

> **Me:** remove my pii please from the pr — no real-name mentions in the code

**Agent:** Grepped the PR for my real name/email in comments and seed strings and scrubbed them before merge.
→ *PII hygiene before the repo went anywhere public.*

> **Me:** no no if i dont want ci. what should i have eg linters n stuff — can i use oxlint? also what is ruff?

**Agent:** Explained the no-CI toolchain, then added oxlint (frontend) + ruff (backend) wired into a pre-commit hook and a `make` check target.
→ *Tooling judgment: the guardrails of CI without the ceremony — pre-commit + one make target.*

> **Me:** remove all comments from this PR unless its needed.

**Agent:** Stripped noise comments across the PR, keeping only the few that explain non-obvious decisions.

> **Me:** do these 3 exist in the env example? (admin@, attorney@, paralegal@tryalma.com so when they run it itll work?

**Agent:** Verified `.env.example` contains all three seed users so a reviewer's fresh `make setup` reproduces the demo exactly.
→ *Closing the loop: every demo affordance earlier in the log had to exist in `.env.example` or it doesn't exist for the reviewer.*

Final pass — I pasted the Alma functional spec back and asked for a full gap audit:

> **Me:** yeah ok can we add this pls why no client-side file size/type check despite the form advertising "10 MB" also can we create another pr for this

**Agent:** Added client-side resume type/size validation matching the advertised 10 MB limit, plus the favicon, in its own PR.
→ *Spec-compliance review: the form promised 10 MB, nothing enforced it — caught in the audit, fixed in its own PR.*

> **Me:** can you do a scan through and check if we have any code smells any hardcoded stuff?

**Agent:** Swept the repo; surfaced dead code, leftover hardcoded values, and an exported-but-unused `parseApiError`.

> **Me:** clean these up and remove these: Dead code inviting reviewer questions: parseApiError() (server/api-client.ts:40-47) — exported, imported nowhere; the three call sites reimplement it inline...

**Agent:** Removed the dead code and hardcoded leftovers in a cleanup PR.
→ *Reviewing for the reviewer: deleted code that would have invited questions, before they could ask.*

> **Me:** they dont conflict with pr 12? [I was merging another PR at the same time]

**Agent:** Checked overlap against PR 12 file-by-file and confirmed a clean merge order.
→ *Parallel-PR discipline: verified merge order instead of letting git find the conflicts.*

---

## Subagent usage

Two examples of delegating well-scoped chunks to subagents from the main session:

- **Initial parallel build (Session 1):** fanned out `agent-0` — "Build the FastAPI backend for a lead-management take-home app. You are building ONLY the backend... The root `docker-compose.yml` and `.env.example` already exist and define the contract you must build against — read them first." — and `agent-1` with the mirror-image frontend brief. Both delivered against the design-doc contract; backend pytest 13/13 green on first integration. → *The brief names the contract file, the boundary ("ONLY the backend"), and what to read first — that's why integration passed first try.*
- **CSS Modules migration (Session 4):** subagent brief included an explicit per-file mapping ("each component/page gets a co-located `*.module.css`; `globals.css` keeps ONLY the design tokens... IMPORTANT: keep `.site-shell` global"). Migration completed across the app; when it introduced styling regressions, a second subagent was dispatched with the bug context and fixed them. → *Specific-enough briefs that the failure mode was recoverable: hand the next agent the bug context and it lands the fix.*

---

*Generated from local session transcripts (Kimi Code `~/.kimi-code/sessions/`). Timestamps are local time (AEST).*
