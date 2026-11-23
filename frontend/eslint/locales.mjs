import {mkdirSync, writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {createJiti} from 'jiti'

const I18N = fileURLToPath(new URL('../src/i18n/', import.meta.url))
const SNAPSHOTS = fileURLToPath(new URL('../node_modules/.cache/calltaker-eslint/locales/', import.meta.url))

/**
 * The German catalogue as `@intlify/eslint-plugin-vue-i18n` reads it.
 *
 * <p>The plugin loads messages from JSON, YAML or CommonJS files only, and the catalogue here is a
 * TypeScript module. So the module is evaluated and written out as JSON for the plugin's
 * `localeDir`.
 *
 * @returns the glob the plugin's `localeDir` setting takes
 */
export async function localeSnapshots() {
    const jiti = createJiti(import.meta.url, {moduleCache: false})
    const german = await jiti.import(`${I18N}de.ts`, {default: true})
    mkdirSync(SNAPSHOTS, {recursive: true})
    writeFileSync(`${SNAPSHOTS}de.json`, JSON.stringify(german))
    return `${SNAPSHOTS}*.json`
}

/**
 * The catalogue module itself, as a glob for the plugin's `localeDir`, which the locale rules need
 * to know the file as a locale.
 *
 * @returns the glob of the German module
 */
export function localeModules() {
    return `${I18N}de.ts`
}
