# Blog series plan: *Building an agent that isn't allowed to press the button*

A weekly build-in-public series on owenadirah.com/blog, one post per week of the 8-week plan plus a finale. Written for AI engineers and for the hiring panels who read their portfolios.

## What the series is for

- **For readers:** a practical account of building an agent you could defend in a production review, with the code, the numbers and the mistakes.
- **For the portfolio:** each post is evidence of judgement. The project shows *that* it works; the posts show *why* it was built this way.
- **For me:** a forcing function. A weekly post means each week ends with something that runs.

## House rules

1. **Real artefacts only.** Every snippet comes from the repository at a tagged commit; every number comes from a run I can reproduce. No illustrative numbers dressed up as results.
2. **One idea per post**, stated in the first paragraph.
3. **A "what broke" section in every post.** The failures are the most useful part, and nobody believes a build log where everything worked first time.
4. **One diagram per post, at most.** Use it only where the prose struggles.
5. **Credit the book** where its ideas appear (Shimonski, *AI in Healthcare*, Wiley 2021).
6. **Length:** 1,200–1,800 words. British English.
7. **Close with a link to the repo tag and one line on next week.**

## The posts

| # | Publish | Working title | The one idea |
|---|---|---|---|
| 0 | End of week 1 | Why I'm building an AI ops agent that can't press the button | Trust in production agents comes from evidence, evaluation and approval, not cleverness |
| 1 | End of week 1 | Write the incidents before the code | Ground truth first: scenarios are the spec, the demo and the eval set at once |
| 2 | End of week 2 | Building a fake hospital that fails on purpose | A simulated estate with realistic faults is what makes an agent testable |
| 3 | End of week 3 | Facts, hypotheses, recommendations: typing an agent's output | Structured findings make an LLM's reasoning checkable |
| 4 | End of week 4 | Tools are evidence, and logs can lie | MCP tools with provenance, and treating retrieved text as data, never instructions |
| 5 | End of week 5 | Approval you can't bypass | Proposal, approval, execution and verification as separate trust boundaries; restored is not fixed |
| 6 | End of week 6 | Measuring an agent: 40 incidents, a baseline and three models | What the evals said, including where the agent lost to a rule |
| 7 | End of week 7 | Designing a console people can trust | UI decisions that keep an agent honest: one accent, one meaning; nothing hides on failure |
| 8 | After week 8 | Eight weeks later: results, costs and what I'd change in production | The full numbers and an honest production gap list |

## Post outlines

### 0. Why I'm building an AI ops agent that can't press the button
- **Hook:** the 3 a.m. lab-results outage, and the two questions on-call needs answered.
- **Points:** the book's warning that restoring a service is not fixing it; the portfolio gap (evals, guardrails, governed actions); what "trustworthy" will mean, measurably.
- **Artefact:** the S2 scenario file, shown as the "contract" for the whole project.
- **Needs from Owen:** ⚠ a real incident or on-call moment from your own work to open with. I will not write one for you. One or two sentences on what happened and what you wished you had.

### 1. Write the incidents before the code
- **Points:** six scenarios with ground truth, forbidden actions and eval variants; the contracts package that validates them against the service catalogue; deterministic blast radius.
- **What broke:** getting CopilotKit onto Angular 22. The prebuilt stylesheet's native `@layer` clashed with the template's Tailwind v3 pipeline, and the fix was to stop sending it through PostCSS at all.
- **Artefact:** the validation errors a bad scenario produces (from the how-to guide).

### 2. Building a fake hospital that fails on purpose
- **Points:** one image configured per service; fault toggles; why the node-failure scenario needs a real second node (ADR-0012); keeping observability lean on a shared VPS.
- **What broke:** *(fill from week 2)*.
- **Artefact:** before/after metrics for one injected fault.

### 3. Facts, hypotheses, recommendations: typing an agent's output
- **Points:** the Findings schema; rejecting unknown evidence IDs; why "facts carry no confidence score".
- **What broke:** *(fill from week 3)*.
- **Artefact:** a real Findings object for S1 and its rendering in the console.

### 4. Tools are evidence, and logs can lie
- **Points:** MCP tools with templated queries only; wrapping tool output as evidence; the poisoned runbook and the injected log line.
- **What broke:** *(fill from week 4)*.
- **Artefact:** a trace where the agent flags an injection instead of obeying it.

### 5. Approval you can't bypass
- **Points:** the agent has no execution tool; approval hashes and expiry; LangGraph `interrupt` with a durable checkpointer; the executor's re-checks; S5 ending as *resolved with problem*.
- **What broke:** *(fill from week 5)*.
- **Artefact:** sequence diagram of propose → approve → execute → verify.

### 6. Measuring an agent: 40 incidents, a baseline and three models
- **Points:** replayed snapshots for reproducible evals; deterministic scoring first, LLM judge last; OpenAI vs DeepSeek vs Qwen on accuracy, safety, cost and latency.
- **Already learned:** streamed responses only report token usage if the client asks for it (`stream_usage=True`). Without that, every call is unmetered and the budget reads low. Unknown spend now shows as unknown.
- **Artefact:** the eval report table, unedited.

### 7. Designing a console people can trust
- **Points:** design tokens straight from the OpenDesign export; facts above hypotheses; the role switcher that changes permissions but never data; Replay mode when the budget runs out.
- **What broke:** *(fill from week 7)*.
- **Artefact:** the component sheet screenshot.

### 8. Eight weeks later
- **Points:** the headline result sentence; total LLM spend; what a real hospital deployment would need (HA, OIDC, compliance mapping, real HL7/FHIR feeds).
- **Artefact:** the 2–3 minute demo video.

## Distribution

- Publish on owenadirah.com/blog. Use the canonical URL if cross-posting to Medium or dev.to.
- A short LinkedIn post per article: the one idea, one image, the link.
- Link every post from the README's status line and from the project's case study.

## Tracking

Each post is a beads task under the "Blog series" epic, blocked by the week it describes. Run `bd ready -l blog` to see which posts can be written next.
