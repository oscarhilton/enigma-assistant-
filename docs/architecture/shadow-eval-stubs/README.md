# Shadow eval stubs (v0)

Illustrative JSON / Markdown examples for [shadow-evaluation.md](../shadow-evaluation.md).  
Field names match the architecture instrumentation section. Not runtime fixtures until SE01–SE03 land typed models.

| File | Schema |
| --- | --- |
| `user_action.v0.json` | `UserAction` |
| `attention_candidate.v0.json` | `ShadowAttentionCandidate` |
| `suppressed_notification.v0.json` | `SuppressedNotificationAudit` |
| `weekly_review.stub.md` | Human companion to `reviews/YYYY-Www.json` (SE03) |

Privacy: transformed `subject_ref` only — no raw emails, Notes bodies, or `PrivatePerson` fields.
