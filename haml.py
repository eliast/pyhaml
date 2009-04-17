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
		if not self.type:
			self.type = indent[0]
			self.length = len(indent)
		
		if indent[0] != self.type:
			raise Exception('mixed indentation')
		
		depth = int(len(indent) / self.length)
		if len(indent) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation')
		
		self.depth = depth
		return self.depth

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
	t.value = t.lexer.tabinfo.process(t.value)
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

lexer = lex.lex(debug=True)
lexer.tabinfo = TabInfo()

# yacc

class Tag:
	def __init__(self, id='', tagname='', classname=[]):
		self.id = id
		self.tagname = tagname
		self.classname = classname

def doc_doctype(p):
	'doc : DOCTYPE'
	print('<!doctype html>')

def doc(p):
	'doc : tag'
	print('<' + p[1].tagname + '>')

def doc_tag(p):
	'doc : doc tag'
	p.lexer.tabinfo.depth = 0
	print('<' + p[2].tagname + '>')

def doc_indentation_tag(p):
	'doc : doc INDENTATION tag'
	print('<' + p[3].tagname + '>')

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
parser = yacc.yacc(debug=True)

s = []
while True:
	try:
		s.append(raw_input())
	except EOFError:
		break

parser.parse('\n'.join(s),lexer=lexer,debug=1)
