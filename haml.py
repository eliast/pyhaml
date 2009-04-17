import sys
sys.path.append('ply')

import lex

if sys.version_info[0] >= 3:
	raw_input = input

# state

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
	
	def render(self):
		print('  ' * self.depth, end='')

# lexer

tokens = (
	'DOCTYPE',
	'TAGNAME',
	'ID',
	'CLASSNAME',
	'INDENTATION',
)

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
	print('Illegal character [%s]' % t.value[0])
	t.lexer.skip(1)

lexer = lex.lex()

# yacc

def render(p, obj):
	while len(p.parser.toclose) > p.parser.tabinfo.depth:
		p.parser.tabinfo.render()
		p.parser.toclose.pop().close()
		print()
	p.parser.toclose.append(obj)
	p.parser.tabinfo.render()
	obj.render()
	print()

class Tag:
	def __init__(self, id='', tagname='', classname=None):
		self.id = id
		self.tagname = tagname
		if not classname:
			self.classname = []
	
	def render(self):
		print('<' + self.tagname, end='')
		if self.id:
			print(' id="' + self.id + '"', end='')
		if len(self.classname):
			print(' class="' + ' '.join(self.classname) + '"', end='')
		print('>', end='')
	
	def close(self):
		print('</' + self.tagname + '>', end='')

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
	
	def render(self):
		print('  ' * self.depth, end='')

def p_doc_doctype(p):
	'doc : DOCTYPE'
	print('<!doctype html>')

def p_doc(p):
	'doc : tag'
	render(p, p[1])

def p_doc_tag(p):
	'doc : doc tag'
	p.parser.tabinfo.depth = 0
	render(p, p[2])

def p_doc_indentation_tag(p):
	'doc : doc INDENTATION tag'
	p.parser.tabinfo.process(p[2])
	render(p, p[3])

def p_tag_tagname(p):
	'tag : TAGNAME'
	p[0] = Tag(tagname=p[1])

def p_tag_id(p):
	'tag : ID'
	p[0] = Tag(id=p[1])

def p_tag_tagname_id(p):
	'tag : TAGNAME ID'
	p[0] = Tag(tagname=p[1], id=p[2])

def p_tag_class(p):
	'tag : tag CLASSNAME'
	p[0] = p[1]
	p[0].classname.append(p[2])

def p_error(p):
	print('syntax error')

import yacc
parser = yacc.yacc()
parser.tabinfo = TabInfo()
parser.toclose = []

s = []
while True:
	try:
		s.append(raw_input())
	except EOFError:
		break

parser.parse('\n'.join(s),lexer=lexer)
