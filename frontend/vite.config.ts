import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
export default defineConfig(() => {
  const env = process.env
  return {
    plugins: [vue(), {
      name: 'shared-configuration',
      resolveId(id) { if (id === 'virtual:opscope-configuration') return '\0opscope-configuration' },
      load(id) {
        if (id !== '\0opscope-configuration') return
        const path = resolve(import.meta.dirname, '../configuration.js')
        this.addWatchFile(path)
        return readFileSync(path, 'utf8').replace(/^if \(typeof module.*$/m, '') + '\nexport default Configuration;'
      }
    }], base: env.VITE_OPSCOPE_BASE || '/',
    server: { host: '127.0.0.1', port: Number(env.OPSCOPE_FRONTEND_PORT || 5173), strictPort: true,
      proxy: { '/api': { target: `http://127.0.0.1:${env.OPSCOPE_PORT || 8768}`, changeOrigin: true } } },
    build: { assetsDir: 'static' }
  }
})
