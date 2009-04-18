import sys
sys.path.append('ply')
write = sys.stdout.write

if sys.version_info[0] >= 3:
	raw_input = input

import lex

tokens = (
	'DOCTYPE',
	'TAGNAME',
	'ID',
	'CLASSNAME',
	'INDENTATION',
)

def HamlLexer():
	literals = '<>'
	
	def t_DOCTYPE(t):
		r'!!!'
		return t

	def t_INDENTATION(t):
		r'[ \t]+'
		return t

	def t_TAGNAME(t):
		r'%[a-zA-Z][a-zA-Z0-9]*'
		t.value = t.value[1:]
		return t

	def t_ID(t):
		r'\#[a-zA-Z][a-zA-Z0-9]*'
		t.value = t.value[1:]
		return t

	def t_CLASSNAME(t):
		r'\.[a-zA-Z-][a-zA-Z0-9-]*'
		t.value = t.value[1:]
		return t
	
	def t_newline(t):
		r'\n+'
		t.lexer.lineno += len(t.value)
	
	def t_error(t):
		write('Illegal character [%s]' % t.value[0])
		t.lexer.skip(1)
	
	return lex.lex()

class TabInfo:
	def __init__(self):
		self.type = None
		self.depth = 0
		self.length = None
	
	def process(self, indent):
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
	
	tabs = TabInfo()
	to_close = []
	
	selfclose = (
		'img',
	)
	
	def close(obj):
		obj.close()
	
	def render(obj):
		while len(to_close) > tabs.depth:
			close(to_close.pop())
		to_close.append(obj)
		obj.render()
	
	class Tag:
		def __init__(self, id='', tagname='', classname=[]):
			self.id = id
			self.tagname = tagname
			self.classname = [] + classname
			if tagname == '':
				self.tagname = 'div'
		
		def render(self):
			write('  ' * tabs.depth)
			write('<' + self.tagname)
			if self.id:
				write(' id="' + self.id + '"')
			if len(self.classname):
				write(' class="' + ' '.join(self.classname) + '"')
			if self.tagname in selfclose:
				write('/')
			write('>\n')
		
		def close(self):
			if self.tagname in selfclose:
				return
			write('  ' * len(to_close))
			write('</' + self.tagname + '>\n')
	
	def p_haml_doc(p):
		'haml : doc'
		while len(to_close) > 0:
			close(to_close.pop())
	
	def p_doc_doctype(p):
		'doc : DOCTYPE'
		write('<!doctype html>\n')
	
	def p_doc(p):
		'doc : tag'
		render(p[1])
	
	def p_doc_tag(p):
		'doc : doc tag'
		tabs.depth = 0
		render(p[2])
	
	def p_doc_indentation_tag(p):
		'doc : doc INDENTATION tag'
		tabs.process(p[2])
		render(p[3])
	
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
		'''trim : '>'
				| '<'
				| '>' '<'
				| '<' '>' '''
		p[0] = p[1]
	
	def p_error(p):
		write('syntax error\n')
	
	return yacc.yacc()

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
