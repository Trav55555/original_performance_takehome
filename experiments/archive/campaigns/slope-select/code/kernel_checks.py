"""Independent read-before-write lane-owner verification."""

from collections import Counter
from problem import SCRATCH_SIZE, SLOT_LIMITS


def lane_identity(ir, logical, addresses):
    """Independent lane-owner simulation; reads occur before cycle-end writes."""
    owner = {}
    for cycle, bundle in enumerate(logical):
        usage, writes = Counter(), {}
        for i, engine, first, count in bundle:
            op = ir.ops[i]
            usage[engine] += count
            partial = op.kind == "gather" or (op.kind == "binary" and engine == "alu")
            reads = []
            if partial:
                for value, offset in op.args:
                    reads.extend(
                        (value, offset + lane) for lane in range(first, first + count)
                    )
            elif not (op.kind == "const_choice" and engine == "load"):
                sizes = (
                    [1, 8]
                    if op.kind == "vstore"
                    else [1]
                    if op.kind in ("vload", "broadcast", "const_choice")
                    else [8] * len(op.args)
                )
                for (value, offset), width in zip(op.args, sizes):
                    reads.extend((value, offset + lane) for lane in range(width))
            for value, lane in reads:
                address = addresses[value] + lane
                assert 0 <= address < SCRATCH_SIZE
                assert owner.get(address) == (value, lane), (
                    "lane identity",
                    cycle,
                    i,
                    address,
                )
            if op.dst is not None:
                lanes = (
                    range(first, first + count) if partial else range(ir.widths[op.dst])
                )
                for lane in lanes:
                    address = addresses[op.dst] + lane
                    assert 0 <= address < SCRATCH_SIZE
                    assert address not in writes, ("duplicate write", cycle, address)
                    writes[address] = (op.dst, lane)
        assert all(n <= SLOT_LIMITS[engine] for engine, n in usage.items())
        owner.update(writes)
