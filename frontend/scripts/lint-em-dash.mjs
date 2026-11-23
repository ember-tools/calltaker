#!/usr/bin/env node
/**
 * Em Dash Linter
 *
 * The em dash is forbidden in this project's code and in the text it ships, so the interface reads
 * the same everywhere. Every source the comment linter reads is checked, together with the styles,
 * the page shell, the question graph, the build and CI files and the README.
 *
 * Exit code 1 if the character is found anywhere it is not allowed.
 */

import {readFileSync} from 'fs'
import {GREEN, RESET, BOLD, SOURCE_TARGETS, createReporter, targetFiles} from './lint-utils.mjs'

const reporter = createReporter()

/** Built from its code point so this file does not trip over itself. */
const EM_DASH = String.fromCharCode(0x2014)

/** The names markup gives the same character, assembled here for the same reason. */
const ENTITIES = ['mdash', '#8212', '#x2014', '#X2014'].map(name => `&${name};`)

const SPELLINGS = [EM_DASH, ...ENTITIES]

/** What is scanned beyond the sources. Paths are relative to the repository root. */
const TARGETS = [
    ...SOURCE_TARGETS,
    {path: 'frontend/src', extensions: ['.css']},
    {path: 'frontend/index.html', extensions: null},
    {path: 'daten', extensions: ['.json']},
    {path: 'docker', extensions: ['Dockerfile', '.yaml']},
    {path: '.github', extensions: ['.yml']},
    {path: 'toolchain.sh', extensions: null},
    {path: 'README.md', extensions: null},
]

/**
 * Reports the first em dash on each line of a file.
 *
 * @param file the absolute path
 */
function check(file) {
    const lines = readFileSync(file, 'utf-8').split('\n')
    for (let i = 0; i < lines.length; i++) {
        for (const spelling of SPELLINGS) {
            const column = lines[i].indexOf(spelling)
            if (column === -1) continue
            reporter.error(file, i + 1,
                `Em dash at column ${column + 1}. Use a comma, a colon, parentheses, a full stop or a spaced hyphen instead.`)
            break
        }
    }
}

const scanned = targetFiles(TARGETS)
scanned.forEach(check)

if (reporter.errors.length === 0 && reporter.warnings.length === 0) {
    console.log(`\n${GREEN}${BOLD}Em dash lint passed.${RESET} ${scanned.length} files carry none.\n`)
} else {
    reporter.print()
    reporter.exit()
}
