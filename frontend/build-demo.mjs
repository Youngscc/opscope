import { build } from 'vite'
import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const bundle = await build({
  root, mode: 'demo', base: './',
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    write: false, cssCodeSplit: false, minify: true,
    lib: { entry: resolve(root, 'src/main.ts'), name: 'OpScopeDemo', formats: ['iife'] },
  },
})
const files = (Array.isArray(bundle) ? bundle : [bundle]).flatMap(result => result.output)
const scripts = files.filter(file => file.type === 'chunk')
if (scripts.length !== 1 || scripts[0].imports.length || scripts[0].dynamicImports.length) {
  throw new Error('Static demo must contain one self-contained script')
}
const css = files.filter(file => file.type === 'asset' && file.fileName.endsWith('.css'))
  .map(file => file.source).join('\n').replace(/<\/style/gi, '<\\/style')
const js = scripts[0].code.replace(/<\/script/gi, '<\\/script')
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; base-uri 'none'">
<title>OpScope · 静态演示</title><style>${css}</style></head><body><div id="app"></div><script>${js}</script></body></html>`
const target = resolve(root, '../opscope-demo.html')
writeFileSync(target, html)
console.log(`Built ${target} (${Buffer.byteLength(html).toLocaleString()} bytes)`)
