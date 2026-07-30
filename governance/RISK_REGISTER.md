# Residual Risk Register

| ID | Risk | Control/evidence | Residual | Owner/action |
|---|---|---|---|---|
| R-01 | Same-OS-user access to files or loopback API | Loopback, trusted host, mutation token, deployment ACL guidance | Medium | IT must isolate the service identity/data ACL before pilot |
| R-02 | Malformed media exploits parser/runtime | Signature + ffprobe validation, fixed args, timeouts | Medium-high | Use approved patched FFmpeg; consider OS sandbox before production |
| R-03 | Model/runtime attempts network access | Model path must exist; no download code or cloud API | Low | Egress deny remains recommended defense in depth |
| R-04 | Runaway compute or storage | Size/duration/job/retention budgets, single worker, killable timeout | Low-medium | Monitor disk/CPU during pilot |
| R-05 | Transcript error changes meaning | Time-linked source review; no confidence or accuracy claim | High for consequential use | Human verification is mandatory; build domain evaluation before expansion |
| R-06 | Rule-based analysis is mistaken for judgment | Method chip and explicit limitations; deterministic only | Medium | Training and UI copy review in pilot |
| R-07 | Export loses control/provenance | JSON evidence package; user-triggered export only | Medium | Destination DLP/records policy is external to this app |
| R-08 | Deletion misses backups/exports/indexes | Job-tree deletion and retention test | Medium | Exclude data directory from unauthorized backup/indexing; document external copies |
| R-09 | Misconfigured retention/model/storage | Readiness check, env validation, versioned defaults/docs | Medium | IT-owned configuration baseline and review required |
| R-10 | Edited demonstration is mistaken for measured performance or broad product proof | Synthetic-data badges, visible 12×/16× processing labels, raw timing records, claim boundaries, retained raw captures | Low-medium | Reviewers must use measured evidence and pilot gates, not demo runtime, for decisions |
| R-11 | Folder batch escapes its approved root, overwrites files, or leaves uncontrolled output copies | Relative-root containment, link/junction and traversal blocks, non-recursive scan, count/byte budgets, collision checks, no-overwrite writes, explicit cleanup copy boundary | Medium | IT/records owners must approve `STS_BATCH_ROOT`, output ACL/DLP, retention, and operator training |
| R-12 | Output filesystem failure strands work or leaves a partial transcript | Observed monitor futures, deterministic terminal failures, same-directory temporary files, fsync, atomic hard-link publication, failure-injection tests | Low-medium | IT must qualify hard-link support, free space, ACLs, and recovery behavior on the approved batch workspace |
| R-13 | Architecture definitions or evaluation claims drift from implementation | Versioned L1-L3 definitions, AST dependency/symbol checks, named regression traces, rendered-diagram gate, revisioned JSON report | Low | Maintainer must update architecture, eval catalog, tests, risk/backlog, and evidence in the same material change |
