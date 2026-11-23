#!/usr/bin/env node
/**
 * Comment Linter
 *
 * Code documents itself in this project. Clear names, small functions and honest structure carry
 * the meaning, and a passage that needs a comment beside it to be understood wants rewriting rather
 * than annotating.
 *
 * So only doc comments are allowed: the block that introduces a class, a method, a function or a
 * constant and says what it is for, which is a docstring in Python. Everything else goes. Where a
 * rationale genuinely has to be written down it belongs in the doc comment of the thing it is
 * about.
 *
 * The one exception is a TODO marking a real gap: something left unimplemented or knowingly
 * missing. Those are better said than left silent.
 *
 * The backend's Python sources, its tests and the tools are scanned alongside the frontend, since
 * the rule is the project's and not the frontend's. A shell script's header and the doc lines above
 * its functions are the shell's doc comments, so shell files are not scanned.
 *
 * Exit code 1 if a comment is found that is neither a doc comment nor a TODO.
 */

import {readFileSync} from 'fs'
import {pythonFindings, scriptFindings} from './comment-scan.mjs'
import {GREEN, RESET, BOLD, SOURCE_TARGETS, createReporter, targetFiles} from './lint-utils.mjs'

const reporter = createReporter()

for (const file of targetFiles(SOURCE_TARGETS)) {
    const text = readFileSync(file, 'utf-8')
    const found = file.endsWith('.py') ? pythonFindings(text) : scriptFindings(text, file.endsWith('.vue'))
    for (const one of found) reporter.error(file, one.line, one.message)
}

if (reporter.errors.length === 0 && reporter.warnings.length === 0) {
    console.log(`\n${GREEN}${BOLD}Comment lint passed.${RESET} ${targetFiles(SOURCE_TARGETS).length} files checked.\n`)
} else {
    reporter.print()
    reporter.exit()
}
