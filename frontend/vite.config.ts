import type {Plugin} from 'vite'
import {defineConfig} from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import {execSync} from 'node:child_process'

const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'

/**
 * The short commit the bundle is built from. The image build hands it in as an environment
 * variable, since its context has no `.git`; without either it is "dev".
 *
 * @returns the commit
 */
function commit(): string {
    if (process.env.CALLTAKER_COMMIT) return process.env.CALLTAKER_COMMIT
    try {
        return execSync('git rev-parse --short HEAD', {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim()
    } catch {
        return 'dev'
    }
}

const gebaut = process.env.CALLTAKER_GEBAUT || new Date().toISOString()

/**
 * Writes `fassung.json` next to the built page, naming the build, so open pages can notice that
 * a newer one is being served.
 *
 * @returns the plugin
 */
function fassung(): Plugin {
    return {
        name: 'calltaker-fassung',
        generateBundle() {
            this.emitFile({type: 'asset', fileName: 'fassung.json', source: JSON.stringify({commit: commit(), gebaut})})
        },
    }
}

export default defineConfig({
    plugins: [vue(), tailwindcss(), fassung()],
    define: {
        __COMMIT__: JSON.stringify(commit()),
        __GEBAUT__: JSON.stringify(gebaut),
    },
    build: {
        outDir: '../src/frontend_dist',
        emptyOutDir: true,
    },
    server: {
        host: true,
        proxy: {
            '/api': backend,
            '/kacheln': backend,
        },
    },
    test: {
        environment: 'happy-dom',
        globals: true,
    },
})
