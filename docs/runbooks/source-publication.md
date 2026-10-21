# Packaging and source publication

## Evaluator links

- [Application and tests on main](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/main)
- [Repository](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone)
- [Verified application/test revision](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/277e44b4009410742027bea92654b8e5fdb54d63)
- [Test evidence at that revision](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/blob/277e44b4009410742027bea92654b8e5fdb54d63/evidence/task-01/step-04-tests.md)

The repository is public. Anonymous HTTP access to `main`, selected source files,
and JUnit evidence was verified on 2026-10-21. After approval, Step 1.5 was merged
and pushed, and GitHub's default branch was changed from
`task-01/step-01-scaffold` to `main`. The original Step 1.5 evidence preserves the
repository state observed before that approved default-branch change.

## Clean packaging verification

Run from the repository root using uv and Python 3.14:

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
./scripts/test.sh
uv build
```

Validate **built artifacts**, not just the editable development install. In a
dedicated Bash session:

```sh
repo="$PWD"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

uv export --locked --no-dev --no-emit-project --no-header --no-annotate \
  --output-file "$scratch/runtime-requirements.txt" >/dev/null

for kind in wheel sdist; do
  uv venv --python 3.14 "$scratch/$kind"
  uv pip sync --python "$scratch/$kind/bin/python" --require-hashes \
    "$scratch/runtime-requirements.txt"
  if [ "$kind" = wheel ]; then
    artifact="$repo/dist/finsecure_pay-0.1.0-py3-none-any.whl"
  else
    artifact="$repo/dist/finsecure_pay-0.1.0.tar.gz"
  fi
  uv pip install --python "$scratch/$kind/bin/python" --no-deps "$artifact"
  uv pip check --python "$scratch/$kind/bin/python"
done
```

This creates two fresh environments with hash-checked runtime dependencies from
`uv.lock`. Installing the source archive invokes the isolated packaging backend;
its declared version range is not fully pinned by the runtime lockfile. Update the
artifact filenames if the project version changes.

Run the installed application **outside the checkout**, still in that dedicated
shell, so source files cannot mask missing package files:

```sh
cd "$scratch"
"$scratch/wheel/bin/python" -I -m uvicorn finsecure_pay.main:create_app \
  --factory --host 127.0.0.1 --port 8001
```

From another terminal, use the requests in the
[API contract](../api-contract.md), replacing port 8000 with 8001. Verify:

- Health: HTTP 200 with `{"status":"healthy"}`.
- Valid transaction: HTTP 200 with `valid: true`.
- Zero amount: HTTP 200 with `AMOUNT_NOT_POSITIVE`.
- Numeric rather than string amount: HTTP 422 with safe error metadata.

Stop the server with Ctrl-C, repeat using `$scratch/sdist/bin/python`, then exit
the dedicated shell to remove only its temporary directory. The recorded automated
verification used inherited loopback sockets on OS-assigned ports, not fixed 8001.

## Publication workflow

- Review and commit each step on its dedicated branch; merge only after approval.
- Confirm the remote URL and intended publication scope before pushing.
- Push approved branches without force-pushing or rewriting remote history.
- Compare remote branch hashes with local commits and check evaluator access without
  relying on the developer's authenticated GitHub session.
- Keep local instructions, credentials, environments, raw reports, and built
  archives out of Git. Commit only selected sanitized evidence.
- Public source publication does not deploy the API or publish a container image.

See [Step 1.5 evidence](../../evidence/task-01/step-05-source-publication.md) for
actual results, artifact hashes, and verification limits.
