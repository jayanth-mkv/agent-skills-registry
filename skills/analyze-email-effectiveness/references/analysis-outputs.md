# Analysis output patterns

Use the smallest format that resolves the user’s decision. Lead with the verdict, evidence strength and limits—not a checklist dump.

## Universal finding

```markdown
### [Finding]
- Layer/scope:
- Evidence and source/time:
- Impact on the message’s job:
- Recommendation:
- Verification:
- Confidence:
```

Keep observed facts separate from causal inference. Use `N/A`/`unknown` rather than scoring absent evidence.

## Single-email audit

```markdown
## Verdict
[What it is, where it belongs, strongest asset, biggest conflict, confidence.]

## Position
- Family:
- Lifecycle/awareness:
- Primary job:
- Intended state change:

## Evidence inspected
- [artifact stage, source, date/hash if useful]

## What works
- [artifact evidence -> why it helps]

## Priority findings
1. [universal finding format]

## Scorecard
| Dimension | Score/N/A | Evidence |

## Unknowns
- [claim that cannot be made -> exact evidence needed]
```

## Sequence audit

```markdown
| Step | Eligibility/trigger | Prior state | Job | CTA/outcome | Branch | Exit/handoff | Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

Then show missing states, repeated jobs, cadence/cross-channel collisions, suppression precedence and a corrected state-transition map.

## Variant or observational comparison

```markdown
## Decision
[Which better serves the job, or why evidence is insufficient.]

| Criterion | A | B | Evidence |
| --- | --- | --- | --- |

## Comparability/confounds
- [audience, timing, receiver, offer, destination, sample or measurement]

## Recommended test
- Hypothesis:
- One controlled difference:
- Assignment unit:
- Primary metric/window:
- Guardrails:
- Minimum worthwhile effect:
```

## Performance diagnosis

```markdown
## Funnel
| Stage | Count | Rate/denominator | Change vs baseline | Data quality |

## Breakdown
| Provider/stream/cohort | Observation | Materiality |

## Most plausible causes
1. [Cause]
   - Supporting:
   - Contradicting/unknown:
   - Discriminating next check:

## Decision
[Change audience, operation, message, offer, destination, measurement—or wait.]
```

## Domain and authentication audit

```markdown
## Verdict
[Configuration posture only; explicitly state whether real-message results exist.]

## Identities
| Role | Value | Source | Exact/claimed/trusted |

## Findings
| Severity | Control/name | Evidence | Impact | Action |

## DMARC interpretation
- RFC 9989 policy source/Organizational Domain/effective policy:
- Legacy/public-suffix comparison:
- Candidate alignment:
- Actual trusted authentication result:

## Collection
- Time/resolver/mode:
- TTL/AD/error notes:
- Selectors/IPs covered and missing:

## Cannot conclude
- Inbox placement, reputation, consent and real-message pass unless separately evidenced.
```

Never title this result “spam score” or “deliverability score.”

## Placement/reputation diagnosis

```markdown
## Verdict
[Provider/stream/time; rejection vs placement; evidence confidence.]

## Evidence ladder
| Layer | Provider/identity/window | Observation | Strength |

## Change point
- Onset:
- Concurrent list/infrastructure/message/product changes:

## Causes and next checks
1. [cause -> supports -> contradicts -> discriminating check]

## Containment
- [safe reversible action]

## Recovery verification
- [same receiver evidence, owner, window; no fixed guarantee]
```

## DMARC aggregate-report analysis

```markdown
## Scope
- Reports/receivers/window/messages represented:
- Duplicates/errors:
- Authorized-source inventory date:

## Alignment
| Source/IP | Messages | Header From | DKIM d=/s= | SPF domain | Aligned | Classification |

## Largest failures
- [weighted row -> owner/unknown -> remediation evidence]

## Limits
- Participating receivers/sample only; not placement, complaints or maliciousness proof.
```

## Consent/compliance audit

```markdown
## Scope
- Sender/promoted entities:
- Recipient jurisdictions/status:
- Recipient-visible classification:
- Primary sources/date:

## Evidence
| Requirement | Artifact/record | Status | Confidence | Missing proof |

## Suppression flow
[collection -> eligibility -> send -> withdrawal/complaint -> propagation]

## High-risk gaps
- [gap -> containment -> owner]

## Counsel decision
- [fact-sensitive issue requiring qualified review]
```

## Rewrite

Show diagnosis first:

```markdown
Strategic change:
[one sentence]

Subject:
Preview:
From name: [if relevant]

[Complete body]

Primary CTA:

Preserved facts/requirements:
- [...]

Assumptions/placeholders:
- [...]

What changed:
- [change -> reason]

Test hypothesis:
- [only if a valid test is useful]
```

## Executive remediation plan

```markdown
| Priority | Layer | Action | Owner | Risk/rollback | Verification | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
```

Order containment before optimization, and reversible/diagnostic changes before broad changes when impact is uncertain.
