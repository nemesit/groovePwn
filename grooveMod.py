#!/usr/bin/python

import re

streamURLRegex = re.compile("(http://.*[.]grooveshark[.]com/.*[.]mp3.*|http://stream.*[.]grooveshark[.]com/stream.php)")

class Filter(object):
	def __init__(self, *args, **kwargs):
		pass
	
	def process(self, data):
		return data
	
	def done(self):
		pass

class SongDownloader(Filter):
	"""A filter which will save MP3s which are transferred through the proxy"""
	# A string which will store the song data
	data = ""
	
	# Remember if the headers have been sent yet
	headersFinished = False
	
	def __init__(self, path):
		print "Pwning in progress..."
	
	def process(self, data):
		self.data += data
		return Filter.process(self, data)
	
	def done(self):
		header, song = self.data.split("\r\n\r\n", 2)
		
		# Check that a music file arrived
		if len(song) > 10000:
			mp3File = open("song.mp3","w")
			mp3File.write(song)
			mp3File.close()
			print "Pwning Complete"
		else:
			print "This script got pwn't: Not a music file."
		
		return Filter.done(self)

def getFilter(path):
	if streamURLRegex.match(path):
		return SongDownloader(path)
	else:
		return Filter(path)
