// Identify the two dependency-side accumulators by retainer signature and report
// their entry counts. Sentry _sentSpans LRUMap (elements = 16-hex span ids) and
// PostHog distinctIdHasSentFlagCalls (elements = Sets keyed by UUID).
//
// Usage: node count-leaks.mjs <file.heapsnapshot>

import fs from 'node:fs'
const file = process.argv[2]
const snap = JSON.parse(fs.readFileSync(file, 'utf8'))
const meta = snap.snapshot.meta
const F = meta.node_fields.length
const nodeTypes = meta.node_types[0]
const edgeFields = meta.edge_fields
const EF = edgeFields.length
const edgeTypes = meta.edge_types[0]
const nodes = snap.nodes, edges = snap.edges, strings = snap.strings
const T = meta.node_fields.indexOf('type'), NAME = meta.node_fields.indexOf('name')
const EC = meta.node_fields.indexOf('edge_count')
const ETYPE = edgeFields.indexOf('type'), ENAME = edgeFields.indexOf('name_or_index'), ETO = edgeFields.indexOf('to_node')
const nodeCount = nodes.length / F
const firstEdge = new Uint32Array(nodeCount + 1)
{ let e = 0; for (let n = 0; n < nodeCount; n++) { firstEdge[n] = e; e += nodes[n*F+EC] } firstEdge[nodeCount] = e }
const tn = (n) => nodeTypes[nodes[n*F+T]]
const nm = (n) => strings[nodes[n*F+NAME]]

// find a property edge with a given name from node n -> returns target node
function prop(n, name) {
  for (let ei = firstEdge[n]; ei < firstEdge[n+1]; ei++) {
    const et = edgeTypes[edges[ei*EF+ETYPE]]
    if ((et === 'property' || et === 'internal' || et === 'context') && strings[edges[ei*EF+ENAME]] === name)
      return edges[ei*EF+ETO]/F
  }
  return -1
}
function countElements(n) { return n < 0 ? -1 : nodes[n*F+EC] }

// Sentry: find any object with property _sentSpans, follow ._cache (Map) -> table (array)
let sentSpans = -1, distinctId = -1
for (let n = 0; n < nodeCount; n++) {
  const t = tn(n)
  if (t !== 'object') continue
  // _sentSpans -> LRUMap; LRUMap._cache -> Map; Map.table -> array
  const ss = prop(n, '_sentSpans')
  if (ss >= 0) {
    const cache = prop(ss, '_cache')
    const map = cache >= 0 ? cache : ss
    const table = prop(map, 'table')
    sentSpans = Math.max(sentSpans, countElements(table >= 0 ? table : map))
  }
  const di = prop(n, 'distinctIdHasSentFlagCalls')
  if (di >= 0) {
    // di is an object/map; count its property/element edges
    distinctId = Math.max(distinctId, countElements(di))
  }
}
console.log(`${file.split('/').pop()}: sentrySentSpans=${sentSpans}  postHogDistinctIdFlagCalls=${distinctId}`)
