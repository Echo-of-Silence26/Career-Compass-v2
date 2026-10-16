# Career Compass — LLM job screening pipeline

**Status: work in progress.** Built for my own job search, not yet a packaged tool.
The eligibility gate is working and evaluated against my own decisions. The fit assessment is still being tuned,
and the end-to-end run has known bugs.

## What problem it solves

- **Time.** Checking job boards every day and filtering for relevant roles by hand is slow and repetitive.
- **Applying into silence.** I couldn't see my own blind spots. The LLM acts as a sparring partner: it shows
  where my experience is direct, adjacent or only transferable, and where the evidence for a requirement is missing.
- **Learning by building.** A real project to learn AI-assisted coding (Claude Code) and LLM evaluation hands-on.

## What it does

1. **Sources** job postings from LinkedIn and Indeed.
2. **Deduplicates** roles posted in several places and checks they are still open.
3. **Eligibility gate:** a hard-requirements check that filters out roles I'm not eligible for.
4. **Fit assessment:** ranks the remaining roles by how well my experience matches.

## What it doesn't do

- Submit applications automatically
- Prepare for interviews
- Research companies

## What I learned

### Iteration 1 — the mismatch was in my own labels, not just the model

1. **Signal:** the v1 recommendation disagreed with my own Apply / No decision on 43 of 88 roles (49%).
2. **Diagnosis:** I classified every disagreement by reason. My decision mixed three different things in
   one call: hard constraints (language, salary, seniority), preference (industry interest), and deliberate
   exploration (10 roles I applied to just to test). With no rule for which one won, my reasons were inconsistent.
3. **Correction:** split the assessment into two stages. First an eligibility gate with explicit rules
   (e.g. language, field/travel, compensation, contract type, seniority), then a separate fit assessment.
   I dropped the "should I apply" prediction entirely.
4. **Result:** on a blind run of 119 roles, the gate excluded 45, each with the job description quoted
   as evidence. Adding seniority rules then excluded 12 more and sent 15 borderline roles to human
   review instead of auto-rejecting them.
5. **Rule of thumb:** before automating a judgment, check that your own labels measure one thing.

### Iteration 2 — automation won't fix the wrong targeting

1. **Signal:** I kept reworking the fit rubric: asked the AI to extract the key skills and requirements,
   then matched my evidence against each one. I realised my own reading of job postings was biased,
   and I wasn't able to judge a good fit myself. If I can't tell whether my approach is right,
   I can't check whether the AI is doing the job correctly.
2. **Diagnosis:** low yield at both ends pointed upstream — to targeting or evidence, not to automation.
3. **Correction:** a faster test is to ask experienced people where my CV goes wrong, and to reach out
   to hiring managers for insight. That unblocks me much faster than relying on the AI to run an
   unreliable assessment.
4. **Rule of thumb:** automation is downstream of strategy. Building is slow, so test assumptions
   cheaply first. Don't automate a broken process.

### Iteration 3 — what's next

Narrow sourcing to two target role families, and hand sourcing and eligibility screening fully to the
pipeline so I only review roles that pass. I will test whether this narrower funnel raises the interview
invitation rate without adding review time, by recording each application's outcome against the job
the pipeline found.

## Repository notes

- `pipeline/` holds the code; `docs/data_pipeline/` and `docs/llm_eval/` hold the specs, policies and
  prompts it loads at runtime.
- References such as "ADR-017" point to the project's design decision log, which is kept private.
