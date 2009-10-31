import sys
from .lexer import tokens

class haml_obj(object):
	
	def __init__(self, parser):
		self.parser = parser
	
	def push(self, *args, **kwargs):
		push(self.parser, *args, **kwargs)
	
	def write(self, *args, **kwargs):
		write(self.parser, *args, **kwargs)
	
	def script(self, *args, **kwargs):
		script(self.parser, *args, **kwargs)
	
	def enblock(self, *args, **kwargs):
		enblock(self.parser, *args, **kwargs)
	
	def deblock(self, *args, **kwargs):
		deblock(self.parser, *args, **kwargs)
	
	def entab(self):
		script(self.parser, '__entab__()')
	
	def detab(self):
		script(self.parser, '__detab__()')
	
	def open(self):
		pass
	
	def close(self):
		pass
	
	def no_nesting(self):
		if not self.parser.last_obj is self:
			self.error('illegal nesting')
	
	def error(self, msg):
		raise Exception(msg)

class Content(haml_obj):
	
	def __init__(self, parser, value):
		haml_obj.__init__(self, parser)
		self.value = value
	
	def open(self):
		self.push(self.value, literal=True)
	
	def close(self):
		self.no_nesting()

class Script(haml_obj):
	
	def __init__(self, parser, type='=', value=''):
		haml_obj.__init__(self, parser)
		self.type = type
		self.value = value
		self.escape = False
		if self.type == '&=':
			self.escape = True
		elif self.type == '=' and parser.op.escape:
			self.escape = True
	
	def open(self):
		self.push(self.value, escape=self.escape)
	
	def close(self):
		pass

class SilentScript(haml_obj):
	
	def __init__(self, parser, value=''):
		haml_obj.__init__(self, parser)
		self.value = value
	
	def entab(self):
		pass
	
	def detab(self):
		pass
	
	def open(self):
		self.script(self.value)
		self.enblock()
	
	def close(self):
		self.deblock()

class Doctype(haml_obj):
	
	def __init__(self, parser):
		haml_obj.__init__(self, parser)
		self.xml = False
		self.type = ''
	
	def open(self):
		if self.xml:
			s = '<?xml version="1.0" encoding="%s"?>'
			self.push(s % self.type, literal=True)
		else:
			s = self.parser.op.format[self.type]
			self.push(s, literal=True)
	
	def close(self):
		self.no_nesting()

class Comment(haml_obj):
	
	def __init__(self, parser, value='', condition=''):
		haml_obj.__init__(self, parser)
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
		'br',
	)
	
	def __init__(self, parser, tagname='', id='', classname=''):
		haml_obj.__init__(self, parser)
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
	
	def is_last(self):
		return self.parser.last_obj is self
	
	def auto_closing(self):
		if self.value:
			return True
		elif self.tagname in Tag.auto_close and self.is_last():
			return True
		elif self.parser.last_obj is self:
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
		self.script('__attrs__(%s, %s)' % (self.dict, repr(self.attrs)))
		
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
			self.parser.trim_next = self.outer
		else:
			self.push('</' + self.tagname + '>', inner=self.outer, outer=self.inner, literal=True)

def enblock(parser):
	parser.depth += 1

def deblock(parser):
	parser.depth -= 1

def push(parser, s, inner=False, outer=False, **kwargs):
	if outer or parser.trim_next:
		write(parser, s, **kwargs)
	else:
		script(parser, '__indent__()')
		write(parser, s, **kwargs)
	parser.trim_next = inner

def write(parser, s, literal=False, escape=False):
	s = repr(s) if literal else 'str(%s)' % s
	f = '__escape__' if escape else '__write__'
	script(parser, '%s(%s)' % (f, s))

def script(parser, s):
	pre = ' ' * parser.depth
	parser.src += [pre + s]

def close(obj):
	obj.detab()
	obj.close()

def open(p, obj):
	while len(p.parser.to_close) > p.lexer.depth:
		close(p.parser.to_close.pop())
	p.parser.last_obj = obj
	obj.open()
	obj.entab()
	p.parser.to_close.append(obj)

def p_haml_doc(p):
	'''haml :
			| doc
			| doc LF'''
	while len(p.parser.to_close) > 0:
		close(p.parser.to_close.pop())

def p_doc(p):
	'doc : obj'
	p.parser.to_close = []
	open(p, p[1])

def p_doc_obj(p):
	'doc : doc obj'
	open(p, p[2])

def p_doc_indent_obj(p):
	'doc : doc LF obj'
	open(p, p[3])

def p_obj(p):
	'''obj : element
		| content
		| comment
		| condcomment
		| doctype
		| script
		| silentscript'''
	p[0] = p[1]

def p_silentscript(p):
	'''silentscript : SILENTSCRIPT'''
	p[0] = SilentScript(p.parser, value=p[1])

def p_script(p):
	'''script : TYPE SCRIPT'''
	p[0] = Script(p.parser, type=p[1], value=p[2])

def p_content(p):
	'content : CONTENT'
	p[0] = Content(p.parser, p[1])

def p_doctype(p):
	'''doctype : DOCTYPE'''
	p[0] = Doctype(p.parser)

def p_htmltype(p):
	'''doctype : DOCTYPE HTMLTYPE'''
	p[0] = Doctype(p.parser)
	p[0].type = p[2]

def p_xmltype(p):
	'''doctype : DOCTYPE XMLTYPE'''
	p[0] = Doctype(p.parser)
	if p[2] == '':
		p[2] = 'utf-8'
	p[0].type = p[2]
	p[0].xml = True

def p_condcomment(p):
	'''condcomment : CONDCOMMENT
				| CONDCOMMENT VALUE'''
	p[0] = Comment(p.parser, condition=p[1])
	if len(p) == 3:
		p[0].value = p[2]

def p_comment(p):
	'''comment : COMMENT
			| COMMENT VALUE'''
	p[0] = Comment(p.parser)
	if len(p) == 3:
		p[0].value = p[2]

def p_element_tag_trim_dict_value(p):
	'element : tag trim dict selfclose text'
	p[0] = p[1]
	p[0].inner = '<' in p[2]
	p[0].outer = '>' in p[2]
	p[0].dict = p[3]
	p[0].self_close = p[4]
	p[0].value = p[5]

def p_selfclose(p):
	'''selfclose :
				| '/' '''
	p[0] = len(p) == 2

def p_trim(p):
	'''trim :
		| TRIM'''
	if len(p) == 1:
		p[0] = ''
	else:
		p[0] = p[1]

def p_text(p):
	'''text :
			| value
			| script'''
	if len(p) == 1:
		p[0] = None
	elif len(p) == 2:
		p[0] = p[1]

def p_value(p):
	'''value : value VALUE
			| VALUE'''
	if len(p) == 2:
		p[0] = p[1]
	elif len(p) == 3:
		p[0] = '%s %s' % (p[1], p[2])

def p_dict(p):
	'''dict : 
			| DICT '''
	if len(p) == 1:
		p[0] = '{}' 
	else:
		p[0] = p[1]

def p_tag_tagname(p):
	'tag : TAGNAME'
	p[0] = Tag(p.parser, tagname=p[1])

def p_tag_id(p):
	'tag : ID'
	p[0] = Tag(p.parser, id=p[1])

def p_tag_class(p):
	'tag : CLASSNAME'
	p[0] = Tag(p.parser, classname=p[1])

def p_tag_tagname_id(p):
	'tag : TAGNAME ID'
	p[0] = Tag(p.parser, tagname=p[1], id=p[2])

def p_tag_tag_class(p):
	'tag : tag CLASSNAME'
	p[0] = p[1]
	p[0].addclass(p[2])

def p_error(p):
	sys.stderr.write('syntax error[%s]\n' % (p,))
