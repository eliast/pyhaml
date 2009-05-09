import sys
sys.path.append('ply')

if sys.version_info[0] >= 3:
	raw_input = input

import lex
import yacc

tokens = (
	'DOCTYPE',
	'TAGNAME',
	'ID',
	'CLASSNAME',
	'INDENTATION',
	'LITERAL',
	'CURLY',
	'VALUE',
	'CONTENT',
	'TRIM',
)

def HamlLexer():
	
	states = (
		('hash', 'exclusive'),
		('tag', 'inclusive'),
	)
	
	literals = '"=:,{}<>/'
	t_ignore = ''
	t_hash_ignore = ' \t\n'
	
	def t_DOCTYPE(t):
		r'!!!'
		return t

	def t_INDENTATION(t):
		r'\n+[ \t]*'
		t.lexer.begin('INITIAL')
		t.lexer.lineno += t.value.count('\n')
		t.value = t.value.replace('\n', '')
		return t
	
	def t_CONTENT(t):
		r'[^/#!.%\n ][^\n]*'
		return t

	def t_TAGNAME(t):
		r'%[a-zA-Z][a-zA-Z0-9]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t

	def t_ID(t):
		r'\#[a-zA-Z][a-zA-Z0-9]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t

	def t_CLASSNAME(t):
		r'\.[a-zA-Z-][a-zA-Z0-9-]*'
		t.lexer.begin('tag')
		t.value = t.value[1:]
		return t
	
	def t_tag_CURLY(t):
		r'{'
		t.lexer.begin('hash')
		return t
	
	def t_tag_VALUE(t):
		r'[ ][^\n]+'
		t.value = t.value.strip()
		return t
	
	def t_tag_TRIM(t):
		r'<|>|<>|><'
		return t
	
	def t_hash_LITERAL(t):
		r'[a-zA-Z]+'
		return t
	
	def t_hash_CURLY(t):
		r'}'
		t.lexer.begin('tag')
		return t
	
	def t_hash_error(t):
		sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
		t.lexer.skip(1)
	
	def t_error(t):
		sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
		t.lexer.skip(1)
	
	return lex.lex()

class TabInfo:
	def __init__(self):
		self.type = None
		self.depth = 0
		self.length = None
	
	def reset(self):
		self.type=  None
		self.depth = 0
		self.length = None
	
	def process(self, indent, lexer):
		if indent == '':
			self.depth = 0
			return
		
		if self.type == None:
			self.type = indent[0]
			self.length = len(indent)
		
		if indent[0] != self.type:
			raise Exception('mixed indentation:[%s]' % lexer.lineno)
		
		depth = int(len(indent) / self.length)
		if len(indent) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation:[%s]' % lexer.lineno)
		
		self.depth = depth
		return self.depth

auto_close = (
	'script',
)

self_close = (
	'img',
	'script',
)

class Tag:
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
			s += ' %s="%s"' % (k, v)
		if self.tagname in auto_close:
			s += '></' + self.tagname
		elif self.self_close or self.tagname in self_close:
			s += '/'
		s += '>'
		if self.value != None:
			s += self.value
		self.parser.push(s, trim_inner=self.trim_inner, trim_outer=self.trim_outer)
	
	def close(self):
		if self.self_close or self.tagname in self_close:
			self.parser.trim_next = self.trim_outer
		elif self.value != None or self.parser.last_obj == self:
			self.parser.buffer[-1] += '</' + self.tagname + '>'
			self.parser.trim_next = self.trim_outer
		else:
			self.parser.push('</' + self.tagname + '>', trim_inner=self.trim_outer, trim_outer=self.trim_inner)

class HamlParser:
	
	def __init__(self):
		self.html = ''
		self.buffer = []
		self.tabs = TabInfo()
		self.to_close = []
		self.trim_next = False
		self.last_obj = None
		self.lexer = HamlLexer()
		self.tokens = tokens
		self.parser = yacc.yacc(module=self, debug='-d' in sys.argv)
	
	def to_html(self, s):
		self.parser.parse(s, lexer=self.lexer, debug='-d' in sys.argv)
		return self.html
	
	def close(self, obj):
		if hasattr(obj, 'close'):
			obj.close()
	
	def render(self, obj):
		self.last_obj = obj
		while len(self.to_close) > self.tabs.depth:
			self.close(self.to_close.pop())
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
	
	def p_haml_empty(self, p):
		'haml : '
		self.html = ''
		pass
	
	def p_cleanup(self, p):
		'cleanup : '
		self.tabs.reset()
		del self.buffer[:]
	
	def p_haml_doc(self, p):
		'haml : cleanup doc'
		while len(self.to_close) > 0:
			self.close(self.to_close.pop())
		self.html = '\n'.join(self.buffer + [''])
		del self.buffer[:]
	
	def p_doc_doctype(self, p):
		'doc : DOCTYPE'
		self.buffer.append('<!doctype html>')
	
	def p_doc(self, p):
		'doc : obj'
		self.render(p[1])
	
	def p_doc_obj(self, p):
		'doc : doc obj'
		self.tabs.depth = 0
		self.render(p[2])
	
	def p_doc_indentation_obj(self, p):
		'doc : doc INDENTATION obj'
		self.tabs.process(p[2], p.lexer)
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
				| VALUE'''
		if len(p) == 1:
			p[0] = None
		elif len(p) == 2:
			p[0] = p[1]
	
	def p_attr(self, p):
		'''attr : ':' LITERAL '=' '>' '"' LITERAL '"' '''
		p[0] = {}
		p[0][p[2]] = p[6]
	
	def p_attrs(self, p):
		'''attrs : attr
				| attrs ',' attr '''
		if len(p) == 2:
			p[0] = p[1]
		else:
			p[1].update(p[3])
			p[0] = p[1]
	
	def p_dict(self, p):
		'''dict : 
				| CURLY attrs CURLY '''
		if len(p) == 1:
			p[0] = {}
		else:
			p[0] = p[2]
	
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

if __name__ == '__main__':
	lexer = HamlLexer()
	parser = HamlParser()
	
	s = []
	while True:
		try:
			s.append(raw_input())
		except EOFError:
			break
	
	sys.stdout.write(parser.to_html('\n'.join(s)))
