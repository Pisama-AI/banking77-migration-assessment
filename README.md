# Banking77 model migration assessment

An example of the assessment [Pisama](https://pisama.ai) runs before a team switches AI models: keep the workflow fixed, run the current model and the candidates on the same cases, and show which answers improve, which regress and where the evidence is incomplete.

The workflow here is support intent classification on the public [Banking77](https://github.com/PolyAI-LDN/task-specific-datasets) dataset (77 labels). The current model is OpenAI o4-mini. Eleven candidate configurations ran on the same 500 primary cases and 30 separate challenge cases on 13 October 2026.

**Everything in the published report can be recomputed from this repository with one command.**

```
python verify.py
```

`verify.py` uses only the Python standard library. It rebuilds every metric from the per-case verdicts in `data/verdicts.csv` and checks each one against the table published with the report (`data/comparison.csv`). The current result is 381 values checked, 0 mismatches.

## Result

| Model | Correct of 500 | Fixed vs o4-mini | Newly wrong | Unreadable replies | USD per 1,000 cases | Eligible |
|---|---:|---:|---:|---:|---:|:---:|
| Gemini 3.8 Flash | 418 | 48 | 4 | 0 | 1.08 | yes |
| GPT-6.1 Sol | 414 | 49 | 9 | 0 | 1.32 | yes |
| **GPT-6 Luna (recommended)** | **405** | **43** | **12** | **0** | **0.08** | **yes** |
| Grok 4.7 | 402 | 34 | 6 | 0 | 3.23 | yes |
| GLM-5.3-Flash | 389 | 35 | 20 | 0 | 0.03 | yes |
| Claude Haiku 5.5 | 385 | 38 | 27 | 7 | unknown | no |
| Gemini 3.5 Flash Lite | 383 | 28 | 19 | 0 | 0.23 | yes |
| Nemotron 3.5 Lightning | 380 | 28 | 22 | 1 | unknown | no |
| Qwen3.7-Flash | 377 | 27 | 24 | 1 | 0.07 | yes |
| o4-mini (current) | 374 | | | 0 | 1.76 | yes |
| DeepSeek V4 Flash | 374 | 20 | 20 | 1 | unknown | no |
| Claude Sonnet 5.5 | 346 | 16 | 44 | 109 | 2.28 | no |

"Newly wrong" counts every case o4-mini got right and the candidate did not, including unreadable replies. The published table's `regressions` column counts only readable wrong labels; both are in `verify.py`.

GPT-6 Luna is recommended because it has the highest default preference score among eligible models (correctness 50%, consistency with current labels 20%, cost 20%, p95 time 10%). It costs about one twentieth of o4-mini per case and fixes 43 cases while breaking 12 (exact McNemar test, p < 0.001).

Read the recommendation with its limits:

- **Gemini 3.8 Flash has the most correct answers** (418, with 48 fixed and 4 newly wrong). It ranks lower only because the default weights value cost. A team that weights correctness higher gets a different pick; the four alternative weightings are in `data/comparison.json`.
- **GPT-6 Luna leads GLM-5.3-Flash by 0.39 preference points.** That gap does not establish that one is better than the other.
- **A preference score is not a confidence level.** It ranks models within this profile only.

## Limits

- **One workflow, in-sample.** The 500 primary cases are the evidence for this decision, not a held-out estimate of general model quality.
- **The current model can no longer be re-run.** OpenAI has returned `model_not_found` for o4-mini since 23 October 2026, so the o4-mini side of this comparison cannot be collected again.
- **Timing is descriptive.** Models were collected in separate windows with automatic cooldowns and manual pauses. Compare latency with care.
- **Some charges are unknown.** Three models have incomplete per-attempt pricing and are marked ineligible on that basis, not on quality.
- **Rate-limit handling differs from later runs.** In this run, HTTP 429 responses counted as provider errors.

## What is in this repository

| Path | Contents |
|---|---|
| `report/banking77-decision-report.pdf` | The decision report, identical to the copy on pisama.ai |
| `report/banking77-evidence-appendix.pdf` | Configurations, comparison limits, recovery, challenge results and examples |
| `data/verdicts.csv` | One row per case per model (6,360 rows): expected label, predicted label, status, correctness, cost, time |
| `data/comparison.csv`, `data/comparison.json` | The published metrics, including the four alternative weightings |
| `data/case-examples.csv`, `data/case-examples.json` | The curated paired examples shown in the report |
| `data/manifest.json` | SHA-256 identities of the published packet and its source files |
| `protocol/system_prompt.txt` | The exact prompt every model received (SHA-256 `92c32fa2...2c17`, as recorded in the protocol) |
| `protocol/configurations.json` | Each model's provider, reasoning setting and token caps, plus the label set |
| `protocol/request_body_template.json` | The request shape sent through OpenRouter |
| `verify.py` | Recomputes the published numbers from the verdicts |

The verdict file carries no message text or model replies. The 55 curated examples in `data/case-examples.*` include the message and each model's visible answer, as already published with the report. Each `case_id` of the form `banking77:test:N` is row `N` (zero-based, header excluded) of the Banking77 `test.csv`, SHA-256 `d12d6e3b...b474d`. Hidden reasoning is never included.

## Reproducing a run

To run a candidate yourself, send each case's text as the user message with `protocol/system_prompt.txt` as the system message, using the model, provider pin, reasoning setting and token cap in `protocol/configurations.json`. A reply is correct only when it parses as `{"intent": "<label>"}` and the label exactly matches the dataset label. Hosted models change over time, so a new run may not match these numbers exactly.

## License

Code is MIT (see `LICENSE`). The data files are derived from Banking77 by PolyAI, licensed [CC BY 4.0](https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE), and are released under the same license.
