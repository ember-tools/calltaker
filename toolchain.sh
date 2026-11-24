#!/usr/bin/env bash
#
# Build and verification commands for this repository.
#
# Every command runs from the repository root regardless of the caller's working directory, and
# inside the nix environment of shell.nix via `direnv exec`, so Python, pipenv, ruff and node are
# the pinned versions.
#
# Usage: ./toolchain.sh <command> [args...]
#        ./toolchain.sh <group> <command> [args...]
#        ./toolchain.sh help

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$ROOT/frontend"

# Runs a command inside the project's direnv/nix environment, or directly when direnv is missing.
run() {
    if [ -f "$ROOT/.envrc" ] && command -v direnv >/dev/null 2>&1; then
        if [ -z "${DIRENV_APPROVED:-}" ]; then
            if ! direnv exec "$ROOT" true >/dev/null 2>&1; then
                echo "toolchain: this checkout's .envrc has not been approved. Approve it once with:" >&2
                echo "               direnv allow $ROOT" >&2
                exit 1
            fi
            DIRENV_APPROVED=1
        fi
        direnv exec "$ROOT" "$@"
    else
        "$@"
    fi
}

usage() {
    cat <<'EOF'
Usage: ./toolchain.sh <command> [args...]
       ./toolchain.sh <group> <command> [args...]

The first hyphen of a name also reads as a space, so `fe build` and `fe-build` are the same
command. `./toolchain.sh fe` lists what is in a group.

Frontend
  fe-install            npm install
  fe-install-clean      npm ci
  fe-dev                Vite dev server with the proxy to a local backend
  fe-typecheck          vue-tsc
  fe-test               vitest, once
  fe-test-watch         vitest, watching
  fe-bundle             Production build
  fe-lint [name] [args] Every linter of the registry in scripts/linters.mjs, failing when one does.
                        With a name only that one: eslint, duplication, browser-storage,
                        em-dash, comments
  fe-audit              All linters, non-gating; prints everything they find
  fe-eslint [args]      ESLint directly
  fe-build              Full verification: linters, type check, tests, build

Backend
  be-install            pipenv sync --dev
  be-dev                uvicorn with reload on port 8000
  be-lint               ruff check
  be-format             ruff format
  be-format-check       ruff format --check
  be-test               pytest
  be-test1 <expr>       pytest -k <expr>
  be-verify             Lint, format check and tests

Data
  data-abfrage          Check the question graph in daten/abfrage/ and print its size
  data-abfrage-uebernehmen [sna-tree.json]
                        Convert alarmzettel's interrogation graph into daten/abfrage/ (one-off)
  data-adressen         Load the Berlin address list into the data folder now
  data-adressen-stand   Show whether the address list is there, its size and age
  data-un [page.html]   Take the list of UN numbers from chemie.de into daten/gefahrstoffe/
  data-orte [extract.shp.zip]
                        Derive the named places of Berlin from OpenStreetMap into daten/orte/
  data-leitfragen       Derive the guidance questions for the medical situations into daten/leitfragen/

Docker
  docker-build          Build the production image from docker/app.Dockerfile
  docker-app            Start the development stack (compose.dev.yaml), always rebuilt
  docker-app-down       Stop the development stack
  docker-app-logs       Follow the development stack's logs
  docker-prod           Start the production stack (compose.prod.yaml)
  docker-prod-down      Stop the production stack

Whole repository
  verify                Everything CI runs
  format                Apply ruff format and the ESLint fixes
  help                  This text
EOF
}

fe() { cd "$FRONTEND"; }
be() { cd "$ROOT"; }

COMMAND_GROUPS=(fe be data docker)

is_group() {
    local candidate
    for candidate in "${COMMAND_GROUPS[@]}"; do
        [ "$1" = "$candidate" ] && return 0
    done
    return 1
}

# Lists a group's commands, read from the case arms below so the listing cannot drift.
list_group() {
    sed -n 's/^    \([a-z][a-z0-9|_-]*\)).*/\1/p' "$ROOT/toolchain.sh" |
        tr '|' '\n' | sed -n "s/^$1-//p"
}

if is_group "${1:-}"; then
    if [ $# -ge 2 ]; then
        set -- "$1-$2" "${@:3}"
    else
        echo "Commands in '$1':" >&2
        list_group "$1" | sed "s|^|  $1 |" >&2
        exit 2
    fi
fi

cmd="${1:-help}"
shift || true

case "$cmd" in
    fe-install)       fe; run npm install "$@" ;;
    fe-install-clean) fe; run npm ci "$@" ;;
    fe-dev)           fe; run npm run dev -- "$@" ;;
    fe-typecheck)     fe; run npx vue-tsc -b "$@" ;;
    fe-test)          fe; run npx vitest run "$@" ;;
    fe-test-watch)    fe; run npx vitest "$@" ;;
    fe-bundle)        fe; run npx vite build "$@" ;;
    fe-lint)          fe; run node scripts/lint.mjs "$@" ;;
    fe-audit)         fe; run node scripts/lint.mjs --audit ;;
    fe-eslint)        fe; run npx eslint "$@" ;;
    fe-build)
        "$ROOT/toolchain.sh" fe-lint
        "$ROOT/toolchain.sh" fe-typecheck
        "$ROOT/toolchain.sh" fe-test
        "$ROOT/toolchain.sh" fe-bundle
        ;;

    be-install)       be; run pipenv sync --dev "$@" ;;
    be-dev)           be; run pipenv run uvicorn main:app --app-dir src --reload --port 8000 "$@" ;;
    be-lint)          be; run ruff check "$@" ;;
    be-format)        be; run ruff format "$@" ;;
    be-format-check)  be; run ruff format --check "$@" ;;
    be-test)          be; run pipenv run pytest "$@" ;;
    be-test1)
        [ $# -ge 1 ] || { echo "be-test1 needs a pytest -k expression" >&2; exit 2; }
        be; run pipenv run pytest -k "$@"
        ;;
    be-verify)
        "$ROOT/toolchain.sh" be-lint
        "$ROOT/toolchain.sh" be-format-check
        "$ROOT/toolchain.sh" be-test
        ;;

    data-abfrage)     be; run env PYTHONPATH=src pipenv run python tools/abfrage_pruefen.py "$@" ;;
    data-adressen)       be; run env PYTHONPATH=src pipenv run python tools/adressen_laden.py laden ;;
    data-adressen-stand) be; run env PYTHONPATH=src pipenv run python tools/adressen_laden.py stand ;;
    data-orte)           be; run pipenv run python tools/orte_uebernehmen.py "$@" ;;
    data-leitfragen)     be; run env PYTHONPATH=src pipenv run python tools/leitfragen_situationen.py ;;
    data-un)             be; run pipenv run python tools/un_nummern_uebernehmen.py "$@" ;;
    data-abfrage-uebernehmen)
        be; run pipenv run python tools/abfrage_uebernehmen.py "$@"
        ;;

    docker-build)     be; run docker build . -f docker/app.Dockerfile "$@" ;;
    docker-app)       cd "$ROOT/docker"; run docker compose -f compose.dev.yaml up -d --build --renew-anon-volumes "$@" ;;
    docker-app-down)  cd "$ROOT/docker"; run docker compose -f compose.dev.yaml down "$@" ;;
    docker-app-logs)  cd "$ROOT/docker"; run docker compose -f compose.dev.yaml logs -f "$@" ;;
    docker-prod)      cd "$ROOT/docker"; run docker compose -f compose.prod.yaml up -d --build "$@" ;;
    docker-prod-down) cd "$ROOT/docker"; run docker compose -f compose.prod.yaml down "$@" ;;

    verify)
        "$ROOT/toolchain.sh" be-verify
        "$ROOT/toolchain.sh" data-abfrage
        "$ROOT/toolchain.sh" fe-build
        ;;
    format)
        "$ROOT/toolchain.sh" be-format
        "$ROOT/toolchain.sh" fe-eslint --fix .
        ;;

    help|-h|--help) usage ;;
    *) echo "Unknown command: $cmd" >&2; echo >&2; usage >&2; exit 2 ;;
esac
