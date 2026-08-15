const assert = require('node:assert/strict')
const test = require('node:test')

const { resolveApiBaseUrl } = require('../../miniprogram/config/environment')

test('development API uses the local server', () => {
  assert.equal(resolveApiBaseUrl('develop'), 'http://127.0.0.1:8000/api/v1')
})

test('release builds reject a missing HTTPS domain', () => {
  assert.throws(() => resolveApiBaseUrl('release'), /HTTPS 合法域名/)
})
