import socket
from time import sleep

buff_size = 16384
PING = b''
PING_FLAG = b'0'
NEOC_FLAG = b'1'
EOC_FLAG = b'2'


class Client:
	def __init__(self, typ, addr):
		self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.addr = addr
		self.typ = b'1' if typ == 'yin' else b'0'
		self.send(PING)

	def send(self, data):
		if(data == PING):
			return self.soc.sendto(self.typ + PING_FLAG, self.addr)

		payload_size = buff_size - 2
		for i in range(0, len(data), payload_size):
			self.soc.sendto(self.typ + NEOC_FLAG + data[i:i + payload_size], self.addr)
			sleep(0.01)
		self.soc.sendto(self.typ + EOC_FLAG, self.addr)

	def recv(self):
		ret = b''
		while True:
			data, _ = self.soc.recvfrom(buff_size)
			flag = data[1]
			if flag == ord(EOC_FLAG):
				return ret
			ret += data[2:]
