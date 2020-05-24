#!/usr/bin/env node
var WebSocketServer = require('websocket').server;
var http = require('http');

var server = http.createServer(function (request, response) {
	console.log((new Date()) + ' Received request for ' + request.url);
	response.writeHead(404);
	response.end();
});

const port = process.env.PORT || 8080;
server.listen(port, function () {
	console.log((new Date()) + ` Server is listening on port ${port}`);
});

wsServer = new WebSocketServer({
	httpServer: server,
	// You should not use autoAcceptConnections for production
	// applications, as it defeats all standard cross-origin protection
	// facilities built into the protocol and the browser.  You should
	// *always* verify the connection's origin and decide whether or not
	// to accept it.
	autoAcceptConnections: false
});

function originIsAllowed(origin) {
	// put logic here to detect whether the specified origin is allowed.
	return true;
}

const YIN = '/yin', YANG = '/yang';

const store = {};

function get_peer(my_type) {
	return my_type === YIN ? store[YANG] : store[YIN];
}

wsServer.on('request', function (request) {
	const type = request.resourceURL.href;
	if (type !== YIN && type !== YANG || store[type]) {
		request.reject();
		return;
	}
	if (!originIsAllowed(request.origin)) {
		// Make sure we only accept requests from an allowed origin
		request.reject();
		console.log((new Date()) + ' Connection from origin ' + request.origin + ' rejected.');
		return;
	}

	var connection = request.accept('echo-protocol', request.origin);
	console.log((new Date()) + ' Connection accepted.');

	store[type] = connection;
	connection.on('message', (message) => {
		const peer = get_peer(type);
		if (!peer) {
			return;
		}
		if (message.type === 'utf8') {
			console.log('Received Message: ' + message.utf8Data);
			peer.sendUTF(message.utf8Data);
		}
		else if (message.type === 'binary') {
			// console.log('Received Binary Message of ' + message.binaryData.length + ' bytes');
			peer.sendBytes(message.binaryData);
		}
	});
	connection.on('close', (reasonCode, description) => {
		store[type] = null;
		console.log((new Date()) + ' Peer ' + connection.remoteAddress + ' disconnected.');
	});
});