
def ex(src, *args):
	if len(args) >= 2:
		glob, loc = args
		exec src in glob, loc
	elif len(args) == 1:
		glob, = args
		exec src in glob
	else:
		exec src
