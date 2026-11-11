# Публикация

Пакет публикуется в PyPI вручную. В репозитории нет автоматической публикации,
API-токен в репозитории не хранится.

1. Укажите версию в `pyproject.toml` и `CITATION.cff` и добавьте запись в `CHANGELOG.md`.
   `deberka_jordan.__version__` читается из метаданных установленного пакета.
2. Проверьте локально: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
3. Соберите пакет: `uv build`. Колёса и архив исходников попадут в `dist/`.
4. Загрузите: `uv publish --token <токен PyPI>`. Токен ваш; в репозиторий его не добавляйте.
5. Поставьте тег на коммит релиза и отправьте его:
   `git tag v0.0.1` и `git push origin main --tags`.

Репозиторий: `https://github.com/89605502155/deberka-jordan`.
