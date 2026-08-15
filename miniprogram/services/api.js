const request = require('../utils/request')

function login(code) {
  return request({
    url: '/auth/login',
    method: 'POST',
    data: { code },
    auth: false
  })
}

function getCurrentUser() {
  return request({ url: '/users/me' })
}

module.exports = {
  login,
  getCurrentUser
}
