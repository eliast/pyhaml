import re
import os
import sys

from .patch import toks, untokenize

class Tabs(object):
	def __init__(self):
		self.type = None
		self.depth = 0
		self.length = None
		self.history = []
	
	def push(self):
		self.history.append(self.depth)
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
		
		if not all(c == self.type for c in s):
			raise Exception('mixed indentation')
		
		depth = int(len(s) / self.length)
		if len(s) % self.length > 0 or depth - self.depth > 1:
			raise Exception('invalid indentation')
		
		self.depth = depth
		return self.depth

tokens = (
	'LF',
	'DOCTYPE',
	'HTMLTYPE',
	'XMLTYPE',
	'TAGNAME',
	'ID',
	'CLASSNAME',
	'VALUE',
	'CONTENT',
	'TRIM',
	'DICT',
	'SCRIPT',
	'SILENTSCRIPT',
	'COMMENT',
	'CONDCOMMENT',
	'TYPE',
)

states = (
	('tag', 'exclusive'),
	('silent', 'exclusive'),
	('doctype', 'exclusive'),
	('comment', 'exclusive'),
	('tabs', 'exclusive'),
	('multi', 'exclusive'),
	('script', 'exclusive'),
)

literals = '":,{}<>/'
t_ANY_ignore = '\r'

def build(self, **kwargs):
	self.lexer.depth = 0
	self.tabs = Tabs()
	return self

def pytokens(t):
	for token in toks(t.lexer.lexdata[t.lexer.lexpos:]):
		_, s, _, (_, ecol), _ = token
		yield token
		for _ in range(s.count('\n')):
			t.lexer.lineno += 1
			t.lexer.lexpos = t.lexer.lexdata.find('\n', t.lexer.lexpos+1) + 1

def read_dict(t):
	t.value = []
	lvl = 0
	for token in pytokens(t):
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

def read_script(t):
	src = []
	for token in pytokens(t):
		_, s, _, (_, ecol), _ = token
		if s == '':
			t.lexer.lexpos = len(t.lexer.lexdata)
			src = untokenize(src).strip()
			return src
		src += [token]
		if s == '\n':
			t.lexer.lexpos += ecol - 1
			src = untokenize(src).strip()
			return src

def t_tag_doctype_comment_INITIAL_LF(t):
	r'\n'
	t.lexer.lineno += t.value.count('\n')
	t.lexer.begin('INITIAL')
	t.lexer.push_state('tabs')
	return t

def t_tabs_other(t):
	r'[^ \t]'
	t.lexer.depth = t.lexer.tabs.process('')
	t.lexer.lexpos -= len(t.value)
	t.lexer.pop_state()

def t_tabs_indent(t):
	r'[ \t]+'
	t.lexer.depth = t.lexer.tabs.process(t.value)
	t.lexer.pop_state()

def t_silentcomment(t):
	r'-\#[^\n]*'
	t.lexer.tabs.push()
	t.lexer.push_state('silent')

def t_silent_LF(t):
	r'\n'
	t.lexer.lineno += t.value.count('\n')
	t.lexer.push_state('tabs')

def t_silent_other(t):
	r'[^\n]+'
	if t.lexer.tabs.depth <= t.lexer.tabs.start:
		t.lexer.lexpos -= len(t.value)
		t.lexer.pop_state()

def t_DOCTYPE(t):
	r'!!!'
	t.lexer.begin('doctype')
	return t

def t_doctype_XMLTYPE(t):
	r'[ ]+XML([ ]+[^\n]+)?'
	t.value = t.value.replace('XML', '', 1).strip()
	return t

def t_doctype_HTMLTYPE(t):
	r'[ ]+(strict|frameset|mobile|basic|transitional)'
	t.value = t.value.strip()
	return t

def t_CONTENT(t):
	r'[^=&/#!.%\n\t -][^\n]*'
	if t.value[0] == '\\':
		t.value = t.value[1:]
	return t

def t_CONDCOMMENT(t):
	r'/\[[^\]]+\]'
	t.lexer.begin('comment')
	t.value = t.value[2:-1]
	return t

def t_COMMENT(t):
	r'/'
	t.lexer.begin('comment')
	return t

def t_comment_VALUE(t):
	r'[^\n]+'
	t.value = t.value.strip()
	return t

def t_TAGNAME(t):
	r'%[a-zA-Z][a-zA-Z0-9]*'
	t.lexer.begin('tag')
	t.value = t.value[1:]
	return t

def t_tag_INITIAL_ID(t):
	r'\#[a-zA-Z][a-zA-Z0-9]*'
	t.value = t.value[1:]
	t.lexer.begin('tag')
	return t

def t_tag_INITIAL_CLASSNAME(t):
	r'\.[a-zA-Z-][a-zA-Z0-9-]*'
	t.value = t.value[1:]
	t.lexer.begin('tag')
	return t

def t_tag_DICT(t):
	r'[ ]*{'
	t.lexer.lexpos -= 1
	return read_dict(t)

def t_SILENTSCRIPT(t):
	r'-'
	t.value = read_script(t)
	return t

def t_tag_INITIAL_TYPE(t):
	r'[ ]*(&|!)?='
	t.lexer.lexpos -= 1
	t.value = t.value.strip()
	t.lexer.push_state('script')
	return t

def t_script_SCRIPT(t):
	r'='
	t.value = read_script(t)
	t.lexer.pop_state()
	return t

def t_tag_TRIM(t):
	r'<>|><|<|>'
	return t

def t_tag_VALUE(t):
	r'[ \t]*[^{}<>=&/#!.%\n\t -][^\n]*'
	t.value = t.value.strip()
	if t.value[0] == '\\':
		t.value = t.value[1:]
	if re.search('[ \t]\|[ \t]*$', t.value):
		t.lexer.begin('multi')
	return t

def t_multi_newline(t):
	r'\n'
	pass

def t_multi_VALUE(t):
	r'[^\n]+[ \t]\|[ \t]*\n'
	t.value = t.value.strip()[:-1].strip()
	return t

def t_multi_other(t):
	r'[^\n]*(?<![ \t]\|)[ \t]*\n'
	t.lexer.lexpos -= len(t.value)
	t.lexer.begin('tabs')

def t_ANY_error(t):
	sys.stderr.write('Illegal character(s) [%s]\n' % t.value)
	t.lexer.skip(1)
