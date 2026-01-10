# Developer guide

## Prerequisites

- Python 3.10+
- [Hatch](https://hatch.pypa.io) (install with `pipx install hatch`)

## Common tasks

```bash
# start dev server
hatch run api

# run tests
hatch run test

# lint
hatch run lint

# type-check
hatch run typecheck
```

## Documentation

```bash
# live docs server
hatch run docs:serve

# build static site
hatch run docs:build
```

MkDocs sources live under `docs/`. Adjust navigation in `mkdocs.yml` when adding new pages.
