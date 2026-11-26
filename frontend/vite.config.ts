import {emberbox} from '@emberbox/ui/vite'
import vue from '@vitejs/plugin-vue'
import {defineConfig} from 'vitest/config'

const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
    plugins: [
        vue(),
        emberbox({
            url: 'https://calltaker.emberbox.app',
            logo: 'calltaker',
            app: {name: 'Calltaker', description: 'Notrufannahme für die Leitstelle üben.'},
            prerender: {entry: 'src/prerender.ts', paths: ['/', '/hilfe']},
        }),
    ],
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
        setupFiles: ['src/test-setup.ts'],
        server: {deps: {inline: ['@emberbox/ui', '@nuxt/ui']}},
    },
})
