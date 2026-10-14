# Experimental 980-cycle witness

This archive rebuilds **980 cycles / 1,449 scratch words** from source and a selected timing assignment. It contains no saved physical instruction stream or scratch-address table.

From the repository root:

```sh
python experiments/archive/research/followup_980/reproduce.py
python experiments/archive/research/followup_980/reproduce.py --verify --seeds 100
```

The second command checks 100 full-width seeds, five asymmetric patterns, engine capacities and non-output memory against the unchanged frozen reference. The builder independently checks semantic operation/lane coverage and dependencies, allocates fresh scratch, rejects allocations above 1,536 words before lowering, and charges the final pause.

`verification.json` records the broader completed gates, including all nine frozen submission tests, supplementary shapes, legacy performance ceilings, corruption controls and isolated generation with runtime/oracle access blocked.

## Provenance and limits

- `config.json` selects the previously verified A graph.
- `timing_assignment.json` records semantic operation keys, native engines, lanes and issue cycles from one successful exact query.
- `timed.py` rebuilds the logical graph and allocates it. It does not consume old physical instructions or addresses.
- `source_manifest.json` hashes this archive's files, excluding itself.
- `problem.py` and the frozen verifier remain in their existing repository locations.

This is **selected-timing replay, not automatic production discovery**. The timing assignment is an experimental artifact, not a production scheduling policy. Production integration needs a separate decision and deterministic configuration/schedule discovery.

See [results](../followup_research_results.md) and [receipt](../followup_research_receipt.json). The instruction digest is:

```text
759f3ecb37854396b68e7503101cc1a4158fa804693d70c41297a1b3fe30302d
```
