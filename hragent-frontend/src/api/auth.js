import http from './http'

// OAuth2 密码流：FastAPI OAuth2PasswordRequestForm 需表单编码
export function login(username, password) {
  const body = new URLSearchParams({ username, password })
  return http.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function fetchMe() {
  return http.get('/auth/me')
}
