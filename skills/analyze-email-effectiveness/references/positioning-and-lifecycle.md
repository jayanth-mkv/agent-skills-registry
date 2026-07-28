# Positioning, lifecycle, and sequence analysis

Use this reference to determine where a message belongs, the state change it owns, and whether the surrounding journey advances coherently.

## Message-family map

Classify from the recipient-visible job, not the internal campaign name.

| Family | Trigger/expectation | Primary job | Common failure |
| --- | --- | --- | --- |
| Authentication/security | User request or detected risk | Verify, protect or recover access | Exposed secret, vague risk, promotion, unsafe link |
| Confirmation/receipt | Completed transaction or request | Confirm facts and next step | Essential details buried, confusing charge/status |
| Account/service | Billing, policy, outage or account event | Explain impact and required action | Legalistic copy, hidden deadline/support |
| Product notification | Relevant event or configured alert | Inform and route | Noise, no priority, missing preference control |
| Digest | Batched expected updates | Summarize and prioritize | Undifferentiated feed, no reason to return |
| Onboarding | New customer/user/subscriber | Establish expectation and first value | Feature dump, too many actions |
| Activation | Incomplete value event | Remove one blocker and advance | Calendar trigger ignores actual behavior |
| Education/nurture | Demonstrated interest, not ready | Build understanding and reduce doubt | Generic content or premature pitch |
| Editorial newsletter | Recurring subscription | Deliver promised standalone value | Every issue becomes an advertisement |
| Announcement | Material product/company change | Translate change into recipient impact | Company-centric news with no consequence |
| Promotion/launch | Known audience and offer | Motivate an appropriate decision | Weak value, hidden terms, false urgency |
| Browse/cart recovery | Recent incomplete intent | Restore context and reduce friction | Sensitive item exposure, repeated pressure |
| Event/webinar | Registration or relevant invitation | Register, prepare, attend or follow up | Time-zone ambiguity, stale CTA after event |
| Survey/feedback | Sufficient experience to answer | Gather useful input and close loop | Asking too early, biased question, no follow-up |
| Review/referral | Demonstrated success | Invite voluntary advocacy | Asked before success, coercive incentive |
| Renewal/dunning | Contract/payment milestone | Preserve service and resolve decision | Surprise deadline, unclear consequence |
| Retention/churn prevention | Observable risk or value gap | Restore value or remove friction | Generic discount after damage is done |
| Expansion | Proven customer value | Extend use/plan appropriately | Upsell before adoption or wrong stakeholder |
| Re-engagement | Inactivity with credible permission | Reconfirm interest or sunset | Endless sends, guilt, no exit |
| Win-back | Lapsed customer | Address lapse and restore fit | Discount without diagnosing why they left |
| Sales outreach | Specific plausible business fit | Start an honest conversation | Fabricated familiarity, unwanted scale |
| Recruiting | Relevant role/candidate fit | Start or advance candidate conversation | Generic blast, hidden employer/role |
| Fundraising/membership | Existing mission relationship or valid basis | Motivate support/renewal | Emotional manipulation, vague use of funds |
| Advocacy/community | Established participation | Invite contribution or sharing | Assumed endorsement, weak consent boundary |

Mixed messages inherit the expectations and stricter risks of each included purpose. A receipt dominated by an offer is not purely transactional; a welcome message that asks for setup is onboarding/activation.

## Lifecycle map

### Acquisition and awareness

Make the problem, desired outcome or relationship recognizable. Ask for the smallest reasonable commitment. Cold attention is not product awareness.

### Consideration

Help the recipient compare approaches. Use mechanism, proof, tradeoffs, use-case boundaries and objections. Do not repeat awareness copy with a stronger CTA.

### Activation

Move from signup/purchase to the first meaningful value event. Trigger from observed state, not elapsed time alone. Branch on the actual blocker.

### Conversion

Turn demonstrated relevance/value into a decision. Clarify offer, price/terms, risk, proof and next step without hiding conditions.

### Adoption and retention

Deepen realized value and prevent avoidable friction. Use milestones, underused capabilities, health/risk signals and service events with appropriate sensitivity.

### Expansion and advocacy

Establish success before asking for a larger plan, referral, review, case study or community contribution. Check stakeholder authority.

### Reactivation

Determine whether value and permission still exist. Use a bounded attempt and explicit sunset; nonresponse is not renewed interest.

### Service

Complete, confirm, protect or explain an existing relationship. Optimize clarity, accuracy, privacy and speed rather than persuasion.

## Awareness fit

- **Unaware:** make a real problem/outcome recognizable without manufacturing fear.
- **Problem-aware:** clarify consequence, priority and desired state.
- **Solution-aware:** explain approach, fit, tradeoffs and alternatives.
- **Product-aware:** provide differentiation, proof and objection handling.
- **Most-aware:** make the offer/action concrete and remove friction.

Do not assume a recipient moves one awareness stage per email. Use observed behavior and research.

## Define the state transition

Complete:

```text
For [specific eligible recipient] who currently [knowledge/belief/behavior],
this message is triggered by [observable event or rule]
and should cause [one recipient state change]
because [relevant promise, proof or service fact].
Success is [recipient-centered event], guarded by [harm metric].
```

If the sentence needs several state changes, split the message or sequence.

## Sequence map

For every step:

| Field | Question |
| --- | --- |
| Eligibility | Who can enter, and what evidence qualifies them? |
| Trigger | What observable event/state starts this step? |
| Prior state | What can this message safely assume? |
| Job | What single change should occur? |
| Argument | What new value/proof/reassurance does this step add? |
| CTA | What event represents progress? |
| Branch | What changes on action, conversion, reply, objection, inactivity or error? |
| Exit | When must the recipient stop receiving this sequence? |
| Suppression | Which consent, complaint, service or frequency rules override it? |
| Handoff | Does product, sales, support, success or another channel take over? |
| Measurement | What job metric and guardrail evaluate it? |

Render the journey:

```text
eligibility + trigger
-> current recipient state
-> message job
-> observed outcome
-> branch or wait
-> next state / handoff / exit
```

## Sequence defects

Flag:

- adjacent steps repeat the same argument or CTA;
- a later message assumes an action that was never observed;
- conversion/activation/reply occurs but queued messages continue;
- calendar timing substitutes for lifecycle behavior;
- onboarding sells before first value;
- re-engagement has no sunset;
- service and promotional streams collide;
- sales, product and marketing contact the same recipient without arbitration;
- event reminders ignore registration, attendance or time zone;
- renewal/dunning ignores payment or support dispute state;
- global complaint/unsubscribe suppression loses to local workflow state;
- frequency caps ignore other campaigns/brands/channels;
- an email exists only because a calendar slot exists.

## Timing and cadence

There is no universal best send time or cadence. Evaluate:

- trigger urgency and shelf life;
- recipient time zone and quiet hours;
- expected decision interval;
- content novelty and incremental value;
- cross-campaign pressure;
- receiver/list quality and complaint evidence;
- operational readiness of the destination/support team;
- sample size and seasonality.

For experiments, randomize within comparable eligibility windows rather than comparing unrelated weekdays or cohorts.

## Behavioral branches by family

### Onboarding/activation

Branch on completed milestone, blocker, role and product state. Exit on value event or explicit abandonment/suppression.

### Commerce/recovery

Branch on purchase, stock/price change, cart modification and service contact. Stop immediately after conversion; do not reveal sensitive browsing details in notifications.

### Event

Branch on registration, cancellation, attendance and recording availability. Convert calendar/time-zone facts reliably and retire expired CTAs.

### Renewal/dunning

Branch on successful payment, grace period, account owner and active dispute. Coordinate product banners/support to prevent contradictory instructions.

### Sales outreach

Branch on positive/negative reply, wrong person, referral, bounce and opt-out. A reply should exit automation and transfer ownership.

### Re-engagement

Branch on meaningful activity, explicit preference and silence. Define the final sunset before launch.

## Cross-channel evaluation

Check email against:

- in-product prompts and notification center;
- SMS/push/phone;
- sales/customer-success outreach;
- support incidents;
- paid retargeting;
- landing page/product state.

Use the channel best suited to urgency, sensitivity and action. Email should not repeat a more timely in-product fact without adding context or recoverability.

## Positioning verdict

```text
For [audience] at [lifecycle/awareness state],
the message should [one state change]
using [promise/proof/service fact].
The current message [supports/conflicts with] that role because [artifact evidence].
In the sequence it [advances/duplicates/skips/contradicts] [adjacent state].
```
