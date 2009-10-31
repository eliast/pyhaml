from __future__ import division

import re
import os
import imp
import cgi
import sys
from optparse import OptionParser

if __name__ == '__main__' and __package__ == None:
	__package__ = 'pyhaml'

from . import lexer,parser
from .ply import lex, yacc
from .patch import ex

__version__ = '0.1'
	
class haml_loader(object):
	
	def __init__(self, engine, path):
		self.engine = engine
		self.path = path
	
	def load_module(self, fullname):
		return self.engine.load_module(fullname, self.path, self)

class haml_finder(object):
	
	def __init__(self, engine):
		self.engine = engine
	
	def find_module(self, fullname, path=None):
		return self.engine.find_module(fullname)

class engine(object):
	
	doctypes = {
		'xhtml': {
			'strict':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
				'"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
			'transitional':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
				'"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
			'basic':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.1//EN" '
				'"http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd">',
			'mobile':
				'<!DOCTYPE html PUBLIC "-//WAPFORUM//DTD XHTML Mobile 1.2//EN" '
				'"http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">',
			'frameset':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" '
				'"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">'
		},
		'html4': {
			'strict':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" '
				'"http://www.w3.org/TR/html4/strict.dtd">',
			'frameset':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" '
				'"http://www.w3.org/TR/html4/frameset.dtd">',
			'transitional':
				'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
				'"http://www.w3.org/TR/html4/loose.dtd">'
		},
		'html5': {
			'': '<!doctype html>'
		}
	}
	
	doctypes['xhtml'][''] = doctypes['xhtml']['transitional']
	doctypes['html4'][''] = doctypes['html4']['transitional']
	
	usage = 'usage: %prog [-d|--debug] [-h|--help] [-e|--escape] [(-f|--format)=(html5|html4|xhtml)]'
	optparser = OptionParser(usage, version='%%prog %s' % __version__)
	
	optparser.add_option('-d', '--debug',
		help='display debugging information',
		action='store_true',
		dest='debug',
		default=False)

	optparser.add_option('-f', '--format',
		help='html output format: html5, html4, xhtml',
		type='choice',
		choices=['html5', 'html4', 'xhtml'],
		default=doctypes['html5'],
		action='callback',
		callback=lambda op, o, v, p: setattr(p.values, 'format', engine.doctypes[v]))

	optparser.add_option('-e', '--escape',
		help='sanitize values by default',
		action='store_true',
		dest='escape',
		default=False)
	
	optparser.add_option('-p', '--path',
		help='haml import path',
		default='',
		dest='path')
	
	def __init__(self):
		self.parser = yacc.yacc(
			module=parser,
			write_tables=False)
		self.lexer = lex.lex(module=lexer)
	
	def reset(self):
		self.depth = 0
		self.html = []
		self.globals = {
			'__write__': self.write,
			'__escape__': self.escape,
			'__attrs__': self.attrs,
			'__indent__': self.indent,
			'__entab__': self.entab,
			'__detab__': self.detab,
			'__imp__': self.imp,
		}
	
	def setops(self, *args, **kwargs):
		if 'args' in kwargs:
			argv = kwargs['args']
		else:
			argv = []
			for k,v in kwargs.items():
				if isinstance(v, bool):
					argv += ['--' + k] if v else []
				else:
					argv += ['--' + k, str(v)]
		self.op, _ = engine.optparser.parse_args(argv)
	
	def find_module(self, fullname):
		dir = os.path.dirname(self.op.path)
		path = os.path.join(dir, '%s.haml' % fullname)
		if os.path.exists(path):
			return haml_loader(self, path)
		return None
	
	def load_module(self, fullname, path, loader):
		f = open(path)
		try:
			src = f.read()
		finally:
			f.close()
		mod = imp.new_module(fullname)
		mod = sys.modules.setdefault(fullname, mod)
		mod.__file__ = path
		mod.__loader__ = loader
		src = self.compile(src)
		mod.__dict__.update(self.globals)
		ex(src, mod.__dict__)
		return mod
	
	def imp(self, fullname):
		finder = haml_finder(self)
		loader = finder.find_module(fullname)
		if loader:
			return loader.load_module(fullname)
		return None
	
	def entab(self):
		self.depth += 1
	
	def detab(self):
		self.depth -= 1
	
	def indent(self):
		self.write('\n' + '  ' * self.depth)
	
	def write(self, s):
		self.html.append(s)
	
	def escape(self, s):
		self.write(cgi.escape(s, True))
	
	def attrs(self, *args):
		attrs = {}
		for a in args:
			attrs.update(a)
		for k,v in attrs.items():
			self.write(' %s="%s"' % (k, str(v).replace('"', '&quot;')))
	
	def compile(self, s):
		self.parser.depth = 0
		self.parser.src = []
		self.parser.trim_next = False
		self.parser.last_obj = None
		self.parser.debug = self.op.debug
		self.parser.op = self.op
		
		self.lexer.begin('INITIAL')
		self.lexer.tabs = lexer.Tabs()
		self.lexer.depth = 0
		
		self.parser.parse(s, lexer=self.lexer, debug=self.op.debug)
		return '\n'.join(self.parser.src)
	
	def to_html(self, s, *args, **kwargs):
		s = s.strip()
		if s == '':
			return ''
		
		self.reset()
		self.setops(*args, **kwargs)
		
		if len(args) > 0:
			self.globals.update(args[0])
		
		src = self.compile(s)
		if self.op.debug:
			sys.stdout.write(src)
		finder = haml_finder(self)
		sys.meta_path.append(finder)
		try:
			ex(src, self.globals, {})
			return ''.join(self.html).strip() + '\n'
		finally:
			sys.meta_path.remove(finder)
	
	def render(self, path, *args, **kwargs):
		f = open(path)
		try:
			return self.to_html(f.read(), path=path, *args, **kwargs)
		finally:
			f.close()

en = engine()
to_html = en.to_html
render = en.render

if __name__ == '__main__':
	en.setops(args=sys.argv[1:])
	if en.op.path:
		sys.stdout.write(render(en.op.path, args=sys.argv[1:]))
	else:
		sys.stdout.write(to_html(sys.stdin.read(), args=sys.argv[1:]))
