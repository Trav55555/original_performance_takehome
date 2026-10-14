"""Reproduce the experimental 980-cycle witness, not a production compiler choice."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.append(str(ROOT))
from timed import build

EXPECTED = "759f3ecb37854396b68e7503101cc1a4158fa804693d70c41297a1b3fe30302d"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--seeds", type=int, default=100)
    args = parser.parse_args()
    assert args.seeds > 0
    cfg = json.loads((HERE / "config.json").read_text())
    assignment = json.loads((HERE / "timing_assignment.json").read_text())
    k = build(cfg, assignment)[-1]
    digest = hashlib.sha256(json.dumps(k.instrs).encode()).hexdigest()
    assert (len(k.instrs), k.scratch_ptr, digest) == (980, 1449, EXPECTED)
    receipt = {"cycles": 980, "scratch": 1449, "digest": digest,
               "provenance": "source-plus-selected-timing-assignment",
               "automatic_production_discovery": False}
    if args.verify:
        sys.path.append(str(ROOT / "tests"))
        from frozen_problem import (Machine, Tree, Input, build_mem_image,
                                    reference_kernel2, SLOT_LIMITS)
        assert all(len(ss) <= SLOT_LIMITS[e] for b in k.instrs for e, ss in b.items())
        patterns = [lambda i: 0, lambda i: 0xFFFFFFFF,
                    lambda i: 0xAAAAAAAA if i % 2 else 0x55555555,
                    lambda i: 1 << (i % 32),
                    lambda i: (i * 0x9E3779B9) & 0xFFFFFFFF]
        cases = [(seed, None) for seed in range(args.seeds)] + [(30000+i, i) for i in range(5)]
        for seed, pattern in cases:
            rng = random.Random(seed)
            nodes = [rng.getrandbits(32) if pattern is None else patterns[pattern](i)
                     for i in range(2047)]
            values = [rng.getrandbits(32) if pattern is None else patterns[(pattern+1) % 5](i)
                      for i in range(256)]
            memory = build_mem_image(Tree(10, nodes), Input([0]*256, values, 16))
            out = memory[6]
            machine = Machine(memory, k.instrs, k.debug_info(), n_cores=1)
            machine.enable_debug = False
            machine.enable_pause = True
            machine.run()
            for expected in reference_kernel2(memory.copy()):
                pass
            assert machine.mem[out:out+256] == expected[out:out+256], (seed, pattern)
            assert machine.mem[:out] == memory[:out]
            assert machine.mem[out+256:] == memory[out+256:]
            assert len(machine.mem) == len(memory) and machine.cycle == 980
        receipt.update(full_width_seeds=args.seeds, asymmetric_patterns=5,
                       non_output_memory_preserved=True)
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
