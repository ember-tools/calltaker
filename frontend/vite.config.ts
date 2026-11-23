import {defineConfig} from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
    plugins: [vue(), tailwindcss()],
    build: {
        outDir: '../src/frontend_dist',
        emptyOutDir: true,
    },
    server: {
        host: true,
        proxy: {
            '/api': backend,
            '/kacheln': backend,
            '/ws': {target: backend.replace(/^http/, 'ws'), ws: true},
        },
    },
    test: {
        environment: 'happy-dom',
    },
})
