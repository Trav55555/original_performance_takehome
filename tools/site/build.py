#!/usr/bin/env python3
"""Render site/index.html: the template plus six inline SVG figures.

Figures 3 and 5 are computed from the emitted program. The page text describes
the 975-cycle program, so the program's digest must match EXPECTED_DIGEST.

    python tools/site/build.py --program program.json   # saved {"instrs": ...}
    python tools/site/build.py                          # cold build, ~15 min
"""

import argparse
import hashlib
import json
import math
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from problem import SLOT_LIMITS

EXPECTED_DIGEST = "861864c85979d75993f9e07187b6bde2035b9d4085b9f6d2acb81622ad67138b"
WINDOW = 25

INK = "#1b1f24"
MUTED = "#5b6470"
GRID = "#d8dde3"
ACCENT = "#0b3d91"  # NASA blue
RED = "#fc3d21"
ENGINE_COLOR = {
    "alu": "#0b3d91",
    "valu": "#2f6fb2",
    "load": "#5b9bd5",
    "store": "#9db9d6",
    "flow": "#fc3d21",
}
LIMITS = {e: n for e, n in SLOT_LIMITS.items() if e != "debug"}


def load_program(path):
    if path:
        instrs = json.loads(Path(path).read_text())["instrs"]
    else:
        from perf_takehome import KernelBuilder

        builder = KernelBuilder()
        builder.build_kernel(10, 2047, 256, 16)
        instrs = builder.instrs
    program = [{e: [tuple(s) for s in slots] for e, slots in b.items()} for b in instrs]
    digest = hashlib.sha256(json.dumps(program).encode()).hexdigest()
    assert digest == EXPECTED_DIGEST, (
        f"page text describes {EXPECTED_DIGEST[:8]}, got {digest[:8]}"
    )
    return program


def slot_use(program):
    cycles = len(program)
    totals = {e: sum(len(b.get(e, [])) for b in program) for e in LIMITS}
    windows = {e: [] for e in LIMITS}
    for start in range(0, cycles, WINDOW):
        chunk = program[start : start + WINDOW]
        for e in LIMITS:
            used = sum(len(b.get(e, [])) for b in chunk)
            windows[e].append(round(used / (LIMITS[e] * len(chunk)), 2))
    return cycles, totals, windows


def svg(w, h, body, label):
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, sans-serif">'
        f"{body}</svg>"
    )


def text(x, y, s, size=12, fill=INK, anchor="start", weight="normal"):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{escape(s)}</text>'
    )


def history():
    pts = [
        ("Scalar baseline", 147734),
        ("SIMD, batching, pipelining", 4294),
        ("Manual packing, hash fusion", 2905),
        ("List scheduling, caches", 1303),
        ("Index encoding, private temps", 1113),
        ("Cached depth-4 lookups", 1082),
        ("SSA graph, late allocation", 1076),
        ("Fused hash, lookahead", 1052),
        ("Earlier startup gathers", 1041),
        ("Cache neighborhood search", 981),
        ("Late arithmetic selectors", 980),
        ("Backward/forward scheduling", 979),
        ("Gather ancestry first", 975),
    ]
    w, h, left, right, top, bottom = 860, 380, 70, 30, 20, 120
    lo, hi = math.log10(800), math.log10(200000)
    y = lambda v: top + (hi - math.log10(v)) / (hi - lo) * (h - top - bottom)
    step = (w - left - right) / (len(pts) - 1)
    x = lambda i: left + i * step
    body = []
    for v in (1000, 10000, 100000):
        body.append(
            f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}"/>'
        )
        body.append(text(left - 8, y(v) + 4, f"{v:,}", 11, MUTED, "end"))
    body.append(
        f'<line x1="{left}" x2="{w - right}" y1="{y(967):.1f}" y2="{y(967):.1f}" stroke="{RED}" stroke-dasharray="4 3"/>'
    )
    body.append(
        text(w - right, y(967) + 14, "967-cycle VALU resource bound", 11, RED, "end")
    )
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(pts)
    )
    body.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>')
    for i, (name, v) in enumerate(pts):
        body.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="{ACCENT}"/>')
        if i in (0, 1, 3, len(pts) - 1):
            body.append(
                text(
                    x(i) + (6 if i < len(pts) - 1 else -6),
                    y(v) - 8,
                    f"{v:,}",
                    12,
                    INK,
                    "start" if i < len(pts) - 1 else "end",
                    "bold",
                )
            )
        cx, cy = x(i), h - bottom + 14
        body.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="10.5" fill="{MUTED}" text-anchor="end" transform="rotate(-40 {cx:.1f} {cy:.1f})">{escape(name)}</text>'
        )
    body.append(
        text(
            16, top + (h - top - bottom) / 2, "Cycles (log scale)", 11, MUTED, "middle"
        ).replace(
            "<text ",
            f'<text transform="rotate(-90 16 {top + (h - top - bottom) / 2:.1f})" ',
            1,
        )
    )
    return svg(w, h, "".join(body), "Cycle count by development stage, log scale")


def machine(cycles, totals):
    w, h = 860, 300
    body = []
    rows = [
        ("alu", "ALU (scalar)"),
        ("valu", "VALU (8-lane vector)"),
        ("load", "Load"),
        ("store", "Store"),
        ("flow", "Flow"),
    ]
    cell, gap, x0, y0 = 30, 4, 190, 30
    body.append(text(x0, 18, "Slots issued per cycle", 11, MUTED))
    body.append(text(650, 18, "Use over the 975-cycle program", 11, MUTED))
    for r, (e, name) in enumerate(rows):
        yy = y0 + r * 50
        body.append(text(x0 - 12, yy + 20, name, 13, INK, "end", "bold"))
        for k in range(LIMITS[e]):
            body.append(
                f'<rect x="{x0 + k * (cell + gap)}" y="{yy}" width="{cell}" height="{cell}" rx="3" fill="{ENGINE_COLOR[e]}"/>'
            )
        frac = totals[e] / (LIMITS[e] * cycles)
        bx, bw = 650, 160
        body.append(
            f'<rect x="{bx}" y="{yy + 6}" width="{bw}" height="18" fill="#eef1f4" rx="2"/>'
        )
        body.append(
            f'<rect x="{bx}" y="{yy + 6}" width="{bw * frac:.1f}" height="18" fill="{ENGINE_COLOR[e]}" rx="2"/>'
        )
        body.append(text(bx + bw + 8, yy + 20, f"{frac:.1%}", 12, INK))
    return svg(
        w,
        h,
        "".join(body),
        "Engine slots per cycle and their use in the 975-cycle program",
    )


def utilization(cycles, windows):
    engines = ["alu", "valu", "load", "flow", "store"]
    n = len(windows["alu"])
    cw, ch, x0, y0 = 19, 26, 70, 10
    w, h = x0 + n * cw + 20, y0 + len(engines) * (ch + 4) + 40
    body = []
    for r, e in enumerate(engines):
        yy = y0 + r * (ch + 4)
        body.append(text(x0 - 8, yy + 17, e.upper(), 12, INK, "end", "bold"))
        for i, v in enumerate(windows[e]):
            body.append(
                f'<rect x="{x0 + i * cw}" y="{yy}" width="{cw - 2}" height="{ch}" fill="{ENGINE_COLOR[e]}" fill-opacity="{max(v, 0.04):.2f}">'
                f"<title>{e.upper()} cycles {i * WINDOW}-{min(i * WINDOW + WINDOW, cycles) - 1}: {v:.0%}</title></rect>"
            )
    by = y0 + len(engines) * (ch + 4) + 16
    for c in (0, 250, 500, 750, cycles):
        xx = x0 + c / WINDOW * cw
        body.append(text(xx, by, str(c), 11, MUTED, "middle"))
    body.append(text(x0 + n * cw / 2, by + 16, "Cycle", 11, MUTED, "middle"))
    return svg(w, h, "".join(body), "Slot use per engine in 25-cycle windows")


def box(x, y, w, h, label, sub=None, fill="#ffffff", stroke=ACCENT, color=INK):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
    if sub:
        s += text(x + w / 2, y + h / 2 - 3, label, 13, color, "middle", "bold")
        s += text(
            x + w / 2,
            y + h / 2 + 14,
            sub,
            11,
            MUTED if color == INK else color,
            "middle",
        )
    else:
        s += text(x + w / 2, y + h / 2 + 5, label, 13, color, "middle", "bold")
    return s


def arrow(x1, y1, x2, y2, color=MUTED):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5" marker-end="url(#arrow)"/>'


MARKER = (
    f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>'
)


def round_flow():
    w, h = 860, 170
    b = [MARKER]
    xs = [10, 180, 320, 520, 690]
    labels = [
        ("Node value", "gather, or select from cache"),
        ("XOR", "value ^ node"),
        ("Hash", "6 add/xor/shift stages"),
        ("Next index", "2i+1 if even, else 2i+2"),
        ("Wrap", "past a leaf: back to root"),
    ]
    bw = [150, 120, 180, 150, 160]
    for i, ((l, s), x) in enumerate(zip(labels, xs)):
        b.append(box(x, 40, bw[i], 60, l, s))
        if i:
            b.append(arrow(xs[i - 1] + bw[i - 1], 70, x - 2, 70))
    b.append(
        f'<path d="M770,100 C770,150 85,150 85,104" fill="none" stroke="{RED}" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
    )
    b.append(text(430, 160, "16 rounds for each of 256 inputs", 12, RED, "middle"))
    b.append(text(10, 24, "One round for one input", 11, MUTED))
    return svg(w, h, "".join(b), "Work for one input in one round")


def compiler():
    w, h = 860, 330
    b = [MARKER]
    b.append(box(20, 30, 180, 64, "Plan", "cache sites + selectors"))
    b.append(box(250, 30, 160, 64, "Build graph", "SSA IR"))
    b.append(box(460, 30, 170, 64, "Schedule", "backward, then forward"))
    b.append(box(680, 30, 160, 64, "Allocate", "fresh scratch"))
    b.append(arrow(200, 62, 248, 62))
    b.append(arrow(410, 62, 458, 62))
    b.append(arrow(630, 62, 678, 62))
    b.append(box(460, 130, 170, 64, "3 priority orders", "native, tail, startup"))
    b.append(
        f'<line x1="545" y1="94" x2="545" y2="128" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="3 3"/>'
    )
    b.append(box(680, 130, 160, 64, "Final-hash rewrites", "on the 2 last blocks"))
    b.append(arrow(760, 94, 760, 128))
    b.append(
        box(
            680,
            240,
            160,
            64,
            "Gate: <= 975?",
            "else fail, never slower",
            fill="#fff4f2",
            stroke=RED,
        )
    )
    b.append(arrow(760, 194, 760, 238))
    b.append(
        box(
            250,
            240,
            380,
            64,
            "Emit bundles",
            "975 cycles, 1,469 scratch words",
            fill=ACCENT,
            stroke=ACCENT,
            color="#ffffff",
        )
    )
    b.append(arrow(680, 272, 632, 272))
    b.append(
        f'<path d="M458,162 L110,162 L110,98" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
    )
    b.append(text(130, 154, "score by schedule length, try next plan", 11, MUTED))
    b.append(text(130, 182, "1,963 of 4,096 candidates scored", 11, MUTED))
    return svg(w, h, "".join(b), "Compiler pipeline")


def proof():
    w, h = 860, 250
    b = [MARKER]
    steps = [
        ("Concrete gate", "simulator vs reference"),
        ("Symbolic run", "every bundle, all 1,536 scratch words"),
        ("Cut points", "each proposed match proved by Z3"),
        ("Final checks", "values, other memory, bounds"),
    ]
    for i, (l, s) in enumerate(steps):
        x = 10 + i * 215
        b.append(box(x, 40, 195, 70, l, s))
        if i:
            b.append(arrow(x - 20, 75, x - 2, 75))
    b.append(
        box(
            10,
            160,
            410,
            60,
            "Mutants all fail",
            "constant, select, store, slot, scratch, rare-input",
            fill="#fff4f2",
            stroke=RED,
        )
    )
    b.append(
        box(
            440,
            160,
            410,
            60,
            "975 program proved",
            "256 inputs x 16 rounds, about 1 minute",
            fill=ACCENT,
            stroke=ACCENT,
            color="#ffffff",
        )
    )
    b.append(
        text(10, 24, "scripts/verify_equivalence.py uses no compiler code", 11, MUTED)
    )
    return svg(w, h, "".join(b), "Equivalence proof stages")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--program", help="JSON with key 'instrs'; default builds via KernelBuilder"
    )
    args = ap.parse_args()
    cycles, totals, windows = slot_use(load_program(args.program))
    figures = {
        "history": history(),
        "machine": machine(cycles, totals),
        "round": round_flow(),
        "compiler": compiler(),
        "utilization": utilization(cycles, windows),
        "proof": proof(),
    }
    page = (Path(__file__).parent / "template.html").read_text()
    for name, figure in figures.items():
        page = page.replace("{{" + name + "}}", figure)
    assert "{{" not in page, "unfilled placeholder"
    (ROOT / "site" / "index.html").write_text(page)


if __name__ == "__main__":
    main()
