from websocket import WebSocket


class WSTunnel:
	def __init__(self, *args, **kwargs):
		self.ws = WebSocket(*args, **kwargs)

	def send(self, data):
		return self.ws.send_binary(data)

	def recv(self):
		return self.ws.recv()

	def connect(self, *args, **kwargs):
		self.ws.connect(*args, **kwargs)

	def up(self):
		pass

	def down(self):
		self.ws.close()
