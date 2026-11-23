/**
 * Every linter the frontend is held to, in the order they run.
 *
 * <p>This is the one list. `./toolchain.sh fe-lint`, the build and CI all read it, so a linter green
 * on one of them is green on all of them. Each entry is a name, which is what
 * `./toolchain.sh fe-lint <name>` takes, and the command that runs it from the frontend directory.
 *
 * <p>ESLint carries the rules about the code itself, the project's own among them. jscpd measures
 * duplication. The scripts check what ESLint does not read: the browser storage catalogue, and the
 * em dash and comment rules, which reach the Python sources as well.
 */
export const LINTERS = [
    {name: 'eslint', command: ['node', 'node_modules/eslint/bin/eslint.js', '--max-warnings=0']},
    {name: 'duplication', command: ['node', 'node_modules/jscpd/run-jscpd.js', '--config', '.jscpd.json']},
    {name: 'browser-storage', command: ['node', 'scripts/lint-browser-storage.mjs']},
    {name: 'em-dash', command: ['node', 'scripts/lint-em-dash.mjs']},
    {name: 'comments', command: ['node', 'scripts/lint-comments.mjs']},
]
