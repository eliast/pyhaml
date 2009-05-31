from __future__ import division

import re
import cgi
import sys
from ply.lex import lex
from ply.yacc import yacc
from optparse import OptionParser

__version__ = '0.1'

if sys.version_info[0] >= 3:
	from patch3 import *
elif sys.version_info[0] < 3:
	from patch2 import *

class TabInfo(object):
	def __init__(self):
		self.reset()
	
	def reset(self):
		self.type = None
		self.depth = 0
		self.length = None
		self.history = []
	
	def push(self, s):
		self.history.append(self.depth)
		self.process(s)
		self.start = self.depth
	
	def pop(self):
		self.depth = self.history.pop()
	
	def process(self, s):
		s = re.sub('[^ \t]', '', s)
		if s == '':
			self.depth = 0
			return self.depth
		
		if self.type == None:
			self.type = s[0]
			self.length = len(s)
		
		if s[0] != self.type:
			raise Exception('mixed indentation')
		
		depth = int(len(s) / self.length)
		if len(s) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation')
		
		self.depth = depth
		return self.depth

class haml_lex(object):

	tokens = (
		'DOCTYPE',
		'HTMLTYPE',
		'XMLTYPE',
		'INDENT',
		'TAGNAME',
		'ID',
		'CLASSNAME',
		'VALUE',
		'CONTENT',
		'TRIM',
		'DICT',
		'SCRIPT',
		'SILENTSCRIPT',
		'SANITIZE',
		'COMMENT',
		'CONDCOMMENT',
		'NOSANITIZE',
	)
	
	states = (
		('tag', 'exclusive'),
		('silent', 'exclusive'),
		('doctype', 'exclusive'),
		('comment', 'exclusive'),
	)
	
	literals = '":,{}<>/'
	t_ignore = '\r'
	t_tag_silent_doctype_comment_ignore = ''
	
	def build(self, **kwargs):
		self.lexer = lex(object=self, **kwargs)
		self.tabs = TabInfo()
		return self
	
	def pytokens(self):
		lexer = self.lexer
		for token in tokens(lexer.lexdata[lexer.lexpos:]):
			_, s, _, (_, ecol), _ = token
			yield token
			for _ in range(s.count('\n')):
				lexer.lineno += 1
				lexer.lexpos = lexer.lexdata.find('\n', lexer.lexpos+1) + 1
	
	def read_dict(self, t):
		t.value = ''
		lvl = 0
		for _, s, _, (_, ecol), _ in self.pytokens():
			t.value += s
			if s == '{':
				lvl += 1
			elif s == '}':
				lvl -= 1
				if lvl == 0:
					t.lexer.lexpos += ecol
					return t
	
	def read_script(self, t):
		t.value = ''
		for _, s, _, (_, ecol), _ in self.pytokens():
			t.value += s
			if s == '\n':
				t.lexer.lexpos += ecol - 1
				t.value = t.value.strip()
				return t
			elif s == '':
				t.lexer.lexpos = len(t.lexer.lexdata)
				return t
	
	def t_silent_indent(self, t):
		r'\n+[ \t]*'
		if self.tabs.process(t.value) <= self.tabs.start:
			self.tabs.pop()
			t.lexer.lexpos -= len(t.value)
			t.lexer.begin('INITIAL')
	
	def t_silent_other(self, t):
		r'[^\n]'
		pass
	
	def t_tag_doctype_comment_INITIAL_INDENT(self, t):
		r'\n+[ \t]*(-\#)?'
		t.lexer.lineno += t.value.count('\n')
		if t.value[-1] == '#':
			self.tabs.push(t.value)
			t.lexer.begin('silent')
		else:
			t.lexer.begin('INITIAL')
			return t
	
	def t_DOCTYPE(self, t):
		r'!!!'
		t.lexer.begin('doctype')
		return t
	
	def t_doctype_XMLTYPE(self, t):
		r'[ ]+XML([ ]+[^\n]+)?'
		t.value = t.value.replace('XML', '', 1).strip()
		return t
	
	def t_doctype_HTMLTYPE(self, t):
		r'[ ]+(strict|frameset|mobile|basic|transitional)'
		t.value = t.value.strip()
		return t

	def t_CONTENT(self, t):
		r'[^=&/#!.%\n\t -][^\n]*'
		if t.value[0] == '\\':
			t.value = t.value[1:]
		return t
	
	def t_CONDCOMMENT(self, t):
		r'/\[[^\]]+\]'
		t.lexer.begin('comment')
		t.value = t.value[2:-1]
		return t
	
	def t_COMMENT(self, t):
		r'/'
		t.lexer.begin('comment')
		return t
	
	def t_comment_VALUE(self, t):
		r'[^\n]+'
		return t

	def t_TAGNAME(self, t):
		r'%[a-zA-Z][a-zA-Z0-9]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t

	def t_ID(self, t):
		r'\#[a-zA-Z][a-zA-Z0-9]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t

	def t_CLASSNAME(self, t):
		r'\.[a-zA-Z-][a-zA-Z0-9-]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t
	
	def t_tag_DICT(self, t):
		r'{'
		t.lexer.lexpos -= 1
		return self.read_dict(t)
	
	def t_tag_INITIAL_SCRIPT(self, t):
		r'='
		return self.read_script(t)
	
	def t_tag_INITIAL_SANITIZE(self, t):
		r'&='
		return self.read_script(t)
	
	def t_tag_INITIAL_NOSANITIZE(self, t):
		r'!='
		return self.read_script(t)
	
	def t_SILENTSCRIPT(self, t):
		r'-'
		return self.read_script(t)
	
	def t_tag_VALUE(self, t):
		r'[ ][^\n]+'
		t.value = t.value.strip()
		return t
	
	def t_tag_TRIM(self, t):
		r'<>|><|<|>'
		return t
	
	def t_tag_silent_doctype_comment_error(self, t):
		self.t_error(t)
	
	def t_error(self, t):
		sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
		t.lexer.skip(1)

class Script(object):
	
	def __init__(self, compiler, value, type='='):
		self.compiler = compiler
		self.value = value
		self.type = type
		if self.type == '&=' or self.type == '=' and self.compiler.op.escape:
			self.value = 'cgi.escape(%s, True)' % self.value
	
	def open(self):
		self.compiler.push(self.value)
	
	def close(self):
		pass

class SilentScript(object):
	
	def __init__(self, compiler, value):
		self.compiler = compiler
		self.value = value
	
	def open(self):
		self.compiler.eval(self.value)
	
	def close(self):
		pass

class Doctype(object):
	
	def __init__(self, compiler, type, xml=False):
		self.compiler = compiler
		self.xml = xml
		self.type = type
	
	def open(self):
		if self.xml:
			s = '<?xml version="1.0" encoding="%s"?>'
			self.compiler.push(repr(s % self.type))
		else:
			s = self.compiler.op.format[self.type]
			self.compiler.push(repr(s))
	
	def close(self):
		pass

class Comment(object):
	
	def __init__(self, compiler, value='', condition=''):
		self.compiler = compiler
		self.value = value.strip()
		self.condition = condition.strip()
	
	def open(self):
		if self.condition:
			s = '<!--[%s]>' % self.condition
		else:
			s = '<!--'
		if self.value:
			s += ' ' + self.value
		self.compiler.push(repr(s))
	
	def close(self):
		if self.condition:
			s = '<![endif]-->'
		else:
			s = '-->'
		if self.value:
			self.compiler.write(repr(' ' + s))
		else:
			self.compiler.push(repr(s))

class Tag(object):
	
	auto_close = (
		'script',
	)
	
	self_close = (
		'img',
		'script',
		'input',
	)
	
	def __init__(self, compiler, tagname=''):
		self.compiler = compiler
		self.attrs = {}
		self.tagname = tagname
		self.inner = False
		self.outer = False
		self.self_close = False
		if tagname == '':
			self.tagname = 'div'
	
	def addclass(self, s):
		if not 'class' in self.attrs:
			self.attrs['class'] = s
		else:
			self.attrs['class'] += ' ' + s
	
	def open(self):
		s = '<' + self.tagname
		for k,v in self.attrs.items():
			s += ' %s="%s"' % (k, cgi.escape(str(v), True))
		if self.tagname in Tag.auto_close:
			s += '></' + self.tagname
		elif self.self_close or self.tagname in Tag.self_close:
			s += '/'
		s += '>'
		self.compiler.push(repr(s), inner=self.inner, outer=self.outer)
		if isinstance(self.value, Script):
			self.compiler.write(self.value.value)
		elif self.value:
			self.compiler.write(repr(self.value))
	
	def close(self):
		if self.self_close or self.tagname in Tag.self_close:
			self.compiler.trim_next = self.outer
		elif self.value or self.compiler.last_obj is self:
			self.compiler.write(repr('</' + self.tagname + '>'))
			self.compiler.trim_next = self.outer
		else:
			self.compiler.push(repr('</' + self.tagname + '>'), inner=self.outer, outer=self.inner)

class haml_parser(object):
	
	tokens = haml_lex.tokens
	
	def __init__(self, compiler):
		self.compiler = compiler
		self.parser = yacc(module=self, write_tables=False)
	
	def parse(self, *args, **kwargs):
		self.parser.parse(*args, **kwargs)
	
	def p_haml_doc(self, p):
		'''haml :
				| doc'''
		pass
	
	def p_doc(self, p):
		'doc : obj'
		self.compiler.open(p[1])
	
	def p_doc_obj(self, p):
		'doc : doc obj'
		self.compiler.open(p[2])
	
	def p_doc_indent_obj(self, p):
		'doc : doc INDENT obj'
		self.compiler.lexer.tabs.process(p[2])
		self.compiler.open(p[3])
	
	def p_obj(self, p):
		'''obj : element
			| CONTENT
			| comment
			| condcomment
			| doctype
			| script
			| sanitize
			| nosanitize
			| silentscript'''
		p[0] = p[1]
	
	def p_doctype(self, p):
		'''doctype : DOCTYPE'''
		p[0] = self.compiler.op.format['']
	
	def p_htmltype(self, p):
		'''doctype : DOCTYPE HTMLTYPE'''
		p[0] = Doctype(self.compiler, p[2])
	
	def p_xmltype(self, p):
		'''doctype : DOCTYPE XMLTYPE'''
		if p[2] == '':
			p[2] = 'utf-8'
		p[0] = Doctype(self.compiler, p[2], xml=True)
	
	def p_comment(self, p):
		'''comment : COMMENT
				| COMMENT VALUE'''
		if len(p) == 2:
			p[0] = Comment(self.compiler)
		elif len(p) == 3:
			p[0] = Comment(self.compiler, value=p[2])
	
	def p_condcomment(self, p):
		'''condcomment : CONDCOMMENT
						| CONDCOMMENT VALUE'''
		if len(p) == 2:
			p[0] = Comment(self.compiler, condition=p[1])
		elif len(p) == 3:
			p[0] = Comment(self.compiler, value=p[2], condition=p[1])
	
	def p_element_tag_trim_dict_value(self, p):
		'element : tag trim dict selfclose value'
		p[0] = p[1]
		p[0].inner = '<' in p[2]
		p[0].outer = '>' in p[2]
		p[0].attrs.update(p[3])
		p[0].self_close = p[4]
		p[0].value = p[5]
	
	def p_selfclose(self, p):
		'''selfclose :
					| '/' '''
		if len(p) == 1:
			p[0] = False
		elif len(p) == 2:
			p[0] = True
	
	def p_trim(self, p):
		'''trim :
			| TRIM'''
		if len(p) == 1:
			p[0] = ''
		else:
			p[0] = p[1]
	
	def p_value(self, p):
		'''value :
				| VALUE
				| script
				| sanitize
				| nosanitize'''
		if len(p) == 1:
			p[0] = None
		elif len(p) == 2:
			p[0] = p[1]
	
	def p_script(self, p):
		'script : SCRIPT'
		p[0] = Script(self.compiler, p[1])
	
	def p_sanitize(self, p):
		'sanitize : SANITIZE'
		p[0] = Script(self.compiler, p[1], type='&=')
	
	def p_nosanitize(self, p):
		'nosanitize : NOSANITIZE'
		p[0] = Script(self.compiler, p[1], type='!=')
	
	def p_silentscript(self, p):
		'silentscript : SILENTSCRIPT'
		p[0] = SilentScript(self.compiler, p[1])
	
	def p_dict(self, p):
		'''dict : 
				| DICT '''
		if len(p) == 1:
			p[0] = {}
		else:
			p[0] = eval(p[1], {}, self.compiler.locals)
	
	def p_tag_tagname(self, p):
		'tag : TAGNAME'
		p[0] = Tag(self.compiler, tagname=p[1])
	
	def p_tag_id(self, p):
		'tag : ID'
		p[0] = Tag(self.compiler)
		p[0].attrs['id'] = p[1]
	
	def p_tag_class(self, p):
		'tag : CLASSNAME'
		p[0] = Tag(self.compiler)
		p[0].addclass(p[1])
	
	def p_tag_tagname_id(self, p):
		'tag : TAGNAME ID'
		p[0] = Tag(self.compiler, tagname=p[1])
		p[0].attrs['id'] = p[2]
	
	def p_tag_tag_class(self, p):
		'tag : tag CLASSNAME'
		p[0] = p[1]
		p[0].addclass(p[2])
	
	def p_error(self, p):
		sys.stderr.write('syntax error[%s]\n' % (p,))

class haml_compiler(object):
	
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
		help='display lex/yacc debugging information',
		action='store_true',
		dest='debug',
		default=False)

	optparser.add_option('-f', '--format',
		help='html output format: html5, html4, xhtml',
		type='choice',
		choices=['html5', 'html4', 'xhtml'],
		default=doctypes['html5'],
		action='callback',
		callback=lambda op, o, v, p: setattr(p.values, 'format', haml_compiler.doctypes[v]))

	optparser.add_option('-e', '--escape',
		help='sanitize values by default',
		action='store_true',
		dest='escape',
		default=False)
	
	def __init__(self):
		self.lexer = haml_lex().build()
		self.parser = haml_parser(self)
		self.reset()
	
	def reset(self):
		self.lexer.lexer.begin('INITIAL')
		self.lexer.tabs.reset()
		self.src = [
			'import cgi',
			'html = ""',
		]
		self.to_close = []
		self.trim_next = False
		self.last_obj = None
		self.locals = {}
	
	def to_html(self, s, *args, **kwargs):
		s = s.strip()
		if s == '':
			return ''
		self.reset()
		if len(args) > 0:
			self.locals, = args
		if 'args' in kwargs:
			argv = kwargs['args']
		else:
			argv = []
			for k,v in kwargs.items():
				if isinstance(v, bool):
					argv += ['--' + k] if v else []
				else:
					argv += ['--' + k, str(v)]
		self.op, _ = haml_compiler.optparser.parse_args(argv)
		self.parser.parse(s,
			lexer=self.lexer.lexer,
			debug=self.op.debug)
		while len(self.to_close) > 0:
			self.close(self.to_close.pop())
		self.src += ['html = html.strip() + "\\n"']
		src = '\n'.join(self.src)
		if self.op.debug:
			pt(src)
		ex(compile(src, '<string>', 'exec'), {}, self.locals)
		return self.locals['html']
	
	def close(self, obj):
		if hasattr(obj, 'close'):
			obj.close()
	
	def open(self, obj):
		while len(self.to_close) > self.lexer.tabs.depth:
			self.close(self.to_close.pop())
		self.last_obj = obj
		if hasattr(obj, 'open'):
			obj.open()
		else:
			self.push(repr(obj))
		self.to_close.append(obj)
	
	def push(self, s, inner=False, outer=False):
		if outer or self.trim_next:
			self.write(s)
		else:
			self.src += ['html += "\\n"']
			self.write(repr('  ' * len(self.to_close)))
			self.write(s)
		self.trim_next = inner
	
	def write(self, s):
		self.src += ['html += str(%s)' % s]
	
	def eval(self, *args):
		self.src += args
	

to_html = haml_compiler().to_html

if __name__ == '__main__':
	sys.stdout.write(to_html(sys.stdin.read(), args = sys.argv[1:]))
