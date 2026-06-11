// Sequential driver with NO keep-alive (Connection: close), to mimic the
// real prod access pattern (UptimeRobot: low-concurrency, single hits). If the
// socket-bounded residual is the only retention, closing connections should
// drive surviving IncrementalCache instances to ~0 after GC.

import http from 'node:http'

const N = Number(process.argv[2] || 2000)

function once() {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port: 3000,
        path: '/',
        method: 'GET',
        headers: { Connection: 'close' },
        agent: false, // no socket pooling
      },
      (res) => {
        res.on('data', () => {})
        res.on('end', resolve)
      }
    )
    req.on('error', reject)
    req.end()
  })
}

for (let i = 0; i < N; i++) {
  await once()
}
console.log(JSON.stringify({ done: N, mode: 'no-keepalive-sequential' }))
