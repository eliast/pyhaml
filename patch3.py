import tokenize
import io

raw_input = input

def ex(src, *args):
	return exec(src, *args)

def pt(*args, **kwargs):
	return print(*args, **kwargs)

def tokens(s):
	for tok in tokenize.tokenize(io.BytesIO(bytes(s.encode())).readline):
		type, _, _, _, _ = tok
		if not type == tokenize.ENCODING:
			yield tok
