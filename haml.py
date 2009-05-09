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

import yacc

def HamlParser():
	
	buffer = []
	tabs = TabInfo()
	to_close = []
	trim_next = [False]
	last_obj = [None]
	
	auto_close = (
		'script',
	)
	
	self_close = (
		'img',
		'script',
	)
	
	def close(obj):
		if hasattr(obj, 'close'):
			obj.close()
	
	def render(obj):
		last_obj[0] = obj
		while len(to_close) > tabs.depth:
			close(to_close.pop())
		if hasattr(obj, 'render'):
			obj.render()
		else:
			push(obj)
		to_close.append(obj)
	
	def push(s, trim_inner=False, trim_outer=False):
		if trim_outer or trim_next[0]:
			if len(buffer) == 0:
				buffer.append('')
			pre = buffer.pop()
		else:
			pre = '  ' * len(to_close)
		buffer.append(pre + s)
		trim_next[0] = trim_inner
	
	class Tag:
		def __init__(self, tagname=''):
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
			push(s, trim_inner=self.trim_inner, trim_outer=self.trim_outer)
		
		def close(self):
			if self.self_close or self.tagname in self_close:
				trim_next[0] = self.trim_outer
			elif self.value != None or last_obj[0] == self:
				buffer[-1] += '</' + self.tagname + '>'
				trim_next[0] = self.trim_outer
			else:
				push('</' + self.tagname + '>', trim_inner=self.trim_outer, trim_outer=self.trim_inner)
	
	def p_haml_empty(p):
		'haml : '
		p.parser.html = ''
		pass
	
	def p_cleanup(p):
		'cleanup : '
		tabs.reset()
		del buffer[:]
	
	def p_haml_doc(p):
		'haml : cleanup doc'
		while len(to_close) > 0:
			close(to_close.pop())
		p.parser.html = '\n'.join(buffer + [''])
		del buffer[:]
	
	def p_doc_doctype(p):
		'doc : DOCTYPE'
		buffer.append('<!doctype html>')
	
	def p_doc(p):
		'doc : obj'
		render(p[1])
	
	def p_doc_obj(p):
		'doc : doc obj'
		tabs.depth = 0
		render(p[2])
	
	def p_doc_indentation_obj(p):
		'doc : doc INDENTATION obj'
		tabs.process(p[2], p.lexer)
		render(p[3])
	
	def p_obj_element(p):
		'''obj : element
			| CONTENT'''
		p[0] = p[1]
	
	def p_element_tag_trim_dict_value(p):
		'element : tag trim dict selfclose value'
		p[0] = p[1]
		p[0].trim_inner = '<' in p[2]
		p[0].trim_outer = '>' in p[2]
		p[0].attrs.update(p[3])
		p[0].self_close = p[4]
		p[0].value = p[5]
	
	def p_selfclose(p):
		'''selfclose :
					| '/' '''
		if len(p) == 1:
			p[0] = False
		elif len(p) == 2:
			p[0] = True
	
	def p_trim(p):
		'''trim :
			| TRIM'''
		if len(p) == 1:
			p[0] = ''
		else:
			p[0] = p[1]
	
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
		p[0] = Tag()
		p[0].attrs['id'] = p[1]
	
	def p_tag_class(p):
		'tag : CLASSNAME'
		p[0] = Tag()
		p[0].addclass(p[1])
	
	def p_tag_tagname_id(p):
		'tag : TAGNAME ID'
		p[0] = Tag(tagname=p[1])
		p[0].attrs['id'] = p[2]
	
	def p_tag_tag_class(p):
		'tag : tag CLASSNAME'
		p[0] = p[1]
		p[0].addclass(p[2])
	
	def p_error(p):
		sys.stderr.write('syntax error[%s]\n' % (p,))
	
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
	
	parser.parse('\n'.join(s), lexer=lexer, debug='-d' in sys.argv)
	sys.stdout.write(parser.html)
