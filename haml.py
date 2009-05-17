import re
import cgi
import sys
from tokenize import *
from ply.lex import lex
from ply.yacc import yacc

if sys.version_info[0] >= 3:
	raw_input = input
	from io import StringIO
elif sys.version_info[0] < 3:
	tokenize = generate_tokens
	from StringIO import StringIO

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
		'INDENT',
		'TAGNAME',
		'ID',
		'CLASSNAME',
		'VALUE',
		'CONTENT',
		'TRIM',
		'DICT',
		'SCRIPT',
	)
	
	states = (
		('tag', 'inclusive'),
		('silent', 'exclusive'),
	)
	
	literals = '":,{}<>/'
	t_ignore = '\r'
	t_silent_ignore = ''
	
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
	
	def t_INDENT(self, t):
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
		return t

	def t_CONTENT(self, t):
		r'[^/#!.%\n ][^\n]*'
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
	
	def t_tag_SCRIPT(self, t):
		r'='
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
		r'<|>|<>|><'
		return t
	
	def t_tag_silent_error(self, t):
		self.t_error(t)
	
	def t_error(self, t):
		sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
		t.lexer.skip(1)

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
	
	def __init__(self):
		self.lexer = haml_lex().build()
		self.tabs = self.lexer.tabs
		self.tokens = self.lexer.tokens
		self.parser = yacc(module=self, debug='-d' in sys.argv, write_tables=False)
		self.reset()
	
	def reset(self):
		self.html = ''
		self.buffer = []
		self.to_close = []
		self.trim_next = False
		self.last_obj = None
		self.lexer.reset()
	
	def to_html(self, s):
		self.reset()
		self.parser.parse(s, lexer=self.lexer.lexer, debug='-d' in sys.argv)
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
	
	def p_doc_doctype(self, p):
		'doc : DOCTYPE'
		self.buffer.append('<!doctype html>')
	
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
	
	def p_obj_element(self, p):
		'''obj : element
			| CONTENT'''
		p[0] = p[1]
	
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
				| script'''
		if len(p) == 1:
			p[0] = None
		elif len(p) == 2:
			p[0] = p[1]
	
	def p_script(self, p):
		'script : SCRIPT'
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

def to_html(s):
	return parser.to_html(s)

if __name__ == '__main__':
	s = []
	while True:
		try:
			s.append(raw_input())
		except EOFError:
			break
	
	sys.stdout.write(to_html('\n'.join(s)))
