#!/usr/bin/env bash
# Установка git-хуков проекта.
#
# Использование:
#   ./scripts/install-hooks.sh
#
# После установки pre-commit хук будет запускать mypy перед каждым коммитом
# и блокировать его при ошибках типов.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
PRE_COMMIT="$HOOK_DIR/pre-commit"

if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "✘ Это не git-репозиторий: $REPO_ROOT"
    exit 1
fi

mkdir -p "$HOOK_DIR"

cat > "$PRE_COMMIT" << 'HOOK_EOF'
#!/usr/bin/env bash
# Pre-commit хук: запускает mypy в strict-режиме.
# Блокирует коммит при ошибках типов.
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> Проверка типов через mypy..."
if ! uv run mypy; then
    echo ""
    echo "✘ mypy нашел ошибки типов. Коммит отменен."
    echo "  Исправьте ошибки или используйте 'git commit --no-verify' для пропуска."
    exit 1
fi

echo "✓ mypy проверка пройдена"
HOOK_EOF

chmod +x "$PRE_COMMIT"

echo "✓ Git pre-commit хук установлен: $PRE_COMMIT"
echo "  Теперь mypy будет запускаться перед каждым коммитом."
