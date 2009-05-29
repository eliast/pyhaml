from __future__ import division

import tokenize
from StringIO import StringIO

def ex(src, *args):
	if len(args) >= 2:
		glob, loc = args
		exec src in glob, loc
	elif len(args) == 1:
		glob, = args
		exec src in glob
	else:
		exec src

def pt(*args, **kwargs):
	for a in args:
		print a,
	print

def tokens(s):
	return tokenize.generate_tokens(StringIO(s).readline)
