# Career Compass — LLM job screening pipeline

**Status: work in progress.** Built for my own job search, not yet a packaged tool.

- **Data pipeline** (steps 1–2): done.
- **Hard filter** (step 3): working; the design is settled.
- **Fit assessment** (step 4): redesigned and in testing. For now I run it by hand in Claude.ai, not yet in the pipeline.

## What problem it solves

- **Time.** Checking job boards every day and filtering for relevant roles by hand is slow and repetitive.
- **Applying into silence.** Applications went unanswered and I couldn't tell why. The LLM reads each
  posting from the hiring manager's side: what problem the role is hired to solve, and what candidate
  they picture for it. It then checks my experience against that, so I can see where my fit is real
  and where it isn't.

## What it does

1. **Sources** recent job postings from LinkedIn and Indeed, using job-title search terms for my
   target role families.
2. **Deduplicates and structures** them: skips roles already collected from the same platform in
   earlier runs (re-assessing only those whose posting changed), and converts each into a standard
   format for assessment.
3. **Hard filter** (LLM): knocks out roles that do not meet my hard requirements (e.g. location,
   contract, seniority).
4. **Fit assessment** (LLM): labels each remaining role Fit, Stretch or Not fit, based on my evidence
   for the skills it needs most.

## What it doesn't do

- Decide whether to apply. It sets review priority; I make the final call.
- Judge whether a role is attractive (industry, company, mission).
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

### Iteration 3 — LLMs apply clear rules well, but struggle with relative judgments

1. **Signal:** I couldn't see how the LLM reached its fit call, so I couldn't tell whether to trust
   it or how to improve my applications.
2. **Diagnosis:** the fit step asked for one overall judgment, which hid the reasoning behind it.
3. **Correction:** I broke the judgment into visible parts:
   - **What the hiring manager wants:** the problem the role is hired to solve, and the profile of
     the candidate they picture.
   - **The evidence:** the five most critical hard skills from the job description, and whether my
     CV has evidence for each. Coverage then decides Fit, Stretch or Not fit.
   - **The reasoning:** a clear trail for every call, so I can trace it, audit it, and see what to
     improve next time.
4. **Result:** the reasoning is now visible, and the hiring-manager view makes my own match much
   easier to judge. But the label stayed unreliable: unlike the knockouts, which were close to 100%
   precise on 145 postings, the model couldn't reliably tell a Fit from a Stretch, and the labels
   didn't noticeably reduce how many roles I review.
5. **Rule of thumb:** transparency shows you why the model decided, not whether the decision is
   right. Explicit rules can be automated; relative judgments stay with you.

### What's next

1. Define "not qualified" precisely, so the fit step can remove those roles as reliably as the hard
   filter does.
2. Align the search terms with my target role families, so out-of-scope roles are never collected.
3. Move the fit assessment from Claude into the pipeline.
4. Catch duplicates across LinkedIn and Indeed.
5. Record each application's outcome against the job the pipeline found.

## Repository notes

- `pipeline/` holds the code; `docs/data_pipeline/` and `docs/llm_eval/` hold the specs, policies and
  prompts it loads at runtime.
- References such as "ADR-017" point to the project's design decision log, which is kept private.
