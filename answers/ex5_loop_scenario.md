# Ex5 — Edinburgh research loop scenario

## Your answer

Since there are no specific instructions for this task, I will provide general reflections on the process.

It is surprisingly difficult to make the AI to call a specific sequence of tools. Extensive rewrites are required to make it work, including prompt engineering as well as the suggested hard guardrail.

Consider sess_5f24ebaf53c4, where we use the default run.py with all the implemented tools. The planner goes completely off-plan, inventing data and not using the tools properly. This is due to lack of direction for it as well as the executor.

Contrast it with sess_fda414fa6e1b, which is using the properly layed out run.py. Its results are clean and following the laid out path.

As a side note, it is not very clear why the formula for calculating costs adds the minimal sum to the total.

## Citations

- evidence/ex5/sess_5f24ebaf53c4
- evidence/ex5/sess_fda414fa6e1b