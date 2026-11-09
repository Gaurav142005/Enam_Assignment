"""Model routing. One place decides which model does which job, so cost is visible and tunable.

  cheap()  → bulk work: classify filings, extract numbers from result PDFs, pull guidance quotes
  strong() → reasoning: promised-vs-delivered, bull/bear, network "why this person" explanations

Every call is cached by hash(model, prompt, inputs); a document is processed once, ever.
Provider + model names come from env (FINN_CHEAP_MODEL / FINN_STRONG_MODEL) — wired in the Pull phase.
"""
