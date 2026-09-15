#!/usr/bin/env python3
"""Verify captured evidence without running searches; optionally replay saved F08."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import sys
import tarfile
import types

CAMPAIGNS = (
    "finalhash-order",
    "mathematical-models",
    "mathematical-models-mix",
    "slope-select",
)
LIMIT = 256 * 1024 * 1024
FROZEN_SHA = "fadb0f0858e2259f5759077a5544b9906dad3ceee80d37b4f0aa77da730c93c9"
PROGRAM_SHA = "d71b7cc458e45d9ae400faf7cbd525bafa531d5c23d6f10d84f3706d60143848"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    require(
        name and not path.is_absolute() and ".." not in path.parts, "Unsafe member path"
    )
    require("\\" not in name and path.as_posix() == name, "Noncanonical member path")
    return name


def check_bytes(data, entry, name):
    require(len(data) == entry["bytes"], f"Size mismatch: {name}")
    require(sha(data) == entry["sha256"], f"SHA-256 mismatch: {name}")


def verify_campaign(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    require(manifest["schema"] == 1, "Unknown manifest schema")
    archive = folder / safe_name(manifest["archive"]["path"])
    require(archive.stat().st_size <= LIMIT, "Archive too large")
    check_bytes(archive.read_bytes(), manifest["archive"], archive.name)
    expected = manifest["members"]
    require(0 < len(expected) <= 2000, "Unexpected member count")
    require(
        sum(row["bytes"] for row in expected.values()) <= LIMIT,
        "Expanded archive too large",
    )
    seen = set()
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            name = safe_name(member.name)
            require(
                member.isfile() and name in expected and name not in seen,
                "Unexpected archive member",
            )
            require(
                member.size == expected[name]["bytes"] and member.size <= LIMIT,
                "Unexpected member size",
            )
            with stream.extractfile(member) as data:
                check_bytes(data.read(member.size + 1), expected[name], name)
            seen.add(name)
    require(seen == set(expected), "Missing archive member")
    for name, entry in manifest["records"].items():
        path = folder / safe_name(name)
        require(path.stat().st_size <= LIMIT, "Record too large")
        check_bytes(path.read_bytes(), entry, name)
    return {
        "campaign": folder.name,
        "status": "integrity-passed",
        "members": len(seen),
        "compressed_bytes": manifest["archive"]["bytes"],
    }


def member_bytes(folder, name):
    # Called only after the complete archive has passed manifest verification.
    with tarfile.open(folder / "workspace.tar.gz", "r:gz") as archive:
        with archive.extractfile(name) as file:
            return file.read(LIMIT + 1)


def replay_finalhash(folder):
    require(__debug__, "Replay requires Python assertions enabled")
    source = member_bytes(folder, "reference/frozen_problem.py")
    require(sha(source) == FROZEN_SHA, "Frozen simulator differs from pinned oracle")
    program = json.loads(member_bytes(folder, "workspace/artifacts/F08/program.json"))
    require(sha(json.dumps(program).encode()) == PROGRAM_SHA, "Unexpected F08 program")
    row = json.loads(member_bytes(folder, "workspace/artifacts/F08/result.json"))
    require(row["scratch"] == 1463 and row["cycles"] == 979, "Unexpected F08 cost")
    # Execute only this hash-pinned frozen simulator, never captured experiment code.
    module = types.ModuleType("archived_frozen_problem")
    module.__file__ = "archive:reference/frozen_problem.py"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    for bundle in program:
        require(
            set(bundle) <= {"alu", "valu", "load", "store", "flow"}, "Unexpected engine"
        )
        for engine, slots in bundle.items():
            require(len(slots) <= module.SLOT_LIMITS[engine], "Issue capacity exceeded")

    def execute(instructions, nodes, values):
        tree = module.Tree(10, nodes)
        inp = module.Input([0] * 256, values, 16)
        memory = module.build_mem_image(tree, inp)
        expected = memory.copy()
        for _ in module.reference_kernel2(expected):
            pass
        machine = module.Machine(memory.copy(), instructions, module.DebugInfo({}))
        machine.enable_debug = False
        machine.run()
        start = memory[6]
        stop = start + 256
        require(machine.mem[start:stop] == expected[start:stop], "Output mismatch")
        require(
            machine.mem[:start] == memory[:start]
            and machine.mem[stop:] == memory[stop:],
            "Non-output memory changed",
        )
        require(machine.cycle == 979, "Replay cycle mismatch")

    cases = []
    for seed in range(3):
        rng = random.Random(seed)
        cases.append(
            (
                [rng.getrandbits(32) for _ in range(2047)],
                [rng.getrandbits(32) for _ in range(256)],
            )
        )
    cases.append(
        (
            [0xAAAAAAAA if i % 2 else 0x55555555 for i in range(2047)],
            [(i * 0x9E3779B9) & 0xFFFFFFFF for i in range(256)],
        )
    )
    for nodes, values in cases:
        execute(program, nodes, values)
    mutant = json.loads(json.dumps(program))
    changed = False
    for bundle in mutant:
        for slot in bundle.get("load", []):
            if slot[0] == "const" and slot[2] == 0xB55A4F09:
                slot[2] ^= 2
                changed = True
                break
        if changed:
            break
    require(changed, "Mutation constant not found")
    try:
        execute(mutant, *cases[0])
    except ValueError as error:
        require(str(error) == "Output mismatch", "Mutation failed for the wrong reason")
    else:
        raise ValueError("Corrupt program accepted")
    return {
        "status": "saved-program-replay-passed",
        "cycles": 979,
        "declared_scratch": 1463,
        "cases": len(cases),
        "corrupt_constant_rejected": True,
        "limit": "Selected program only; no rediscovery, fresh allocation or full historical promotion rerun.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--replay-finalhash", action="store_true")
    args = parser.parse_args()
    result = {"archives": [verify_campaign(args.root / name) for name in CAMPAIGNS]}
    if args.replay_finalhash:
        result["finalhash_replay"] = replay_finalhash(args.root / "finalhash-order")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
