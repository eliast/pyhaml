import sys
sys.path.append('ply')

if sys.version_info[0] >= 3:
	raw_input = input

import lex

tokens = (
	'DOCTYPE',
	'TAGNAME',
	'ID',
	'CLASSNAME',
	'INDENTATION',
	'LITERAL',
	'CURLY',
	'VALUE',
)

def HamlLexer():
	
	states = (
		('hash', 'exclusive'),
		('tag', 'inclusive'),
	)
	
	literals = '<>"=:,{}'
	t_ignore = ''
	t_hash_ignore = ' \t'
	
	def t_DOCTYPE(t):
		r'!!!'
		return t

	def t_INDENTATION(t):
		r'\n+[ \t]*'
		t.lexer.begin('INITIAL')
		t.lexer.lineno += t.value.count('\n')
		t.value = t.value.replace('\n', '')
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
	
	def process(self, indent):
		if indent == '':
			self.depth = 0
			return
		
		if self.type == None:
			self.type = indent[0]
			self.length = len(indent)
		
		if indent[0] != self.type:
			raise Exception('mixed indentation')
		
		depth = int(len(indent) / self.length)
		if len(indent) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation')
		
		self.depth = depth
		return self.depth

import yacc

def HamlParser():
	
	buffer = []
	tabs = TabInfo()
	to_close = []
	trim_next = [False]
	last_tag = [None]
	
	auto_close = (
		'script',
	)
	
	self_close = (
		'img',
		'script',
	)
	
	def close(obj):
		obj.close()
	
	def render(obj):
		while len(to_close) > tabs.depth:
			close(to_close.pop())
		obj.render()
		to_close.append(obj)
	
	def push(s, trim_inner=False, trim_outer=False):
		if trim_outer or trim_next[0]:
			pre = buffer.pop()
		else:
			pre = '  ' * len(to_close)
		buffer.append(pre + s)
		trim_next[0] = trim_inner
	
	class Tag:
		def __init__(self, id='', tagname='', classname=[]):
			self.id = id
			self.attrs = {}
			self.tagname = tagname
			self.classname = [] + classname
			self.trim_inner = False
			self.trim_outer = False
			if tagname == '':
				self.tagname = 'div'
		
		def render(self):
			s = '<' + self.tagname
			if self.id:
				s += ' id="%s"' % self.id
			if len(self.classname):
				s += ' class="%s"' % ' '.join(self.classname)
			if self.tagname in auto_close:
				s += '></' + self.tagname
			elif self.tagname in self_close:
				s += '/'
			for k,v in self.attrs.items():
				s += ' %s="%s"' % (k, v)
			s += '>'
			if self.value != None:
				s += self.value
			push(s, trim_inner=self.trim_inner, trim_outer=self.trim_outer)
			last_tag[0] = self
		
		def close(self):
			if self.tagname in self_close:
				trim_next[0] = self.trim_outer
			elif self.value != None or last_tag[0] == self:
				buffer[-1] += '</' + self.tagname + '>'
				trim_next[0] = self.trim_outer
			else:
				push('</' + self.tagname + '>', trim_inner=self.trim_outer, trim_outer=self.trim_inner)
	
	def p_haml_empty(p):
		'haml : '
		p.parser.html = ''
		pass
	
	def p_haml_doc(p):
		'haml : doc'
		while len(to_close) > 0:
			close(to_close.pop())
		p.parser.html = '\n'.join(buffer + [''])
		del buffer[:]
	
	def p_doc_doctype(p):
		'doc : DOCTYPE'
		buffer.append('<!doctype html>')
	
	def p_doc(p):
		'doc : element'
		render(p[1])
	
	def p_doc_element(p):
		'doc : doc element'
		tabs.depth = 0
		render(p[2])
	
	def p_doc_indentation_element(p):
		'doc : doc INDENTATION element'
		tabs.process(p[2])
		render(p[3])
	
	def p_element_tag_trim(p):
		'element : tag trim dict value'
		p[0] = p[1]
		p[0].trim_inner = '<' in p[2]
		p[0].trim_outer = '>' in p[2]
		p[0].attrs = p[3]
		p[0].value = p[4]
	
	def p_value(p):
		'''value :
				| VALUE'''
		if len(p) == 1:
			p[0] = None
		elif len(p) == 2:
			p[0] = p[1]
	
	def p_attr(p):
		'''attr : ':' LITERAL '=' '>' '"' LITERAL '"' '''
		p[0] = {}
		p[0][p[2]] = p[6]
	
	def p_attrs(p):
		'''attrs : attr
				| attrs ',' attr '''
		if len(p) == 2:
			p[0] = p[1]
		else:
			p[1].update(p[3])
			p[0] = p[1]
	
	def p_dict(p):
		'''dict : 
				| CURLY attrs CURLY '''
		if len(p) == 1:
			p[0] = {}
		else:
			p[0] = p[2]
	
	def p_tag_tagname(p):
		'tag : TAGNAME'
		p[0] = Tag(tagname=p[1])
	
	def p_tag_id(p):
		'tag : ID'
		p[0] = Tag(id=p[1])
	
	def p_tag_class(p):
		'tag : CLASSNAME'
		p[0] = Tag(classname=[p[1]])
	
	def p_tag_tagname_id(p):
		'tag : TAGNAME ID'
		p[0] = Tag(tagname=p[1], id=p[2])
	
	def p_tag_tag_class(p):
		'tag : tag CLASSNAME'
		p[0] = p[1]
		p[0].classname.append(p[2])
	
	def p_trim(p):
		'''trim :
				| '>'
				| '<'
				| '>' '<'
				| '<' '>' '''
		if len(p) == 1:
			p[0] = ''
		elif len(p) == 2:
			p[0] = p[1]
		elif len(p) == 3:
			p[0] = p[1] + p[2]
	
	def p_error(p):
		sys.stderr.write('syntax error\n')
	
	return yacc.yacc(debug=0)

if __name__ == '__main__':
	lexer = HamlLexer()
	parser = HamlParser()
	
	s = []
	while True:
		try:
			s.append(raw_input())
		except EOFError:
			break
	
	parser.parse('\n'.join(s), lexer=lexer)
	sys.stdout.write(parser.html)
