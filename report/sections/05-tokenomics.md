### What one run costs

Every model call in this project goes through a single ledger
(`backend/usage.py`) that records tokens at the moment the call returns.
Nothing here is estimated or reconstructed after the fact.

A typical assessment is **{{f['typical']['calls']}} model calls**: one
transcription, four criterion specialists in parallel, one adjudicator, one
drill generator.

| | per run |
|---|---|
| Input tokens | {{"{:,}".format(f['typical']['prompt_tokens'])}} |
| of which served from cache | {{"{:,} ({:.1%})".format(f['typical']['cached_tokens'], f['typical']['cache_hit_rate'])}} |
| Output tokens | {{"{:,}".format(f['typical']['completion_tokens'])}} |
| **Cost** | **{{"${:.4f}".format(f['typical']['cost_usd'])}}** |

### At scale

Assuming four compositions per student per month:

| | monthly cost |
|---|---|
| 1 student | {{"${:.3f}".format(f['typical']['cost_usd'] * 4)}} |
| 1 class of 30 | {{"${:.2f}".format(f['typical']['cost_usd'] * 4 * 30)}} |
| 100 students | {{"${:.2f}".format(f['typical']['cost_usd'] * 4 * 100)}} |
| 10,000 students | {{"${:,.0f}".format(f['typical']['cost_usd'] * 4 * 10000)}} |

A district with 10,000 language students could run this for roughly the cost
of one classroom projector per year. The binding constraint on adoption is
not money; it is trust in the output, which is why most of this report is
about validation rather than cost.

### Where the price comes from

No per-token rate sheet is published for `gpt-6-luna`, and none appears
anywhere on the course site. The rate used is derived from this account's own
Portkey analytics: **$29.72 across 34.1M tokens over 90 days = $0.872 per 1M
tokens, blended**.

!! A blended rate cannot price the three token classes separately. Every
dollar figure above is therefore sound on total volume but understates the
benefit of caching, since a cached token is billed here at the same rate as
a fresh one. Caching is reported below in tokens, which were measured
directly and need no price at all.

### Cutting cost: prompt caching

The ACTFL descriptors are large, identical on every call, and prepended to
every prompt — about 3,400 tokens of rubric before anything student-specific.
`backend/rubric.py` therefore builds that block as a function taking no
arguments, so it is physically awkward to interpolate anything variable into
the cached region by accident.

Measured effect: cache hit rate on input rises from **44.9% on a cold run to
{{"{:.1%}".format(f['typical']['cache_hit_rate'])}} once warm**. Roughly
three-quarters of all input tokens are served from cache in steady state.

A note on terminology, because the Portkey dashboard and the API report
different things. Portkey's own cache is a *response* cache — an identical
request replays a stored answer, at 138 ms. The figures above are *prompt
prefix* caching reported by the provider in `prompt_tokens_details`: the
model still runs, but the shared prefix is discounted. The two are separate
mechanisms and this report never mixes their numbers.

### Cutting cost: the experiment that failed

The obvious further saving is to collapse the four criterion specialists into
one call that returns all four findings, paying the big cached prefix once
instead of four times. `scripts/compare_architectures.py` tests exactly that,
with transcription run once and shared so OCR variation cannot contaminate
the comparison.

| | four specialists | one combined call |
|---|---|---|
| Cost over {{f['arch']['n']}} samples | {{"${:.4f}".format(f['arch']['cost_a'])}} | {{"${:.4f}".format(f['arch']['cost_b'])}} |
| Saving | — | **{{"{:.0%}".format(f['arch']['saving'])}}** |
| Same final placement | — | {{f['arch']['same_placement']}}/{{f['arch']['n']}} |
| Individual criteria agreeing | — | {{f['arch']['criteria_agree']}}/{{f['arch']['criteria_total']}} |

The saving is real and so is its cost: collapsing the fan-out changes the
placement in {{f['arch']['n'] - f['arch']['same_placement']}} of
{{f['arch']['n']}} samples and disagrees on a third of individual criteria.
The combined call was also *slower* in wall-clock terms — 13.5 s against
4.7 s — because the four specialists run in parallel and the single call
cannot.

**Decision: the fan-out was kept.** Paying {{"${:.4f}".format(f['typical']['cost_usd'])}}
instead of about {{"${:.4f}".format(f['typical']['cost_usd'] * (1 - f['arch']['saving']))}}
per composition is not a meaningful cost at any realistic scale, and the
cheap version produces a different answer a third of the time.

### Reliability is a cost

One further observation from the ledgers. Agents occasionally return JSON
that fails schema validation; the client retries once with the validation
error attached. On one early run the drill generator appears **twice** in the
same ledger for this reason, roughly doubling that agent's cost for that run.
Schema reliability is therefore a cost variable, not only a correctness one,
and it is visible in the per-agent table in the appendix.
