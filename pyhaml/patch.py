from __future__ import division

import sys
import tokenize

if sys.version_info[0] >= 3:
	import io
	from .patch3 import ex
	
	raw_input = input
	StringIO = io.StringIO
	
	def toks(s):
		g = io.BytesIO(bytes(s.encode())).readline
		return (t for t in tokenize.tokenize(g))
	
	def untokenize(toks):
		return tokenize.untokenize(toks).decode()
else:
	from .patch2 import ex
	from StringIO import StringIO
	
	def toks(s):
		return tokenize.generate_tokens(StringIO(s).readline)
	
	def untokenize(toks):
		return tokenize.untokenize(toks)
