#!/usr/bin/python
import BaseHTTPServer, socket, select, urlparse, SocketServer

# The timeout (secs) to wait for a socket to become available
WAIT_TIMEOUT = 1

# Number of 1kb blocks to transfer per cycle
BLOCK_SIZE = 1

def addressToTuple(addressString):
	"""
	Convert a computer address with/without a port numbre into a tuple containing
	the address and port.
	"""
	address, _ , port = addressString.partition(":")
	if port != "":
		port = int(port)
	else:
		port = 80
	return (address, port)

def otherItem(tuple, element):
	"""Return the other element from a two-element tuple given one element"""
	if tuple[0] == element:
		return tuple[1]
	else:
		return tuple[0]

class GroovePwnProxy(BaseHTTPServer.BaseHTTPRequestHandler):
	def _canConnectToTarget(self, targetAddressString, soc):
		"""
		Opens a connection to a remote system via the provided socket and
		responds with the sucess of the operation.
		"""
		target = addressToTuple(targetAddressString)
		try:
			# The provided socket is now propperly connected
			soc.connect(target)
			return True
		except socket.error, messageList:
			# Couldn't connect: inform the client
			try:    message = messageList[1]
			except: message = messageList
			self.send_error(404, message)
			return False
	
	def _streamData(self, remoteSiteSocket, maxIdleTimeout=20):
		"""
		Attempt to stream data from the remote socket to the client in blocks of
		1Kbyte. maxIdleTimeout is the maximum number of idle responses to tolerate
		before ending the stream.
		"""
		# A list of sockets which are to be connected
		streamSockets = (self.connection, remoteSiteSocket)
		
		# The number of consecutive attempts to read the data which have resulted in
		# an idle response.
		idleResponseCount = 0
		
		while True:
			# Wait until a socket is ready to read
			readySockets, _ , errSockets = select.select(streamSockets, [],
			                                             streamSockets, WAIT_TIMEOUT)
			if errSockets:
				# An exceptional state has occurred on one of the sockets
				break
			else:
				# For each socket which is ready, read from it
				for readSocket in readySockets:
					writeSocket = otherItem(streamSockets, readSocket)
					
					# Read 1Kbyte from the socket
					data = readSocket.recv(BLOCK_SIZE * 1024 * 8)
					if data:
						# Data was recieved, forward it on
						writeSocket.send(data)
						idleResponseCount = 0
					else:
						# Data was not recieved -- idle/timeout
						idleResponseCount += 1
			
			# Exit if the response count has been reached
			if idleResponseCount >= maxIdleTimeout:
				break
	
	def do_CONNECT(self):
		remoteSiteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			if self._canConnectToTarget(self.path, remoteSiteSocket):
				# A connection has been established, send the header
				self.wfile.write(self.protocol_version
				                 + " 200 Connection established\r\n")
				self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
				self.wfile.write("\r\n")
				
				self._streamData(remoteSiteSocket, maxIdleTimeout=300)
		finally:
			remoteSiteSocket.close()
			self.connection.close()
	
	def do_GET(self):
		url = urlparse.urlparse(self.path, "http")
		
		# If the url is not for a HTTP protocal address, has a fragment or has no
		# location specified then this script cannot handle it.
		if url.scheme != "http" or url.fragment or not url.netloc:
			self.send_error(400, "Bad URL: %s"%(self.path,))
			return False
		
		# Create a socket for the remote server
		remoteSiteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			if self._canConnectToTarget(url.netloc, remoteSiteSocket):
				# Format a URL for the remote site's request header
				formattedURL = urlparse.urlunparse(( "", "",
					url.path,
					url.params,
					url.query, ""
				))
				
				# The top of the header indicating the connection details
				headerTop = "%s %s %s\r\n"%(
					self.command, # e.g. GET, HEAD, etc.
					formattedURL,
					self.request_version
				)
				
				# Inform the remote site that the connection to it will cease
				self.headers['Connection'] = 'close'
				del self.headers['Proxy-Connection']
				
				# Send the header top
				remoteSiteSocket.send(headerTop)
				
				# Send headers to the client
				for key_val in self.headers.items():
					remoteSiteSocket.send("%s: %s\r\n"%key_val)
				
				# End the header data
				remoteSiteSocket.send("\r\n")
				
				# Stream data between the client and remote site
				self._streamData(remoteSiteSocket)
		finally:
			remoteSiteSocket.close()
			self.connection.close()
	
	do_DELETE = do_GET
	do_HEAD = do_GET
	do_POST = do_GET
	do_PUT = do_GET


# Add threadding support to the minimal HTTP server
class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer):
	pass

def startServer(port=8080):
	"""Start a proxy server to pwn grooveshark through"""
	hostname = ""
	serverAddress = (hostname, port)
	
	server = ThreadingHTTPServer(serverAddress, GroovePwnProxy)
	server.serve_forever()

if __name__ == "__main__":
	startServer()
