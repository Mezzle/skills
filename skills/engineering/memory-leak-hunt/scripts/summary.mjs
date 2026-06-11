// Compact heap summary: total retained self_size by node TYPE (string, object,
// array, ...) plus a few key constructors. This is the bucket-2 instrument:
// the handoff describes bucket 2 as "object Object + concatenated string +
// arrays", so we watch string/object/array totals vs request count, NOT the
// IncrementalCache instance count.
//
// Usage: node summary.mjs <file.heapsnapshot>

import fs from 'node:fs'

const file = process.argv[2]
const snap = JSON.parse(fs.readFileSync(file, 'utf8'))
const meta = snap.snapshot.meta
const nodeFields = meta.node_fields
const F = nodeFields.length
const nodeTypes = meta.node_types[0]
const nodes = snap.nodes
const strings = snap.strings
const T = nodeFields.indexOf('type')
const NAME = nodeFields.indexOf('name')
const SIZE = nodeFields.indexOf('self_size')
const nodeCount = nodes.length / F

const byType = new Map()
const objByName = new Map()
let total = 0
for (let n = 0; n < nodeCount; n++) {
  const size = nodes[n * F + SIZE]
  total += size
  const t = nodeTypes[nodes[n * F + T]]
  byType.set(t, (byType.get(t) || 0) + size)
  if (t === 'object') {
    const name = strings[nodes[n * F + NAME]]
    objByName.set(name, (objByName.get(name) || 0) + size)
  }
}

const mb = (b) => (b / 1024 / 1024).toFixed(2)
const watch = ['IncrementalCache', 'CacheHandler', 'IncomingMessage', 'ServerResponse']
const parts = [
  `total=${mb(total)}MB`,
  `string=${mb(byType.get('string') || 0)}`,
  `object=${mb(byType.get('object') || 0)}`,
  `array=${mb(byType.get('array') || 0)}`,
  `(concat str=${mb(byType.get('concatenated string') || 0)})`,
  `code=${mb(byType.get('code') || 0)}`,
]
console.log(`${file.split('/').pop()}: ${parts.join('  ')}`)
const ic = watch
  .map((w) => `${w}=${(objByName.get(w) ? '' : '0KB')}` || '')
  .join(' ')
// instance self-size of watched constructors
const watchLine = watch
  .map((w) => `${w} ${((objByName.get(w) || 0) / 1024).toFixed(1)}KB`)
  .join('  ')
console.log(`   ${watchLine}`)
