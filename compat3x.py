import tokenize
from io import StringIO, BytesIO

def ex(src, *args):
	return exec(src, *args)

def pt(*args, **kwargs):
	return print(*args, **kwargs)

def tokens(s):
	for tok in tokenize.tokenize(BytesIO(bytes(s.encode())).readline):
		type, _, _, _, _ = tok
		if not type == tokenize.ENCODING:
			yield tok
