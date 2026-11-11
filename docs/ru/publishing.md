# Публикация

Пакет публикуется в PyPI по тегу версии рабочим процессом `.github/workflows/publish.yml`
через доверенную публикацию PyPI (trusted publishing): API-токен в репозитории не хранится.

1. Обновите версию в `pyproject.toml`, добавьте запись в `CHANGELOG.md` и обновите `CITATION.cff`.
2. Проверьте локально: `uv run ruff check . && uv run mypy && uv run pytest && uv build`.
3. Поставьте тег и отправьте его: `git tag v0.1.0 && git push origin v0.1.0`.
4. Рабочий процесс выполняет `uv build` и `uv publish --trusted-publishing always`.

Доверенного издателя нужно один раз настроить на PyPI для репозитория
`89605502155/deberka-jordan`, рабочего процесса `publish.yml`, окружения `pypi`.
