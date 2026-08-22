# Learned Workflows

Webcmd's actual site memory, verified endpoints, field maps, and
fixtures live under `~/.webcmd/` (site memory) and `~/.webcmd/clis/`
(authored adapter source) on whichever machine runs the live demo —
not in this repo directory, and not portable by copying files, since
some of it is tied to the local webcmd daemon/session state.

This folder exists as a place to commit **exported** artifacts you
want version-controlled for the demo/judges, e.g.:

```
webcmd site sample add vtu/results ./workflows/vtu-results-sample-response.json
```

See `/adapter/webcmd-cli-reference.md` (one level up, from the earlier
webcmd-vtu-agent scaffold) for the real inspected CLI surface — copy
the relevant adapter-authoring commands over here once Phase 2 starts.
