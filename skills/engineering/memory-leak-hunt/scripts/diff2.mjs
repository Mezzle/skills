// Diff per-type heap pools across an ordered list of snapshots (baseline → ...
// → final). Reports bucket-2 pools (string/object/array) + code + IncrementalCache
// instance count, so a time-proportional parsed-graph leak is visible as a
// monotonic climb in string/object/array (NOT code, which is JIT warmup).
//
// Usage: node diff2.mjs <label> <snap1> <snap2> [snap3 ...]

import fs from 'node:fs'

function pools(file) {
  const snap = JSON.parse(fs.readFileSync(file, 'utf8'))
  const meta = snap.snapshot.meta
  const F = meta.node_fields.length
  const nodeTypes = meta.node_types[0]
  const nodes = snap.nodes
  const strings = snap.strings
  const T = meta.node_fields.indexOf('type')
  const NAME = meta.node_fields.indexOf('name')
  const SIZE = meta.node_fields.indexOf('self_size')
  const n = nodes.length / F
  const byType = new Map()
  let total = 0
  let icCount = 0
  let icSize = 0
  for (let i = 0; i < n; i++) {
    const size = nodes[i * F + SIZE]
    total += size
    const t = nodeTypes[nodes[i * F + T]]
    byType.set(t, (byType.get(t) || 0) + size)
    if (t === 'object' && strings[nodes[i * F + NAME]] === 'IncrementalCache') {
      icCount++
      icSize += size
    }
  }
  const MB = (b) => b / 1024 / 1024
  return {
    total: MB(total),
    string: MB(byType.get('string') || 0),
    object: MB(byType.get('object') || 0),
    array: MB(byType.get('array') || 0),
    concat: MB(byType.get('concatenated string') || 0),
    code: MB(byType.get('code') || 0),
    icCount,
  }
}

const label = process.argv[2]
const files = process.argv.slice(3)
console.log(`\n=== ${label} : per-type heap pools across ${files.length} snapshots ===`)
console.log(
  'idx  total   string  object  array   concat  code    IncrCache#'
)
const base = pools(files[0])
files.forEach((f, i) => {
  const p = pools(f)
  const d = (v, b) => `${v.toFixed(1)}${i > 0 ? `(${v - b >= 0 ? '+' : ''}${(v - b).toFixed(1)})` : ''}`
  console.log(
    `${i}    ${d(p.total, base.total)}  ${d(p.string, base.string)}  ${d(p.object, base.object)}  ${d(p.array, base.array)}  ${d(p.concat, base.concat)}  ${d(p.code, base.code)}  ${p.icCount}`
  )
})
console.log(
  '\nBucket-2 leak signature = monotonic climb in string/object/array.\n' +
    'JIT warmup = code climbs then plateaus (NOT a leak).'
)
