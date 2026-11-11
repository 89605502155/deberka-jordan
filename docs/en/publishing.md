# Publishing

The package is published to PyPI from a version tag by `.github/workflows/publish.yml`,
through PyPI trusted publishing: no API token is stored in the repository.

1. Update the version in `pyproject.toml`, add the entry to `CHANGELOG.md` and
   update `CITATION.cff`.
2. Check locally: `uv run ruff check . && uv run mypy && uv run pytest && uv build`.
3. Tag and push: `git tag v0.1.0 && git push origin v0.1.0`.
4. The workflow runs `uv build` and `uv publish --trusted-publishing always`.

Configure the trusted publisher once on PyPI for the repository
`89605502155/deberka-jordan`, workflow `publish.yml`, environment `pypi`.
