/**
 * What the script linters read: the frontend, its configs, the backend, its tests and the tools,
 * and for the em dash also the styles, the page shell, the question graph, the build and CI files
 * and the README. Paths are relative to the repository root.
 */
export default {
    root: '..',
    sources: [
        {path: 'frontend/src', extensions: ['.ts', '.vue', '.js', '.mjs']},
        {path: 'frontend/eslint.config.mjs', extensions: null},
        {path: 'frontend/emberbox-lint.config.mjs', extensions: null},
        {path: 'frontend/vite.config.ts', extensions: null},
        {path: 'src', extensions: ['.py']},
        {path: 'tests', extensions: ['.py']},
        {path: 'tools', extensions: ['.py']},
    ],
    text: [
        {path: 'frontend/src', extensions: ['.css']},
        {path: 'frontend/index.html', extensions: null},
        {path: 'daten', extensions: ['.json']},
        {path: 'docker', extensions: ['Dockerfile', '.yaml']},
        {path: '.github', extensions: ['.yml']},
        {path: 'toolchain.sh', extensions: null},
        {path: 'README.md', extensions: null},
    ],
    browserStorage: {catalogue: 'frontend/browser-storage.json', sources: 'frontend/src'},
    duplication: '.jscpd.json',
}
