/**
 * Checks the browser storage catalogue against the running code.
 *
 * `browser-storage.json` lists every value the application keeps in the browser, each with what it
 * holds and why. A key added to the code without an entry would be stored without anybody having
 * written down why, so every key the frontend reads or writes must be declared, and every declared
 * key must still be used.
 *
 * Keys are collected from `localStorage` and `sessionStorage` calls to `getItem`, `setItem` and
 * `removeItem`. A key held in a constant of the same file resolves to its literal; any other
 * argument is reported as one that cannot be checked.
 */

import {readFileSync} from 'fs'
import {join} from 'path'
import {SRC, createReporter, rel, walk} from './lint-utils.mjs'

const reporter = createReporter()

const CATALOG_FILE = join(SRC, '..', 'browser-storage.json')
const CATALOG_LABEL = 'frontend/browser-storage.json'
const STORAGE_CALL = /\b(?:localStorage|sessionStorage)\??\.(?:getItem|setItem|removeItem)\(\s*([^,)]+)/g

/**
 * The `const NAME = 'value'` bindings of a file, so a key held in a constant resolves.
 *
 * @param content the file's source
 * @returns the constants by name
 */
function constantsIn(content) {
    return new Map([...content.matchAll(/const\s+([A-Za-z_$][\w$]*)\s*=\s*'([^']*)'/g)].map(match => [match[1], match[2]]))
}

/**
 * The storage keys a file uses, and the arguments that are not literals.
 *
 * @param content the file's source
 * @returns the keys and the unresolved arguments
 */
function keysIn(content) {
    const constants = constantsIn(content)
    const keys = new Set()
    const dynamic = []
    for (const match of content.matchAll(STORAGE_CALL)) {
        const argument = match[1].trim()
        const literal = argument.match(/^'([^']*)'$/)
        if (literal) keys.add(literal[1])
        else if (constants.has(argument)) keys.add(constants.get(argument))
        else dynamic.push(argument)
    }
    return {keys, dynamic}
}

const catalog = JSON.parse(readFileSync(CATALOG_FILE, 'utf-8'))
const declared = new Set((catalog.entries ?? []).map(entry => entry.key))
const used = new Map()

for (const file of [...walk(SRC, '.ts'), ...walk(SRC, '.vue')]) {
    if (file.endsWith('.test.ts')) continue
    const {keys, dynamic} = keysIn(readFileSync(file, 'utf-8'))
    for (const key of keys) if (!used.has(key)) used.set(key, file)
    for (const argument of dynamic) {
        reporter.error(file, 0, `storage key is not a literal (${argument}), so it cannot be checked against ${CATALOG_LABEL}`, 'dynamic')
    }
}

for (const [key, file] of used) {
    if (!declared.has(key)) reporter.error(file, 0, `browser storage key '${key}' is not declared in ${CATALOG_LABEL}`, 'undeclared')
}
for (const key of declared) {
    if (!used.has(key)) reporter.error(CATALOG_LABEL, 0, `declared browser storage key '${key}' is no longer used`, 'stale')
}

console.log(`Checked ${used.size} storage keys against ${declared.size} declared in ${rel(CATALOG_FILE)}`)
reporter.print()
process.exit(reporter.errors.length > 0 ? 1 : 0)
