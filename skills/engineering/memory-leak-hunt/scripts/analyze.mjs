// Heap snapshot analyzer.
//   1. Counts instances of named constructors (the leak candidates).
//   2. Reverse retainer BFS from a sample node to a GC root, CORRECTLY skipping
//      weak edges (the bug in the prior session's retainers2.mjs was treating
//      WeakMap/weak edges as strong).
//
// Usage: node analyze.mjs <file.heapsnapshot> [constructorNameToTrace]

import fs from 'node:fs'

const file = process.argv[2]
const traceName = process.argv[3]
const snap = JSON.parse(fs.readFileSync(file, 'utf8'))

const meta = snap.snapshot.meta
const nodeFields = meta.node_fields
const nodeFieldCount = nodeFields.length
const nodeTypes = meta.node_types[0]
const edgeFields = meta.edge_fields
const edgeFieldCount = edgeFields.length
const edgeTypes = meta.edge_types[0]

const nodes = snap.nodes
const edges = snap.edges
const strings = snap.strings

const NODE_TYPE = nodeFields.indexOf('type')
const NODE_NAME = nodeFields.indexOf('name')
const NODE_ID = nodeFields.indexOf('id')
const NODE_SELF_SIZE = nodeFields.indexOf('self_size')
const NODE_EDGE_COUNT = nodeFields.indexOf('edge_count')

const EDGE_TYPE = edgeFields.indexOf('type')
const EDGE_NAME = edgeFields.indexOf('name_or_index')
const EDGE_TO = edgeFields.indexOf('to_node')

const nodeCount = nodes.length / nodeFieldCount

// Precompute, for each node, the index of its first edge in the flat edges array.
const firstEdge = new Uint32Array(nodeCount + 1)
{
  let e = 0
  for (let n = 0; n < nodeCount; n++) {
    firstEdge[n] = e
    e += nodes[n * nodeFieldCount + NODE_EDGE_COUNT]
  }
  firstEdge[nodeCount] = e
}

function nodeName(n) {
  return strings[nodes[n * nodeFieldCount + NODE_NAME]]
}
function nodeTypeName(n) {
  return nodeTypes[nodes[n * nodeFieldCount + NODE_TYPE]]
}
function nodeSelfSize(n) {
  return nodes[n * nodeFieldCount + NODE_SELF_SIZE]
}
function nodeId(n) {
  return nodes[n * nodeFieldCount + NODE_ID]
}

// ---- 1. Count by constructor name (object-type nodes only) ----
const counts = new Map()
const sizeByName = new Map()
for (let n = 0; n < nodeCount; n++) {
  const t = nodeTypeName(n)
  if (t !== 'object') continue
  const name = nodeName(n)
  counts.set(name, (counts.get(name) || 0) + 1)
  sizeByName.set(name, (sizeByName.get(name) || 0) + nodeSelfSize(n))
}

const watch = [
  'IncrementalCache',
  'CacheHandler',
  'WorkStore',
  'RequestStore',
  'AfterContext',
  'FlightRenderResult',
  'RenderResult',
  'ReactServerResult',
  'IncomingMessage',
  'ServerResponse',
  'NodeNextRequest',
  'NodeNextResponse',
  'AwaiterMulti',
  'AwaiterOnce',
]
console.log('== instance counts (file: %s) ==', file.split('/').pop())
for (const w of watch) {
  if (counts.has(w)) {
    console.log(
      `  ${w}: ${counts.get(w)}  (self_size total ${(sizeByName.get(w) / 1024).toFixed(1)} KB)`
    )
  }
}

// Top object constructors by total self size
const top = [...sizeByName.entries()]
  .sort((a, b) => b[1] - a[1])
  .slice(0, 15)
console.log('\n== top object constructors by total self_size ==')
for (const [name, size] of top) {
  console.log(`  ${(size / 1024 / 1024).toFixed(2)} MB  x${counts.get(name)}  ${name}`)
}

// ---- 2. Reverse retainer BFS skipping weak edges ----
if (traceName) {
  // Build reverse edge map (to_node -> list of {from, edgeType, edgeName}),
  // skipping weak edges entirely.
  console.log(`\n== building reverse graph (skipping weak edges) for trace of ${traceName} ==`)
  // Find a sample target node
  let target = -1
  for (let n = 0; n < nodeCount; n++) {
    if (nodeTypeName(n) === 'object' && nodeName(n) === traceName) {
      target = n
      break
    }
  }
  if (target === -1) {
    console.log(`  no node named ${traceName} found`)
  } else {
    // reverse adjacency built lazily via full scan during BFS is too slow;
    // build a compact reverse index once.
    const fromOf = new Int32Array(edges.length / edgeFieldCount).fill(-1)
    // For each edge, we know its owning node by scanning firstEdge.
    // Build owner array:
    const edgeCountTotal = edges.length / edgeFieldCount
    const ownerOf = new Int32Array(edgeCountTotal)
    {
      for (let n = 0; n < nodeCount; n++) {
        const s = firstEdge[n]
        const e = firstEdge[n + 1]
        for (let ei = s; ei < e; ei++) ownerOf[ei] = n
      }
    }
    // reverse map: toNode -> array of edgeIndex (non-weak)
    const rev = new Map()
    const WEAK = edgeTypes.indexOf('weak')
    for (let ei = 0; ei < edgeCountTotal; ei++) {
      const etype = edges[ei * edgeFieldCount + EDGE_TYPE]
      if (etype === WEAK) continue
      const to = edges[ei * edgeFieldCount + EDGE_TO] / nodeFieldCount
      let arr = rev.get(to)
      if (!arr) {
        arr = []
        rev.set(to, arr)
      }
      arr.push(ei)
    }

    // BFS from target up to a GC root (node type 'synthetic' named like (GC roots) or root)
    const visited = new Set([target])
    const queue = [target]
    const parent = new Map() // node -> {from, ei}
    let rootNode = -1
    while (queue.length) {
      const cur = queue.shift()
      const ct = nodeTypeName(cur)
      // Real GC roots are synthetic nodes only.
      if (ct === 'synthetic' && cur !== target) {
        rootNode = cur
        break
      }
      const inEdges = rev.get(cur)
      if (!inEdges) continue
      for (const ei of inEdges) {
        const from = ownerOf[ei]
        if (visited.has(from)) continue
        visited.add(from)
        parent.set(from, { child: cur, ei })
        queue.push(from)
      }
    }

    if (rootNode === -1) {
      console.log(`  reachable nodes from a ${traceName}: ${visited.size}; no GC root found via strong edges (=> NOT strongly retained / collectable)`)
    } else {
      // Reconstruct path root -> target
      console.log(`  STRONG retainer path from GC root to ${traceName}:`)
      const path = []
      let cur = rootNode
      // walk down via parent map (parent maps from->{child}), so we need to follow child links
      while (cur !== target) {
        const p = parent.get(cur)
        path.push({ node: cur, viaEi: p.ei, child: p.child })
        cur = p.child
      }
      path.push({ node: target })
      for (let i = 0; i < path.length; i++) {
        const { node, viaEi } = path[i]
        let edgeLabel = ''
        if (viaEi != null) {
          const et = edgeTypes[edges[viaEi * edgeFieldCount + EDGE_TYPE]]
          const enRaw = edges[viaEi * edgeFieldCount + EDGE_NAME]
          const en = et === 'element' || et === 'hidden' ? `[${enRaw}]` : strings[enRaw]
          edgeLabel = ` --${et}:${en}-->`
        }
        console.log(
          `    ${nodeTypeName(node)} '${nodeName(node)}' @id=${nodeId(node)} selfSize=${nodeSelfSize(node)}${edgeLabel}`
        )
      }
    }
  }
}
