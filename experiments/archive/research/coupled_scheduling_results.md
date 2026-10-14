# Coupled scheduling: a flow-tail certificate

## Decision

Retain the verified **981-cycle / 1,465-word** candidate. Coupled engine reassignment did not find a faster program. The useful result is a simpler explanation: the current graph cannot beat 981 while keeping the prefix through cycle 615 unchanged.

There are 354 remaining flow selections, and every one requires at least eleven following cycles. At one flow selection per cycle:

```text
T >= 616 + 354 + 11 = 981
```

This certificate uses true data dependencies, not scratch-reuse ordering. It does not establish global optimality: moving work into cycle 615 or earlier, changing flow work, or shortening the dependency tail can escape it.

## Coupled model

The previous [mathematical investigation](math_bounds_results.md) left 980-cycle feasibility open beyond a fixed 64-cycle suffix. This screen moved the boundary earlier and allowed both directions of binary engine reassignment.

The reproduced program became 41,761 atoms with 4,518 vector-binary groups and 278,459 physical-version dependency edges. Each eligible binary group can:

- issue as one VALU instruction, tying all eight lane times; or
- issue as eight scalar ALU instructions, with separate lane times.

The model enforces per-cycle engine capacities, producer timing, physical read/write versions, precommit read semantics, and terminal pause placement. It permits a mode change only when all eight original lanes are inside the movable region. Other instructions and physical addresses stay fixed. The encoded physical-version order is a restriction, not a claim about every legal allocation or lifetime ordering.

## Four planned trials

All trials targeted 980 cycles. Construction time is separate from solver time.

| Movable suffix | First movable cycle | Engine choices | Eligible groups | Build time | Solver time | Direct result |
|---|---:|---|---:|---:|---:|---|
| 128 cycles | 853 | Fixed | 575 | 1.80 s | 0.55 s | UNSAT |
| 128 cycles | 853 | Flexible | 575 | 2.63 s | 8.59 s | UNSAT |
| 256 cycles | 725 | Fixed | 1,177 | 4.12 s | 30.04 s | Unknown: timeout |
| 256 cycles | 725 | Flexible | 1,177 | 5.60 s | 2.14 s | UNSAT |

The flexible 256-cycle model contains the fixed-mode case as a subset. Its UNSAT result therefore also rules out that subset, although the direct fixed-mode solver result remains recorded as a timeout. The independent flow certificate below reaches the same conclusion without that inference.

Each solver had a thirty-second cap, with a 120-second child wall limit and 2 GiB address-space limit. No memory or child wall limit was reached. No additional optimization region or target was searched.

## Verification controls

Two executable toys required opposite reassignment directions to improve from four cycles to three. Fixed modes returned UNSAT for the shorter target. Flexible modes produced legal programs, which ran on the frozen machine and produced all expected register values.

Additional checks passed:

- the original 981 assignment satisfied the same encoding and executed correctly;
- reconstruction preserved the instruction/lane multiset, capacities, prefix, hazards and mode coupling;
- wrong mode assignments failed specifically on capacity checks;
- a corrupted dependency assignment was rejected;
- 36 frozen-machine cases checked all four binary opcodes used by the benchmark, with input/output aliasing and varied bit patterns.

No new benchmark candidate reached SAT, so no new faster-kernel verification or promotion claim is made.

## The capacity contradiction

For the flexible physical-version model, both regions force forty loads into cycles 937 through 955: nineteen cycles with only 38 load slots. Other cuts also overflow flow and weighted arithmetic capacity.

A diagnostic then removed 168,050 scratch-reuse ordering edges, retaining 110,409 true data edges. This was a relaxation analysis, not another optimization solve or an executable program. The load overload disappeared, but flow still did not fit:

| Fixed prefix ends at | Remaining flow selections | Latest allowable issue for target 980 | Available slots |
|---:|---:|---:|---:|
| 852 | 117 | 968 | 116 |
| 724 | 245 | 968 | 244 |

Every selected flow instruction has a true dependency tail of at least twelve cycles including its own issue. To finish in 980 cycles, it must therefore issue by cycle 968.

Looking at the existing program explains both cuts. Its last flow hole before the drain is cycle 615. Flow is then occupied in every cycle from 616 through 969: 354 consecutive selections. With the prefix through 615 fixed, those selections cannot fit by 968. At least one must issue at 969 or later, and its remaining computation requires completion at cycle count 981 or later.

The original program is a matching 981 witness. Thus this is a tight bound for the stated prefix, retained flow work and data dependencies, even after relaxing scratch reuse and permitting eligible binary engine reassignment. It is stronger than merely failing to find a better schedule.

## A separate single-rewrite follow-up

The four scheduling trials were closed before this follow-up. The flow-tail proof suggested an exact final-round reassociation:

```text
Original:
    s = u >> 16
    v = u XOR s
    output = v XOR C

Reassociated:
    s = u >> 16
    a = u XOR C
    output = a XOR s
```

More simply, the identity is `(u XOR (u >> 16)) XOR C = (u XOR C) XOR (u >> 16)`, with `C = 0xB55A4F09`. In the new form, the shift and constant XOR can run in parallel. Only the final round changes; earlier rounds keep their encoded representation, and the final raw value is stored directly.

One bounded Z3 query proved the identity. The follow-up compiled exactly one control and one candidate, with no parameter search. Both passed full-width frozen smoke execution. The logical operation counts were identical.

| Program | Cycles | Scratch | Last data-flow instruction | Following cycles |
|---|---:|---:|---:|---:|
| Original control | 981 | 1,465 | 969 | 11 |
| Final-XOR reassociation | 985 | 1,465 | 974 | 10 |

The intended tail reduction occurred, but the unchanged scheduling heuristic placed the last flow instruction five cycles later. Runtime regressed by four cycles. The new physical stream also used one more VALU instruction and eight fewer ALU instructions. The candidate was rejected without claiming full-width-suite or compatibility verification beyond its smoke test.

This does not prove the identity useless. It shows that shortening a dependency chain is not enough if the resulting schedule loses more time elsewhere. Joint scheduling of that changed graph remains untested.

## Next work and artifacts

For the unchanged graph, do not repeat smaller suffix searches: they cannot overcome the flow-count certificate. A useful next region must include cycle 615 or earlier; a 384-cycle suffix would start at 597. Alternatively, jointly reschedule a graph with less flow work or a shorter tail. Allocation changes alone do not remove the demonstrated flow obstruction under the fixed prefix.

Artifacts are in `/tmp/perf-coupled-scheduling.8I8SNA/`: model, controls, four case receipts, physical and true-data window checks, flow certificate, source hashes and decisions. The separate rewrite lives in `final_xor/`. A compact [receipt](coupled_scheduling_certificate.json) preserves the key results and scopes.

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-coupled-scheduling.8I8SNA/controls.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-coupled-scheduling.8I8SNA/driver.py 256 flex
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-coupled-scheduling.8I8SNA/verify_model.py
PYTHONDONTWRITEBYTECODE=1 /tmp/perf-five-arms/solver-env/bin/python /tmp/perf-coupled-scheduling.8I8SNA/flow_certificate.py
PYTHONDONTWRITEBYTECODE=1 python /tmp/perf-coupled-scheduling.8I8SNA/final_xor/screen.py
```

Production remains at commit `5691617`, with a 1,041-cycle default. All production sources, tests, simulator and prior reports were preserved. No commit, push, cloud job or external submission occurred.
