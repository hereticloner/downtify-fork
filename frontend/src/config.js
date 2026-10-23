// Browser location, or safe defaults when this module is evaluated
// without a DOM (the Vitest suite imports the API client directly).
const location =
  typeof window !== 'undefined' && window.location ? window.location : {}

const config = {
  PROTOCOL: process.env.PROTOCOL || location.protocol || 'http:',
  WS_PROTOCOL:
    process.env.WS_PROTOCOL ||
    (location.protocol === 'https:' ? 'wss:' : 'ws:'),
  BACKEND: process.env.BACKEND || location.hostname || '',
  PORT: process.env.PORT || location.port || '',
  WS_PORT: process.env.WS_PORT || location.port || '',
  BASEURL: process.env.BASEURL || '',
}

export default config
