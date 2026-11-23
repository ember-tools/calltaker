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

export default defineConfig({
    plugins: [vue(), tailwindcss()],
    define: {
        __COMMIT__: JSON.stringify(commit()),
        __GEBAUT__: JSON.stringify(process.env.CALLTAKER_GEBAUT || new Date().toISOString()),
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
