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

class haml_obj(object):
	
	def __init__(self, compiler):
		self.compiler = compiler
		self.lexer = self.compiler.lexer.lexer
		self.lineno = self.lexer.lineno
	
	def push(self, *args, **kwargs):
		self.compiler.push(*args, **kwargs)
	
	def write(self, *args, **kwargs):
		self.compiler.write(*args, **kwargs)
	
	def script(self, *args, **kwargs):
		self.compiler.script(*args, **kwargs)
	
	def enblock(self, *args, **kwargs):
		self.compiler.enblock(*args, **kwargs)
	
	def deblock(self, *args, **kwargs):
		self.compiler.deblock(*args, **kwargs)
	
	def open(self):
		pass
	
	def close(self):
		pass
	
	def no_nesting(self):
		if not self.compiler.last_obj is self:
			self.error('illegal nesting')
	
	def error(self, msg):
		msg = 'line %s: %s' % (self.lineno, msg)
		raise Exception(msg)

class Content(haml_obj):
	
	def __init__(self, compiler, value):
		haml_obj.__init__(self, compiler)
		self.value = value
	
	def open(self):
		self.push(self.value, literal=True)
	
	def close(self):
		self.no_nesting()

class Script(haml_obj):
	
	def __init__(self, compiler, value, type='='):
		haml_obj.__init__(self, compiler)
		self.value = value
		self.type = type
		self.escape = False
		if self.type == '&=':
			self.escape = True
		elif self.type == '=' and self.compiler.op.escape:
			self.escape = True
	
	def open(self):
		self.push(self.value, escape=self.escape)
	
	def close(self):
		pass

class SilentScript(haml_obj):
	
	def __init__(self, compiler, value):
		haml_obj.__init__(self, compiler)
		self.value = value
	
	def open(self):
		self.script(self.value)
		self.enblock()
	
	def close(self):
		self.deblock()

class Doctype(haml_obj):
	
	def __init__(self, compiler):
		haml_obj.__init__(self, compiler)
		self.xml = False
		self.type = ''
	
	def open(self):
		if self.xml:
			s = '<?xml version="1.0" encoding="%s"?>'
			self.push(s % self.type, literal=True)
		else:
			s = self.compiler.op.format[self.type]
			self.push(s, literal=True)
	
	def close(self):
		self.no_nesting()

class Comment(haml_obj):
	
	def __init__(self, compiler, value='', condition=''):
		haml_obj.__init__(self, compiler)
		self.value = value.strip()
		self.condition = condition.strip()
	
	def open(self):
		if self.condition:
			s = '<!--[%s]>' % self.condition
		else:
			s = '<!--'
		if self.value:
			s += ' ' + self.value
		self.push(s, literal=True)
	
	def close(self):
		if self.condition:
			s = '<![endif]-->'
		else:
			s = '-->'
		if self.value:
			self.write(' ' + s, literal=True)
		else:
			self.push(s, literal=True)

class Tag(haml_obj):
	
	auto_close = (
		'script',
	)
	
	self_close = (
		'img',
		'input',
		'link',
	)
	
	def __init__(self, compiler, tagname='', id='', classname=''):
		haml_obj.__init__(self, compiler)
		self.attrs = {}
		if id:
			self.attrs['id'] = id
		if classname:
			self.attrs['class'] = classname
		self.dict = ''
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
	
	def auto_closing(self):
		if self.value:
			return True
		elif self.tagname in Tag.auto_close:
			return True
		elif self.compiler.last_obj is self:
			return True
		return False
	
	def self_closing(self):
		if self.value:
			return False
		elif self.self_close:
			return True
		elif self.tagname in Tag.self_close:
			return True
		return False
	
	def open(self):
		if self.self_close and self.value:
			self.error('self-closing tags cannot have content')
		
		self.push('<' + self.tagname,
			inner=self.inner,
			outer=self.outer,
			literal=True)
		self.script('attrs(%s, %s)' % (self.dict, repr(self.attrs)))
		
		if self.value:
			self.write('>', literal=True)
			if isinstance(self.value, Script):
				script = self.value
				self.write(script.value, escape=script.escape)
			else:
				self.write(self.value, literal=True)
		else:
			if self.self_closing():
				self.no_nesting()
				self.write('/', literal=True)
			self.write('>', literal=True)
	
	def close(self):
		if self.value or self.self_close:
			self.no_nesting()
		
		if self.auto_closing() and not self.self_closing():
			self.write('</%s>' % self.tagname, literal=True)
		
		if self.auto_closing() or self.self_closing():
			self.compiler.trim_next = self.outer
		else:
			self.push('</' + self.tagname + '>', inner=self.outer, outer=self.inner, literal=True)

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
		
		if ' ' in s and '\t' in s:
			raise Exception('mixed indentation')
		
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
	
	def __init__(self, compiler):
		self.compiler = compiler
	
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
		t.value = []
		lvl = 0
		for token in self.pytokens():
			_, s, _, (_, ecol), _ = token
			t.value += [token]
			if s == '{':
				lvl += 1
			elif s == '}':
				lvl -= 1
				if lvl == 0:
					t.lexer.lexpos += ecol
					t.value = untokenize(t.value)
					return t
	
	def read_script(self, t):
		t.value = []
		for token in self.pytokens():
			_, s, _, (_, ecol), _ = token
			if s == '':
				t.lexer.lexpos = len(t.lexer.lexdata)
				t.value = untokenize(t.value)
				return t
			t.value += [token]
			if s == '\n':
				t.lexer.lexpos += ecol - 1
				t.value = untokenize(t.value).strip()
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
		t.value = Doctype(self.compiler)
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
		t.value = Tag(self.compiler, tagname=t.value[1:])
		return t

	def t_tag_INITIAL_ID(self, t):
		r'\#[a-zA-Z][a-zA-Z0-9]*'
		t.value = t.value[1:]
		if t.lexer.lexstate != 'tag':
			t.value = Tag(self.compiler, id=t.value)
		t.lexer.begin('tag')
		return t

	def t_tag_INITIAL_CLASSNAME(self, t):
		r'\.[a-zA-Z-][a-zA-Z0-9-]*'
		t.value = t.value[1:]
		if t.lexer.lexstate != 'tag':
			t.value = Tag(self.compiler, classname=t.value)
		t.lexer.begin('tag')
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
	
	def t_ANY_error(self, t):
		sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
		t.lexer.skip(1)

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
			| content
			| comment
			| condcomment
			| doctype
			| script
			| sanitize
			| nosanitize
			| silentscript'''
		p[0] = p[1]
	
	def p_content(self, p):
		'content : CONTENT'
		p[0] = Content(self.compiler, p[1])
	
	def p_doctype(self, p):
		'''doctype : DOCTYPE'''
		p[0] = p[1]
	
	def p_htmltype(self, p):
		'''doctype : DOCTYPE HTMLTYPE'''
		p[0] = p[1]
		p[0].type = p[2]
	
	def p_xmltype(self, p):
		'''doctype : DOCTYPE XMLTYPE'''
		p[0] = p[1]
		if p[2] == '':
			p[2] = 'utf-8'
		p[0].type = p[2]
		p[0].xml = True
	
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
		p[0].dict = p[3]
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
			p[0] = '{}' 
		else:
			p[0] = p[1]
	
	def p_tag_tagname(self, p):
		'tag : TAGNAME'
		p[0] = p[1]
	
	def p_tag_id(self, p):
		'tag : ID'
		p[0] = p[1]
	
	def p_tag_class(self, p):
		'tag : CLASSNAME'
		p[0] = p[1]
	
	def p_tag_tagname_id(self, p):
		'tag : TAGNAME ID'
		p[0] = p[1]
		p[0].attrs['id'] = p[2]
	
	def p_tag_tag_class(self, p):
		'tag : tag CLASSNAME'
		p[0] = p[1]
		p[0].addclass(p[2])
	
	def p_error(self, p):
		sys.stderr.write('syntax error[%s]\n' % (p,))

class haml_compiler(object):
	
	def __init__(self):
		self.lexer = haml_lex(self).build()
		self.parser = haml_parser(self)
		self.reset()
	
	def reset(self):
		self.lexer.lexer.begin('INITIAL')
		self.lexer.tabs.reset()
		self.depth = 0
		self.src = []
		self.to_close = []
		self.trim_next = False
		self.last_obj = None
	
	def compile(self, s, *args, **kwargs):
		self.reset()
		self.parser.parse(s,
			lexer=self.lexer.lexer,
			debug=self.op.debug)
		while len(self.to_close) > 0:
			self.close(self.to_close.pop())
		return '\n'.join(self.src)
	
	def close(self, obj):
		obj.close()
	
	def open(self, obj):
		while len(self.to_close) > self.lexer.tabs.depth:
			self.close(self.to_close.pop())
		self.last_obj = obj
		obj.open()
		self.to_close.append(obj)
	
	def enblock(self):
		self.depth += 1
	
	def deblock(self):
		self.depth -= 1
	
	def push(self, s, inner=False, outer=False, **kwargs):
		if outer or self.trim_next:
			self.write(s, **kwargs)
		else:
			self.write('\n', literal=True)
			i = len(self.to_close) - self.depth
			if i:
				self.write('  ' * i, literal=True)
			self.write(s, **kwargs)
		self.trim_next = inner
	
	def write(self, s, literal=False, escape=False):
		if literal:
			s = repr(s)
		else:
			s = 'str(%s)' % s
		if escape:
			f = 'escape'
		else:
			f = 'write'
		self.script('%s(%s)' % (f, s))
	
	def script(self, s):
		pre = ' ' * self.depth
		self.src += [pre + s]

class haml_engine(object):
	
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
		callback=lambda op, o, v, p: setattr(p.values, 'format', haml_engine.doctypes[v]))

	optparser.add_option('-e', '--escape',
		help='sanitize values by default',
		action='store_true',
		dest='escape',
		default=False)
	
	def __init__(self):
		self.compiler = haml_compiler()
	
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
		self.op, _ = haml_engine.optparser.parse_args(argv)
		self.compiler.op = self.op
	
	def to_html(self, s, *args, **kwargs):
		self.setops(*args, **kwargs)
		s = s.strip()
		if s == '':
			return ''
		
		html = []
		def write(s):
			html.append(s)
		
		def escape(s):
			write(cgi.escape(s, True))
		
		def attrs(*args):
			attrs = {}
			for a in args:
				attrs.update(a)
			for k,v in attrs.items():
				write(' %s="%s"' % (k, cgi.escape(str(v), True)))
			
		glob = {
			'write': write,
			'attrs': attrs,
			'escape': escape
		}
		loc = {}
		if len(args) > 0:
			loc, = args
		src = self.compiler.compile(s, *args, **kwargs)
		if self.op.debug:
			pt(src)
		ex(compile(src, '<string>', 'exec'), glob, loc)
		return ''.join(html).strip() + '\n'
	
	def render(self, path, *args, **kwargs):
		f = open(path)
		try:
			return self.to_html(f.read(), *args, **kwargs)
		finally:
			f.close()

engine = haml_engine()
to_html = engine.to_html
render = engine.render

if __name__ == '__main__':
	sys.stdout.write(to_html(sys.stdin.read(), args = sys.argv[1:]))
