/**
 * Shared utilities for the script linters: the source folders, a file walker and a reporter that
 * groups and prints what the linters find.
 */

import {existsSync, readdirSync} from 'fs'
import {join, relative} from 'path'

export const SRC = new URL('../src', import.meta.url).pathname
export const REPO_ROOT = new URL('../..', import.meta.url).pathname

export const RED = '\x1b[31m'
export const GREEN = '\x1b[32m'
export const YELLOW = '\x1b[33m'
export const RESET = '\x1b[0m'
export const BOLD = '\x1b[1m'

/**
 * The project's sources, which both the comment and the em dash linter read: the frontend, its
 * build and lint tooling, the backend, its tests and the tools. Paths are relative to the
 * repository root.
 */
export const SOURCE_TARGETS = [
    {path: 'frontend/src', extensions: ['.ts', '.vue', '.js', '.mjs']},
    {path: 'frontend/scripts', extensions: ['.mjs', '.ts']},
    {path: 'frontend/eslint', extensions: ['.mjs', '.ts']},
    {path: 'frontend/eslint.config.mjs', extensions: null},
    {path: 'frontend/vite.config.ts', extensions: null},
    {path: 'src', extensions: ['.py']},
    {path: 'tests', extensions: ['.py']},
    {path: 'tools', extensions: ['.py']},
]

/** Folders no linter looks into: dependencies, builds and caches. */
const SKIPPED_DIRS = new Set(['node_modules', 'frontend_dist', 'dist', '__pycache__', '.venv'])

/**
 * Every file below a folder whose name ends in the extension.
 *
 * @param dir the folder, which may be missing
 * @param ext the extension, with its dot
 * @returns the absolute paths
 */
export function walk(dir, ext) {
    if (!existsSync(dir)) return []
    const results = []
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name)
        if (entry.isDirectory()) {
            if (!SKIPPED_DIRS.has(entry.name)) results.push(...walk(full, ext))
        } else if (entry.name.endsWith(ext)) {
            results.push(full)
        }
    }
    return results
}

/**
 * A path relative to the repository root, for messages.
 *
 * @param file the absolute path
 * @returns the relative path
 */
export function rel(file) {
    return relative(REPO_ROOT, file)
}

/**
 * Every file of the given targets, each a folder or a file relative to the repository root.
 *
 * @param targets `{path, extensions}` entries; `extensions` is null for a single file
 * @returns the absolute paths of the files that exist
 */
export function targetFiles(targets) {
    return targets.flatMap(target => {
        const absolute = join(REPO_ROOT, target.path)
        if (!target.extensions) return existsSync(absolute) ? [absolute] : []
        return target.extensions.flatMap(extension => walk(absolute, extension))
    })
}

/**
 * A collector for errors and warnings that prints them grouped by category.
 *
 * @returns the reporter
 */
export function createReporter() {
    const errors = []
    const warnings = []
    const entry = (file, line, msg, category) => ({file: typeof file === 'string' && file.startsWith('/') ? rel(file) : file, line, msg, category})

    return {
        error(file, line, msg, category = '') {
            errors.push(entry(file, line, msg, category))
        },
        warn(file, line, msg, category = '') {
            warnings.push(entry(file, line, msg, category))
        },
        get errors() { return errors },
        get warnings() { return warnings },

        print() {
            printGroup(warnings, YELLOW, 'Warnings')
            printGroup(errors, RED, 'Errors')
        },

        exit() {
            if (errors.length > 0) {
                console.log(`\n${RED}Lint failed with ${errors.length} error(s).${RESET}\n`)
                process.exit(1)
            } else if (warnings.length > 0) {
                console.log(`\n${YELLOW}Lint passed with ${warnings.length} warning(s).${RESET}\n`)
            } else {
                console.log(`\nLint passed.\n`)
            }
        },
    }
}

/**
 * Prints one group of findings, split by category when there is more than one.
 *
 * @param items the findings
 * @param color the colour of the label
 * @param label the group's name
 */
function printGroup(items, color, label) {
    if (items.length === 0) return
    console.log(`\n${color}${BOLD}${label} (${items.length}):${RESET}`)
    const groups = Map.groupBy(items, item => item.category || 'Other')
    for (const [category, entries] of groups) {
        if (groups.size > 1) console.log(`\n  ${BOLD}${category}${RESET}`)
        for (const e of entries) {
            const loc = e.line > 0 ? `:${e.line}` : ''
            console.log(`    ${color}${label.toLowerCase().slice(0, -1)}${RESET} ${e.file}${loc}: ${e.msg}`)
        }
    }
}
