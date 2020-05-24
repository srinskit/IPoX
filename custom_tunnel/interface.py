from pytun import TunTapDevice
from threading import Thread


class NWInterface:
	def __init__(self, tunnel, *args, **kwargs):
		self.tunnel = tunnel
		self.write_thread = Thread(target=NWInterface.write_loop, args=(self,))
		self.read_thread = Thread(target=NWInterface.read_loop, args=(self,))
		self.running = True
		self.tun = TunTapDevice(*args, **kwargs)

	def up(self):
		self.tunnel.up()
		self.tun.up()
		self.running = True
		self.write_thread.start()
		self.read_thread.start()

	def down(self):
		self.tun.down()
		self.tunnel.down()
		self.running = False
		self.read_thread.join()
		self.write_thread.join()

	def write_loop(self):
		try:
			while self.running:
				data = self.tun.read(self.tun.mtu)
				self.tunnel.send(data)
				print('OS -> int', len(data))
		except:
			pass

	def read_loop(self):
		try:
			while self.running:
				data = self.tunnel.recv()
				self.tun.write(data)
				print('int -> OS', len(data))
		except:
			pass
