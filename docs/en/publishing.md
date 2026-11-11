# Publishing

The package is published to PyPI by hand. There is no automated publishing
workflow in the repository, and no API token is stored in it.

1. Set the version in `pyproject.toml` and `CITATION.cff`, and add the entry to `CHANGELOG.md`.
   `deberka_jordan.__version__` is read from the installed package metadata.
2. Check locally: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
3. Build: `uv build`. It writes the wheel and the source distribution to `dist/`.
4. Upload: `uv publish --token <PyPI token>`. The token is your own; do not commit it.
5. Tag the release commit and push the tag:
   `git tag v0.0.1` and `git push origin main --tags`.

The repository is `https://github.com/89605502155/deberka-jordan`.
