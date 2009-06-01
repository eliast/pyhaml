import tokenize
import io

raw_input = input

def ex(src, *args):
	return exec(src, *args)

def pt(*args, **kwargs):
	return print(*args, **kwargs)

def tokens(s):
	g = io.BytesIO(bytes(s.encode())).readline
	for tok in tokenize.tokenize(g):
		yield tok

def untokenize(toks):
	return tokenize.untokenize(toks).decode()
