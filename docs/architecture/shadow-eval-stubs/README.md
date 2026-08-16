# Shadow eval stubs (v0)

Illustrative JSON / Markdown examples for [shadow-evaluation.md](../shadow-evaluation.md) and [shadow-silence-evaluation.md](../shadow-silence-evaluation.md).  
Field names match the architecture instrumentation sections. Not runtime fixtures until SE* land typed models.

| File | Schema |
| --- | --- |
| `user_action.v0.json` | `UserAction` |
| `attention_candidate.v0.json` | `ShadowAttentionCandidate` |
| `suppressed_notification.v0.json` | `SuppressedNotificationAudit` (SE02 would-notify) |
| `suppression_decision.v0.json` | Frozen `SUPPRESS` decision snapshot (SE04) |
| `weekly_review.v0.json` | Weekly review JSON artefact (`reviews/YYYY-Www.json`) |
| `weekly_review.stub.md` | Human companion Markdown twin (SE03) |

Privacy: transformed `subject_ref` only — no raw emails, Notes bodies, or `PrivatePerson` fields.
