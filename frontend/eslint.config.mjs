import js from '@eslint/js'
import vueI18n from '@intlify/eslint-plugin-vue-i18n'
import {createNodeResolver, importX} from 'eslint-plugin-import-x'
import vue from 'eslint-plugin-vue'
import vueA11y from 'eslint-plugin-vuejs-accessibility'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import calltaker from './eslint/index.mjs'
import * as localeParser from './eslint/i18n/locale-parser.mjs'
import {localeModules, localeSnapshots} from './eslint/locales.mjs'
import {INLINE_STATE_TYPE, restrictSyntax} from './eslint/restrictions.mjs'

/** The German catalogue as the plugin's key rules read it. */
const SNAPSHOTS = await localeSnapshots()

/** The catalogue module, which only the locale rules read. */
const LOCALE_FILES = ['src/i18n/de.ts']

/**
 * Which layer may not reach which, as `import-x/no-restricted-paths` zones.
 *
 * <p>The bottom layers do not import from the ones above them: the API clients, the catalogue and
 * the call phases stand on nothing of the interface, and components and composables stand on no
 * view.
 */
const LAYERS = [
    {layer: 'api', above: ['views', 'components', 'composables', 'phasen']},
    {layer: 'i18n', above: ['views', 'components', 'composables', 'phasen', 'api']},
    {layer: 'phasen', above: ['views', 'components', 'composables']},
    {layer: 'composables', above: ['views', 'components']},
    {layer: 'components', above: ['views']},
]

/**
 * Vue's rules as the components here are written: script, template, style; an element with nothing
 * inside closes itself; no `v-html`. Layout is left to the author, as in Ember, where Nuxt's stylistic
 * preset is off.
 */
const VUE_RULES = {
    'vue/block-order': ['error', {order: ['script', 'template', 'style']}],
    'vue/html-self-closing': ['error', {html: {void: 'always', normal: 'always', component: 'always'}, svg: 'always', math: 'always'}],
    'vue/no-v-html': 'error',
    'vue/multi-word-component-names': 'off',
    'vue/html-indent': 'off',
    'vue/html-closing-bracket-spacing': 'off',
    'vue/html-closing-bracket-newline': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/multiline-html-element-content-newline': 'off',
    'vue/max-attributes-per-line': 'off',
    'vue/first-attribute-linebreak': 'off',
}

/**
 * Text that reads the same in every language and so needs no catalogue entry: a run without
 * letters, a number with its unit, an upper-case code.
 */
const LANGUAGE_NEUTRAL_TEXT = [
    '[\\p{N}\\p{P}\\p{S}\\s]+',
    '[<>≤≥]?\\s?\\d[\\d.,:]*\\s?(?:ms|s|min|h|m|km|%)?',
    '[A-Z0-9]+(?:[-./][A-Z0-9]+)*\\.?',
]

/**
 * The `import-x/no-restricted-paths` zones of one layer.
 *
 * @param layer the layer, as listed in {@link LAYERS}
 * @returns the zones its files are held to
 */
function layerZones({layer, above}) {
    return above.map(from => ({
        target: `./src/${layer}`,
        from: `./src/${from}`,
        message: `${layer}/ may not import from ${from}/.`,
    }))
}

/**
 * Leaves the catalogue module to the locale rules: the locale parser hands ESLint a JSON AST, which
 * no rule written for a script can read.
 *
 * @param config one config entry
 * @returns the entry, ignoring the catalogue where it would apply rules to it
 */
function keepOffLocales(config) {
    if (config.name === 'calltaker/locales') return config
    if (!config.rules && !config.processor) return config
    return {...config, ignores: [...(config.ignores ?? []), ...LOCALE_FILES]}
}

export default [
    {
        name: 'calltaker/ignores',
        ignores: ['node_modules/**', 'dist/**', 'coverage/**', 'public/**'],
    },
    {
        name: 'calltaker/settings',
        settings: {
            'import-x/resolver-next': [createNodeResolver({extensions: ['.ts', '.vue', '.mjs', '.js']})],
            'vue-i18n': {localeDir: SNAPSHOTS, messageSyntaxVersion: '^11.0.0'},
        },
    },
    {name: 'calltaker/plugin', plugins: {calltaker, 'import-x': importX}},
    js.configs.recommended,
    ...tseslint.configs.recommended,
    ...vue.configs['flat/recommended'],
    {
        name: 'calltaker/vue-parser',
        files: ['**/*.vue'],
        languageOptions: {parserOptions: {parser: tseslint.parser, extraFileExtensions: ['.vue']}},
    },
    {
        name: 'calltaker/globals',
        languageOptions: {globals: {...globals.browser}},
    },
    {
        name: 'calltaker/node',
        files: ['eslint/**/*.{mjs,ts}', 'scripts/**/*.mjs', '*.config.{ts,mjs}'],
        languageOptions: {globals: {...globals.node}},
    },
    ...vueA11y.configs['flat/recommended'],
    {
        name: 'calltaker/accessibility',
        files: ['**/*.vue'],
        rules: {
            'vuejs-accessibility/label-has-for': ['error', {required: {some: ['nesting', 'id']}, allowChildren: true}],
        },
    },
    {name: 'calltaker/vue', files: ['**/*.vue'], rules: VUE_RULES},
    {
        name: 'calltaker/console',
        files: ['src/**/*.{ts,vue}'],
        rules: {
            'no-restricted-properties': ['error',
                {object: 'console', property: 'log', message: 'Leftover console.log: remove it.'},
                {object: 'console', property: 'debug', message: 'Leftover console.debug: remove it.'},
            ],
        },
    },
    {
        name: 'calltaker/vue-i18n',
        files: ['src/**/*.{ts,vue}'],
        ignores: ['src/i18n/**', 'src/**/*.test.ts'],
        plugins: {'@intlify/vue-i18n': vueI18n},
        rules: {
            '@intlify/vue-i18n/no-missing-keys': 'error',
        },
    },
    {
        name: 'calltaker/raw-text',
        files: ['src/**/*.vue'],
        plugins: {'@intlify/vue-i18n': vueI18n},
        rules: {
            '@intlify/vue-i18n/no-raw-text': ['error', {
                ignorePattern: `^(?:${LANGUAGE_NEUTRAL_TEXT.join('|')})$`,
                ignoreNodes: ['code'],
                attributes: {'/.+/': ['aria-label', 'title', 'placeholder', 'alt', 'label']},
            }],
        },
    },
    {
        name: 'calltaker/locales',
        files: LOCALE_FILES,
        languageOptions: {parser: localeParser},
        plugins: {'@intlify/vue-i18n': vueI18n},
        settings: {'vue-i18n': {localeDir: [SNAPSHOTS, localeModules()], messageSyntaxVersion: '^11.0.0'}},
        rules: {
            '@intlify/vue-i18n/valid-message-syntax': 'error',
            'calltaker/i18n-no-plural-messages': 'error',
            'calltaker/i18n-unused-keys': ['error', {sources: 'src', german: [{file: 'src/i18n/de.ts'}]}],
        },
    },
    ...LAYERS.map(layer => ({
        name: `calltaker/layers/${layer.layer}`,
        files: [`src/${layer.layer}/**/*.{ts,vue}`],
        rules: {'import-x/no-restricted-paths': ['error', {zones: layerZones(layer)}]},
    })),
    {
        name: 'calltaker/source-size',
        files: ['src/**/*.{ts,vue}'],
        ignores: ['src/**/*.test.ts', 'src/i18n/**'],
        rules: {'calltaker/max-function-lines': ['error', {max: 79}]},
    },
    {
        name: 'calltaker/state-types',
        files: ['src/**/*.{ts,vue}'],
        rules: restrictSyntax(INLINE_STATE_TYPE),
    },
    {
        name: 'calltaker/view-templates',
        files: ['src/**/*.vue'],
        ignores: ['src/components/**'],
        rules: {
            'calltaker/repeated-class-pattern': 'error',
            'calltaker/template-block-size': 'error',
        },
    },
    {
        name: 'calltaker/views',
        files: ['src/views/**/*.vue'],
        rules: {'max-lines': ['error', {max: 500}]},
    },
].map(keepOffLocales)
