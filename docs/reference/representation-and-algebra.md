# Representation and algebra

[Wiki](README.md) · [Memory and lookups](memory-and-lookups.md) · [Scheduling](scheduling-and-allocation.md)

All identities below use wrapping unsigned 32-bit arithmetic unless stated otherwise. Expression equivalence establishes eligibility, not a cycle saving. Check the complete emitted computation after scheduling and allocation.

## SIMD and affine fusion

**Production, established during the January work.** Eight-lane arithmetic processes independent walkers together. Multiple active groups expose enough independent instructions to use the available engines. SIMD alone does not turn an irregular gather into one contiguous vector load.

An affine hash stage of the form

```text
(x + a) + (x << k) = x * (1 + 2^k) + a
```

can use one vector `multiply_add`. This applies to hash stages 0, 2 and 4. It does not justify replacing XOR with addition or assuming an equivalent integer instruction exists on another target.

See the [January progression](../performance-progression.md#4294--about-2905-improve-manually-packed-bundles) and [current emitter](../../kernel_compiler.py).

## Mirrored indices and XOR encoding

**Production, introduced during the 1303 → 1113 retry.** Let `C = 0xB55A4F09`, the hash's terminal XOR constant:

```text
v = actual_value XOR C
q = 3*2^depth - 2 - original_index
q_next = 2*q + (v & 1)
gather_address = 3*2^depth + 5 - q
```

Keeping values encoded avoids repeatedly converting the full hash result. Encoding cached node words with the same constant cancels the two XORs:

```text
(actual_value XOR C) XOR (node XOR C) = actual_value XOR node
```

Because `C` is odd, encoding reverses the low branch bit. The mirrored index convention absorbs that reversal. Raw gathered nodes still need the appropriate decode/mix; final values must be decoded before storage. The address formula includes this benchmark's memory layout and is not a generic tree API.

At root wrap, `q` becomes 1. At initial entry, folding the root mix uses the same cancellation. The retained root-folding combination saved operations and reached 1084, although an earlier variant saved no cycles.

Sources: [retry](../../experiments/retry_results.md), [root folding](../../experiments/domain_sweep_results.md), `_build_ir` in [the compiler](../../kernel_compiler.py).

## Perfect-tree geometry

**Production assumption, not data compression.** `2047 = 2^11 - 1` describes a perfect tree with 11 levels. From root starts, depth and wrap are known from the round number, regardless of branch choices. Level boundaries and lookup sizes are powers of two.

Reset-on-overflow is not masking. An out-of-range child index 2049 must reset to 0; `2049 & 2047` gives 1. Tree values are arbitrary words, so the shape supplies no universal compression of their contents.

One-based indices append a branch bit during descent. Mirrored indices and retained history exploit that structure without changing traversal semantics. Non-root starts require separate reasoning and are not established by the current verification.

## Branch predicate reuse and projection

**Reuse is production; extra projection variants were experimental.** If the index update is `q_next = 2*q + bit`, its low bit is already `bit`. Reusing that predicate removed 192 vector operations in the historical 1113 → 1107 step. Private storage was necessary; sharing across round-tile boundaries caused a rejected incorrect variant.

For the encoded final XOR-shift result:

```text
(u XOR (u >> 16)) & 1 = (u & 1) XOR ((u >> 16) & 1)
```

Ignoring the upper contribution fails at `u = 65536`. Computing only branch parity can expose an earlier path, but the full hash value is still needed for subsequent work and final output. Projection and carry-aware radix variants did not improve complete execution in the declared mathematical-model screen.

Source: [predicate reuse](../../experiments/cross_domain_results.md). Projection evidence is cataloged under local mathematical research in [search and research](search-and-research.md#local-only-records).

## Fuse two middle hash stages

**Production, integrated in the 1052 compiler.** Given:

```text
B = 33*X + C2
Y = (B + C3) XOR (B << 9)
```

rewrite the two arms as:

```text
Y = (33*X + C2 + C3) XOR (16896*X + (C2 << 9))
```

The arms are independent multiply-adds. This is cross-stage fusion, distinct from the single-stage affine fusion above. The useful rewrite was audited in an external implementation and reimplemented locally. Its individual prototype improvement and its combined cache/selector improvement are different measurements.

Sources: [fork audit](../../experiments/github_1063_audit.md), [isolated ports](../../experiments/technique_port_results.md), [promotion](../../experiments/technique_promotion_results.md).

## Reassociate the final XOR

**Production, selectively used in the 979 result.**

```text
(u XOR (u >> 16)) XOR C = (u XOR C) XOR (u >> 16)
```

The constant XOR and shift can run on independent branches. The implemented variant also changes the shift's preferred engine. A matched retimed comparison shortened the final gather-to-store path from 11 to 10 cycles. Native timing spans looked worse before backward/forward scheduling; the rewrite was not a standalone greedy-schedule win.

The final-hash pilot checked zero and the 32 basis words for two affine GF(2) expressions, and rejected a wrong shifted-input mutation. That argument is specific to affine bit expressions. It does not prove equivalence of arbitrary arithmetic with carries. Full-kernel execution checked emitter wiring, dependencies and memory behavior.

Sources: [979 promotion](../../experiments/promotion_979_results.md), [local pilot provenance](search-and-research.md#local-only-records).

## Other exact algebra that did not establish a faster kernel

The local mathematical work examined odd-multiplier inverses modulo `2^32`, right-XOR-shift inverses, a 2-adic inverse for the mixed addition/XOR stage, and radix decompositions with explicit carries. A cheap inverse is not a cheap forward hash. Word-affine arithmetic is not generally affine over GF(2), because carries couple bits.

Walsh-Hadamard division shortcuts fail over wrapping words where division by two is not invertible. Boolean Mobius differences remain invertible, but do not make arbitrary tables sparse. Low-rank/tensor representations need an actual rank restriction; the table shape alone does not supply one.

Treat these as algebraic tools and counterexamples, not performance bounds. See [lookup forms](memory-and-lookups.md#tensor-and-mobius-lookup-forms) and the [research catalog](search-and-research.md) for the tested variants and source limits.
