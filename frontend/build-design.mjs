import { build, transformWithOxc } from 'vite'
import { parse, compileScript, babelParse } from '@vue/compiler-sfc'
import { parse as parseTemplate } from '@vue/compiler-dom'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const templates = new Map()
const dataBlocks = [
  ['designer-matrix-data', 'workspace-demo.json'],
  ['designer-optimization-data', 'optimization-demo.json'],
]
const escapeScript = text => text.replace(/<\/script/gi, '<\\/script')
const dataModule = id => `export default JSON.parse(document.getElementById(${JSON.stringify(id)}).textContent);`

async function javascriptExpression(expression, event) {
  const input = event ? `function __event($event) { ${expression} }` : `const __value = (${expression});`
  const {code} = await transformWithOxc(input, 'designer-expression.ts', {lang:'ts', target:'es2023'})
  const statement = babelParse(code, {sourceType:'module'}).program.body[0]
  const value = event ? statement.body : statement.declarations[0].init
  return code.slice(value.start + (event ? 1 : 0), value.end - (event ? 1 : 0)).trim().replace(/;$/, '')
}

async function browserTemplate(source) {
  const edits = []
  async function expression(value, event, attribute) {
    if (!value || !/\bas\s+|!\s*(?:[.\]),?]|$)/.test(value.content)) return
    let code = await javascriptExpression(value.content, event)
    if (attribute) code = code.replaceAll('&', '&amp;').replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    edits.push({start:value.loc.start.offset, end:value.loc.end.offset, code})
  }
  async function visit(node) {
    if (node.type === 5) await expression(node.content, false, false)
    for (const prop of node.props || []) {
      if (prop.type === 7) await expression(prop.name === 'for' ? prop.forParseResult?.source : prop.exp,
        prop.name === 'on', true)
    }
    for (const child of node.children || []) await visit(child)
  }
  await visit(parseTemplate(source, {whitespace:'preserve'}))
  for (const edit of edits.sort((a, b) => b.start - a.start)) source = source.slice(0, edit.start) + edit.code + source.slice(edit.end)
  return source
}

function editableTemplate(source) {
  function format(node, depth) {
    const indent = '  '.repeat(depth)
    if (!node.loc.source.trim()) return ''
    if (node.type !== 1 || !node.children.some(child => child.type === 1)) return indent + node.loc.source
    const start = source.slice(node.loc.start.offset, node.children[0].loc.start.offset).trim()
    const end = source.slice(node.children.at(-1).loc.end.offset, node.loc.end.offset).trim()
    return [indent + start, ...node.children.map(child => format(child, depth + 1)), indent + end].filter(Boolean).join('\n')
  }
  return parseTemplate(source, {whitespace:'preserve', comments:true}).children.map(node => format(node, 0)).filter(Boolean).join('\n')
}

async function componentModule(path) {
  const source = relative(root, path).replaceAll('\\', '/')
  const id = 'designer-' + source.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()
  const {descriptor} = parse(readFileSync(path, 'utf8'), {filename:path})
  if (!descriptor.template || descriptor.styles.length) throw new Error(`Designer export needs an unscoped template: ${source}`)
  templates.set(id, {source, content:editableTemplate(await browserTemplate(descriptor.template.content))})
  const script = descriptor.script || descriptor.scriptSetup
    ? compileScript(descriptor, {id, genDefaultAs:'__design_component', inlineTemplate:false}) : null
  const metadata = {...script?.bindings, __isScriptSetup:true}
  const components = Object.values(script?.imports || {}).filter(item => !item.isType && item.source.endsWith('.vue'))
    .map(item => item.local).join(', ')
  // Runtime templates need setup values on the instance proxy, as in an ordinary setup component.
  const setup = script?.content.replace(/Object\.defineProperty\(__returned__, ['"]__isScriptSetup['"], \{[^}]*\}\)\s*;?/, '')
  const code = `${setup || 'const __design_component = {};'}
import { compile as __compileDesignTemplate } from 'vue';
__design_component.components = {${components}};
__design_component.render = __compileDesignTemplate(document.getElementById(${JSON.stringify(id)}).textContent, {bindingMetadata:${JSON.stringify(metadata)}});
export default __design_component;`
  return (await transformWithOxc(code, path, {lang:'ts', target:'es2023'})).code
}

const designerPlugin = {
  name:'opscope-designer-handoff',
  resolveId(id) {
    if (id === 'virtual:opscope-demo') return '\0designer-matrix'
    if (id === 'virtual:opscope-configuration') return '\0designer-configuration'
    if (id.endsWith('optimization-demo.json')) return '\0designer-optimization'
  },
  async load(id) {
    if (id === '\0designer-matrix') return dataModule('designer-matrix-data')
    if (id === '\0designer-optimization') return dataModule('designer-optimization-data')
    if (id === '\0designer-configuration') return readFileSync(resolve(root, '../configuration.js'), 'utf8')
      .replace(/^if \(typeof module.*$/m, '') + '\nexport default Configuration;'
    if (id.endsWith('.vue')) return componentModule(id)
  },
}

const bundle = await build({
  root, configFile:false, mode:'demo', base:'./', plugins:[designerPlugin],
  resolve:{alias:[{find:/^vue$/, replacement:resolve(root, 'node_modules/vue/dist/vue.esm-bundler.js')}]},
  define:{'process.env.NODE_ENV':JSON.stringify('production'), __VUE_OPTIONS_API__:true,
    __VUE_PROD_DEVTOOLS__:false, __VUE_PROD_HYDRATION_MISMATCH_DETAILS__:false},
  build:{write:false, cssCodeSplit:false, cssMinify:false, minify:false, sourcemap:false,
    lib:{entry:resolve(root, 'src/main.ts'), name:'OpScopeDesign', formats:['iife']}},
})
const files = (Array.isArray(bundle) ? bundle : [bundle]).flatMap(result => result.output)
const scripts = files.filter(file => file.type === 'chunk')
if (scripts.length !== 1 || scripts[0].imports.length || scripts[0].dynamicImports.length) throw new Error('Designer HTML must be self-contained')
const css = files.filter(file => file.type === 'asset' && file.fileName.endsWith('.css'))
  .map(file => file.source).join('\n').replace(/<\/style/gi, '<\\/style')
const blocks = dataBlocks.map(([id, name]) => {
  const data = JSON.parse(readFileSync(resolve(root, 'src/data', name), 'utf8'))
  return `<script id="${id}" type="application/json">\n${escapeScript(JSON.stringify(data, null, 2))}\n</script>`
}).join('\n\n')
const markup = [...templates].sort(([, a], [, b]) => a.source.localeCompare(b.source)).map(([id, template]) =>
  `<!-- 模板来源：${template.source} -->\n<script id="${id}" type="text/x-template" data-source="${template.source}">\n${escapeScript(template.content)}\n</script>`).join('\n\n')
const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; base-uri 'none'">
  <title>OpScope · UI 设计交接</title>
  <!-- 编辑区 1：页面样式。修改颜色、间距、字体与布局，刷新即可预览。 -->
  <style id="designer-styles">
${css}
  </style>
</head>
<body>
  <!-- 本文件包含性能评估、性能分析、MegaKernel及弹窗；数据为合成示例。 -->
  <div id="app"></div>

  <!-- 编辑区 2：页面与组件模板。data-source标注对应Vue源文件，便于回传后迁回。 -->
  <!-- 保留v-绑定及事件含义，可调整HTML结构、class、文案和样式。 -->
${markup}

  <!-- 编辑区 3：示例JSON。两个数据区独立于布局；后续由数据适配层接回接口。 -->
${blocks}

  <!-- 运行区：Vue、路由、状态与现有交互逻辑已内嵌，无外部文件依赖。 -->
  <script id="designer-runtime">
${escapeScript(scripts[0].code)}
  </script>
</body>
</html>
`
const target = resolve(root, '../opscope-ui-design.html')
const output = html.replace(/[\t ]+$/gm, '')
writeFileSync(target, output)
console.log(`Built ${target} (${Buffer.byteLength(output).toLocaleString()} bytes, ${templates.size} editable templates)`)
