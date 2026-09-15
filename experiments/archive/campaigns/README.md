# Preserved research campaigns

[Experiment index](../../README.md) · [Prototype archive](../README.md) · [Evidence method](../../../docs/reference/evidence-and-experiments.md)

This collection preserves four selected campaign groups from temporary workspaces. It contains 336 archive members and 12 unchanged report, protocol and receipt copies. The four compressed bundles total about 11.3 MiB. Production discovery does not use them.

## What can be reproduced

| Campaign | Captured result | Availability |
|---|---|---|
| [Final-hash ordering report](finalhash-order/records/report.md) | F08 reached 979 cycles with 1463 declared scratch words | **Saved-program replay verified.** Sources, four graphs, candidate artifacts and original checks are preserved. Complete search rediscovery is unverified. |
| [Mathematical models report](mathematical-models/records/report.md) | Five-arm screen; best 981 cycles | Workspace preserved, including available finalist artifacts. Reexecution unverified. |
| [Model combinations report](mathematical-models-mix/records/report.md) | Favorable interactions did not yield a new cycle winner | Workspace preserved, including available candidate artifacts. Reexecution unverified. |
| [Slope/select report](slope-select/records/report.md) | Sixteen candidates; best 981 cycles / 1473 words | Workspace preserved, including available candidate artifacts. Reexecution unverified. |

Replay means executing a saved physical program, not discovering it from source. None of these bundles is labeled a fully reproduced experiment campaign. The separate [979 production promotion](../../promotion_979_results.md) established automatic source-only discovery under its own gates.

## Verify without restarting experiments

From the repository root, run:

```sh
python experiments/archive/campaigns/verify.py
python experiments/archive/campaigns/test_verify.py
python experiments/archive/campaigns/verify.py --replay-finalhash
```

These commands need only the Python standard library. Leave assertions enabled for replay. The verifier checks each bundle hash, member path, member size and member hash, plus the loose record copies. It reads archived files without extracting them. The small tests reject corrupted archives, member hashes, records and unsafe paths.

The optional replay loads only the hash-pinned frozen simulator and saved F08 program. It checks engine issue capacities, outputs, non-output memory preservation and 979 complete cycles on three seeded full-width inputs and one asymmetric pattern. A changed hash constant must fail with an output mismatch. It does not rebuild lifetimes, allocate scratch again, run the complete historical test matrix or validate arbitrary starting indices. The scratch figure is the preserved allocation record, not a new allocation measurement.

The [capture verification receipt](verification.json) records these checks and the fresh-directory portability check. No search, solver query or cold production build ran during capture. Historical experiment drivers are not supported entry points for this archive. Their budgets remain closed.

## Contents and provenance

Each campaign has a `workspace.tar.gz`, a `manifest.json` and loose `records/` files. The manifests identify every captured member by original absolute path, size and SHA-256 digest. Tar metadata uses fixed timestamps and no owner names; the captured file bytes are unchanged. Python bytecode was omitted.

| Campaign | Manifest | Original protocol | Original receipt |
|---|---|---|---|
| Final-hash ordering | [Manifest](finalhash-order/manifest.json) | [Protocol](finalhash-order/records/protocol.md) | [Receipt](finalhash-order/records/receipt.json) |
| Mathematical models | [Manifest](mathematical-models/manifest.json) | [Protocol](mathematical-models/records/protocol.md) | [Receipt](mathematical-models/records/receipt.json) |
| Model combinations | [Manifest](mathematical-models-mix/manifest.json) | [Protocol](mathematical-models-mix/records/protocol.md) | [Receipt](mathematical-models-mix/records/receipt.json) |
| Slope/select | [Manifest](slope-select/manifest.json) | [Protocol](slope-select/records/protocol.md) | [Receipt](slope-select/records/receipt.json) |

The four bundles contain their complete available workspace files except bytecode, plus a copy of the frozen simulator. Existing dependency snapshots inside `original/` are included. Available does not mean complete: some candidates had no physical artifact, and captured drivers still reference other temporary directories and former repository revisions. Those external dependency chains have not been closed or replayed.

Raw records retain their original paths, links, source guards and creation-time publication status. Some links inside them therefore refer to the old location. Use this index for navigation. Do not rewrite historical hashes to match today's compiler. The source paths in a manifest explain provenance; neither verification command reads those paths.

Integrity checks detect changes relative to the captured manifests. They do not authenticate the historical claims independently or prove that every dependency was captured. Original local records and unrelated untracked research remain untouched outside this collection.
