const http = require('http');
const { WebSocketServer } = require('./sfu/node_modules/ws');
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/plain' });
  res.end('ok');
});
const wss = new WebSocketServer({ server });
wss.on('connection', (ws) => {
  ws.send('hello');
  ws.on('message', (m) => ws.send('echo:' + m));
});
server.listen(3011, '127.0.0.1', () => {
  console.log('ws3011 ready');
});
setInterval(() => {}, 1 << 30);
