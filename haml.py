import re
import cgi
import sys
from getopt import *
from tokenize import *
from ply.lex import lex
from ply.yacc import yacc

if sys.version_info[0] >= 3:
	raw_input = input
	from io import StringIO
elif sys.version_info[0] < 3:
	tokenize = generate_tokens
	from StringIO import StringIO

def usage():
	sys.stderr.write('usage: python haml.py [-d|--debug] [-h|--help] [(-f|--format)=HTMLFORMAT]\n')

class Options(object):
	
	doctypes = {
		'xhtml': {
			'strict': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
			'transitional': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
			'basic': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.1//EN" "http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd">',
			'mobile': '<!DOCTYPE html PUBLIC "-//WAPFORUM//DTD XHTML Mobile 1.2//EN" "http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">',
			'frameset': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">'
		},
		'html4': {
			'strict': '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">',
			'frameset': '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">',
			'transitional': '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
		},
		'html5': {
			'': '<!doctype html>'
		}
	}
	
	doctypes['xhtml'][''] = doctypes['xhtml']['transitional']
	doctypes['html4'][''] = doctypes['html4']['transitional']
	
	def __init__(self):
		self.format = Options.doctypes['html5']
		self.escape = False
		self.debug = False
	
	def set(self, opts):
		if 'format' in opts:
			self.format = Options.doctypes[opts['format']]
		if 'escape' in opts:
			self.escape = opts['escape']

op = Options()
if __name__ == '__main__':
	try:
		opts, args = getopt(sys.argv[1:], 'ehdf:', ['escape', 'help', 'debug', 'format='])
		for opt, val in opts:
			if opt in ('-d', '--debug'):
				op.debug = True
			elif opt in ('-f', '--format'):
				op.set({ 'format' : val })
			elif opt in ('-e', '--escape'):
				op.set({ 'escape' : True })
	except GetoptError:
		usage()
		sys.exit(2)

class TabInfo(object):
	def __init__(self, lexer):
		self.lexer = lexer
		self.reset()
	
	def reset(self):
		self.type = None
		self.depth = 0
		self.length = None
		self.history = []
	
	def push(self):
		self.history.append(self.depth)
	
	def pop(self):
		self.depth = self.history.pop()
	
	def process(self, s):
		self.lexer.lineno += s.count('\n')
		s = re.sub('[^ \t]', '', s)
		if s == '':
			self.depth = 0
			return
		
		if self.type == None:
			self.type = s[0]
			self.length = len(s)
		
		if s[0] != self.type:
			raise Exception('mixed indentation:[%s]' % self.lexer.lineno)
		
		depth = int(len(s) / self.length)
		if len(s) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation:[%s]' % self.lexer.lineno)
		
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
	
	def __init__(self):
		pass
	
	def reset(self):
		self.tabs.reset()
		self.lexer.begin('INITIAL')
	
	def build(self, **kwargs):
		self.lexer = lex(object=self, **kwargs)
		self.tabs = TabInfo(self.lexer)
		return self
	
	def pytokens(self):
		lexer = self.lexer
		g = StringIO(lexer.lexdata[lexer.lexpos:]).readline
		for token in tokenize(g):
			_, s, _, (_, ecol), _ = token
			yield token
			for _ in range(s.count('\n')):
				lexer.lineno += 1
				lexer.lexpos = lexer.lexdata.find('\n', lexer.lexpos+1) + 1
	
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
		if t.value[-1] == '#':
			self.tabs.push()
			self.tabs.process(t.value)
			self.tabs.start = self.tabs.depth
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
		r'[^=&/#!.%\n\t ][^\n]*'
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
		t.value = ''
		lvl = 0
		t.lexer.lexpos -= 1
		for _, s, _, (_, ecol), _ in self.pytokens():
			t.value += s
			if s == '{':
				lvl += 1
			elif s == '}':
				lvl -= 1
				if lvl == 0:
					t.lexer.lexpos += ecol
					return t
	
	def t_tag_INITIAL_SCRIPT(self, t):
		r'(!|&)?='
		if t.value[0] == '&':
			t.type = 'SANITIZE'
		elif t.value[0] == '!':
			t.type = 'NOSANITIZE'
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

class Comment(object):
	
	def __init__(self, parser, value='', condition=''):
		self.parser = parser
		self.value = value.strip()
		self.condition = condition.strip()
	
	def render(self):
		if self.condition:
			s = '<!--[%s]>' % self.condition
		else:
			s = '<!--'
		if self.value:
			s += ' ' + self.value
		self.parser.push(s)
	
	def close(self):
		if self.condition:
			s = '<![endif]-->'
		else:
			s = '-->'
		if self.value:
			self.parser.buffer[-1] += ' ' + s
		else:
			self.parser.push(s)

class Tag(object):
	
	auto_close = (
		'script',
	)
	
	self_close = (
		'img',
		'script',
	)
	
	def __init__(self, parser, tagname=''):
		self.parser = parser
		self.attrs = {}
		self.tagname = tagname
		self.trim_inner = False
		self.trim_outer = False
		self.self_close = False
		if tagname == '':
			self.tagname = 'div'
	
	def addclass(self, s):
		if not 'class' in self.attrs:
			self.attrs['class'] = s
		else:
			self.attrs['class'] += ' ' + s
	
	def render(self):
		s = '<' + self.tagname
		for k,v in self.attrs.items():
			s += ' %s="%s"' % (k, cgi.escape(str(v), True))
		if self.tagname in Tag.auto_close:
			s += '></' + self.tagname
		elif self.self_close or self.tagname in Tag.self_close:
			s += '/'
		s += '>'
		if self.value:
			s += self.value
		self.parser.push(s, trim_inner=self.trim_inner, trim_outer=self.trim_outer)
	
	def close(self):
		if self.self_close or self.tagname in Tag.self_close:
			self.parser.trim_next = self.trim_outer
		elif self.value or self.parser.last_obj is self:
			self.parser.buffer[-1] += '</' + self.tagname + '>'
			self.parser.trim_next = self.trim_outer
		else:
			self.parser.push('</' + self.tagname + '>', trim_inner=self.trim_outer, trim_outer=self.trim_inner)

class haml_parser(object):
	
	def __init__(self, **kwargs):
		op.set(kwargs)
		self.lexer = haml_lex().build()
		self.tabs = self.lexer.tabs
		self.tokens = self.lexer.tokens
		self.parser = yacc(module=self, debug=op.debug, write_tables=False)
		self.reset()
	
	def reset(self):
		self.html = ''
		self.buffer = []
		self.to_close = []
		self.trim_next = False
		self.last_obj = None
		self.lexer.reset()
	
	def to_html(self, s, **kwargs):
		op.set(kwargs)
		self.reset()
		self.parser.parse(s, lexer=self.lexer.lexer, debug=op.debug)
		return self.html
	
	def close(self, obj):
		if hasattr(obj, 'close'):
			obj.close()
	
	def render(self, obj):
		while len(self.to_close) > self.tabs.depth:
			self.close(self.to_close.pop())
		self.last_obj = obj
		if hasattr(obj, 'render'):
			obj.render()
		else:
			self.push(obj)
		self.to_close.append(obj)
	
	def push(self, s, trim_inner=False, trim_outer=False):
		if trim_outer or self.trim_next:
			if len(self.buffer) == 0:
				self.buffer.append('')
			pre = self.buffer.pop()
		else:
			pre = '  ' * len(self.to_close)
		self.buffer.append(pre + s)
		self.trim_next = trim_inner
	
	def p_haml_doc(self, p):
		'''haml :
				| doc'''
		if len(p) == 2:
			while len(self.to_close) > 0:
				self.close(self.to_close.pop())
			self.html = '\n'.join(self.buffer + [''])
	
	def p_doctype(self, p):
		'''doctype : DOCTYPE'''
		p[0] = op.format['']
	
	def p_htmltype(self, p):
		'''doctype : DOCTYPE HTMLTYPE'''
		p[0] = op.format[p[2]]
	
	def p_xmltype(self, p):
		'''doctype : DOCTYPE XMLTYPE'''
		if p[2] == '':
			p[2] = 'utf-8'
		p[0] = '<?xml version="1.0" encoding="%s"?>' % p[2]
	
	def p_doc(self, p):
		'doc : obj'
		self.render(p[1])
	
	def p_doc_obj(self, p):
		'doc : doc obj'
		self.render(p[2])
	
	def p_doc_indent_obj(self, p):
		'doc : doc INDENT obj'
		self.tabs.process(p[2])
		self.render(p[3])
	
	def p_obj(self, p):
		'''obj : element
			| CONTENT
			| comment
			| condcomment
			| doctype
			| script
			| sanitize
			| nosanitize'''
		p[0] = p[1]
	
	def p_comment(self, p):
		'''comment : COMMENT
				| COMMENT VALUE'''
		if len(p) == 2:
			p[0] = Comment(self)
		elif len(p) == 3:
			p[0] = Comment(self, value=p[2])
	
	def p_condcomment(self, p):
		'''condcomment : CONDCOMMENT
						| CONDCOMMENT VALUE'''
		if len(p) == 2:
			p[0] = Comment(self, condition=p[1])
		elif len(p) == 3:
			p[0] = Comment(self, value=p[2], condition=p[1])
	
	def p_element_tag_trim_dict_value(self, p):
		'element : tag trim dict selfclose value'
		p[0] = p[1]
		p[0].trim_inner = '<' in p[2]
		p[0].trim_outer = '>' in p[2]
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
		p[0] = eval(p[1])
		if op.escape:
			p[0] = cgi.escape(p[0], True)
	
	def p_sanitize(self, p):
		'sanitize : SANITIZE'
		p[0] = cgi.escape(eval(p[1]), True)
	
	def p_nosanitize(self, p):
		'nosanitize : NOSANITIZE'
		p[0] = eval(p[1])
	
	def p_dict(self, p):
		'''dict : 
				| DICT '''
		if len(p) == 1:
			p[0] = {}
		else:
			p[0] = eval(p[1])
	
	def p_tag_tagname(self, p):
		'tag : TAGNAME'
		p[0] = Tag(self, tagname=p[1])
	
	def p_tag_id(self, p):
		'tag : ID'
		p[0] = Tag(self)
		p[0].attrs['id'] = p[1]
	
	def p_tag_class(self, p):
		'tag : CLASSNAME'
		p[0] = Tag(self)
		p[0].addclass(p[1])
	
	def p_tag_tagname_id(self, p):
		'tag : TAGNAME ID'
		p[0] = Tag(self, tagname=p[1])
		p[0].attrs['id'] = p[2]
	
	def p_tag_tag_class(self, p):
		'tag : tag CLASSNAME'
		p[0] = p[1]
		p[0].addclass(p[2])
	
	def p_error(self, p):
		sys.stderr.write('syntax error[%s]\n' % (p,))

parser = haml_parser()

def to_html(s, **kwargs):
	return parser.to_html(s, **kwargs)

if __name__ == '__main__':
	s = []
	while True:
		try:
			s.append(raw_input())
		except EOFError:
			break
	
	sys.stdout.write(to_html('\n'.join(s)))
