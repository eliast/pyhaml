clean:
	find . -name *.pyc | xargs rm -f
	rm -f parser.out
	rm -f test/haml/*.py
