import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    base: "./",
    plugins: [react()],
    server: {
        watch: {
            usePolling: true,
            interval: 1000,
            ignored: ['**/node_modules/**', '**/.git/**'],
        },
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/analyze': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/bulk-analyze': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
})
