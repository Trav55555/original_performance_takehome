# Trace viewer

[Home](../../README.md) · [Verification and diagnostic tools](../../docs/verification.md)

This directory contains the existing trace-viewing helper and its HTML asset, relocated from the root. It does not generate traces or compile a kernel.

With an existing `trace.json` in the repository root, run from that root:

```sh
python tools/trace/watch_trace.py
```

The helper opens `http://localhost:8000`. Click **Open Perfetto** to view the trace. Trace generation remains separate work and can require an expensive kernel build.

The HTML asset resolves relative to `watch_trace.py`. The trace and its modification time still resolve from the process's working directory, preserving the previous behavior. To inspect a trace in another directory, start the helper by its absolute path while working in that directory.

| Endpoint | Content |
|---|---|
| `/` | Bundled `watch_trace.html` |
| `/trace.json` | The current working directory's trace |
| `/mtime` | That trace's modification time |
| `/perfetto...` | The existing proxy to the external Perfetto UI |

The helper retains its original development-server behavior, including binding port 8000 on all interfaces. Do not expose it as a public service. The page opens `https://ui.perfetto.dev` and passes the trace buffer to that browser window; review sensitive trace contents before using it.

The relocation checks exercise local HTML, trace, timestamp and missing-file responses. They do not validate external Perfetto availability, browser rendering or the old proxy's JavaScript substitutions.
