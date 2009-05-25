import os
import sys
import unittest
from haml import to_html, haml_parser

doctypes = haml_parser.doctypes

class TestHaml(unittest.TestCase):
	
	def testempty(self):
		self.assertEqual(to_html(''), '')
	
	def testattrs(self):
		self.assertEqual('<div style="ugly" class="atlantis"></div>\n', to_html(".atlantis{'style' : 'ugly'}"))
	
	def testoneline(self):
		self.assertEqual('<p>foo</p>\n', to_html('%p foo'))
	
	def teststripvalue(self):
		self.assertEqual('<p>strip</p>\n', to_html('%p       strip     '))
	
	def testemptytags(self):
		self.assertEqual('<p></p>\n<p></p>\n', to_html('%p\n%p'))
	
	def testmulti(self):
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
	
	def testhashwithnewline(self):
		self.assertEqual('<p a="b" c="d">foo</p>\n', to_html("%p{'a' : 'b',\n   'c':'d'} foo"))
		self.assertEqual('<p a="b" c="d"/>\n', to_html("%p{'a' : 'b',\n    'c' : 'd'}/"))
	
	def testtrim(self):
		self.assertEqual('<img/><img/><img/>\n', to_html('%img\n%img>\n%img'))
	
	def testselfclose(self):
		self.assertEqual('<sandwich/>\n', to_html('%sandwich/'))
	
	def testflextabs(self):
		html = '<p>\n  foo\n</p>\n<q>\n  bar\n  <a>\n    baz\n  </a>\n</q>\n'
		self.assertEqual(html, to_html('%p\n  foo\n%q\n  bar\n  %a\n    baz'))
		self.assertEqual(html, to_html('%p\n foo\n%q\n bar\n %a\n  baz'))
		self.assertEqual(html, to_html('%p\n\tfoo\n%q\n\tbar\n\t%a\n\t\tbaz'))
	
	def testattrs(self):
		self.assertEqual('<p foo="bar}"></p>\n', to_html("%p{'foo':'bar}'}"))
		self.assertEqual('<p foo="{bar"></p>\n', to_html("%p{'foo':'{bar'}"))
		self.assertEqual('<p foo="bar"></p>\n', to_html("%p{'foo':'''bar'''}"))
	
	def testmultilineattrs(self):
		self.assertEqual('<p foo="bar">val</p>\n', to_html("%p{  \n   'foo'  :  \n  'bar'  \n } val"))
	
	def testcodeinattrs(self):
		self.assertEqual('<p foo="3"></p>\n', to_html("%p{ 'foo': 1+2 }"))
	
	def testnestedattrs(self):
		self.assertEqual('''<p foo="{'foo': 'bar'}">val</p>\n''', to_html("%p{'foo':{'foo':'bar'}} val"))
	
	def testcrlf(self):
		self.assertEqual('<p>foo</p>\n<p>bar</p>\n<p>baz</p>\n<p>boom</p>\n', to_html('%p foo\r\n%p bar\r\n%p baz\n\r%p boom'))
	
	def testscript(self):
		self.assertEqual('<p>foo</p>\n', to_html("%p= 'foo'"))
		self.assertEqual('<p>foo</p>\n<p></p>\n', to_html("%p= 'foo'\n%p"))
	
	def testmultilinescript(self):
		self.assertEqual('<p>foo\nbar</p>\n', to_html("%p='''foo\nbar'''"))
	
	def testescapeattrs(self):
		self.assertEqual('<img foo="bar&amp;baz"/>\n', to_html("%img{'foo':'bar&baz'}"))
		self.assertEqual('<p foo="&lt;bar&gt;"></p>\n', to_html("%p{'foo':'<bar>'}"))
		self.assertEqual('<p foo="&quot;bar&quot;"></p>\n', to_html("%p{'foo':'\"bar\"'}"))
	
	def testsilent(self):
		self.assertEqual('<p></p>\n<p></p>\n', to_html("%p\n-# foo\n%p"))
		self.assertEqual('<p></p>\n<p></p>\n', to_html("%p\n-# foo\n  bar\n    baz\n%p"))
		self.assertEqual('<div>\n  <span>foo</span>\n</div>\n', to_html("%div\n  %span foo\n  -# foo\n    bar\n      baz"))
	
	def testcomment(self):
		self.assertEqual('<!-- foo -->\n', to_html("/foo"))
		self.assertEqual('<!-- strip -->\n', to_html("/      strip     "))
		self.assertEqual('<!--\n  foo\n  bar\n-->\n', to_html("/\n foo\n bar"))
		self.assertEqual('<!--[if IE]> foo <![endif]-->\n', to_html('/[if IE] foo'))
		self.assertEqual('<!--[if IE]>\n  foo\n<![endif]-->\n', to_html('/[if IE]\n foo'))
	
	def testdoctype(self):
		self.assertEqual(doctypes['xhtml'][''], to_html('!!!', format='xhtml').strip())
		self.assertEqual(doctypes['xhtml']['strict'], to_html('!!! strict', format='xhtml').strip())
		self.assertEqual(doctypes['xhtml']['transitional'], to_html('!!! transitional', format='xhtml').strip())
		self.assertEqual(doctypes['xhtml']['basic'], to_html('!!! basic', format='xhtml').strip())
		self.assertEqual(doctypes['xhtml']['mobile'], to_html('!!! mobile', format='xhtml').strip())
		self.assertEqual(doctypes['xhtml']['frameset'], to_html('!!! frameset', format='xhtml').strip())
		self.assertEqual(doctypes['html4'][''], to_html('!!!', format='html4').strip())
		self.assertEqual(doctypes['html4']['strict'], to_html('!!! strict', format='html4').strip())
		self.assertEqual(doctypes['html4']['frameset'], to_html('!!! frameset', format='html4').strip())
		self.assertEqual(doctypes['html4']['transitional'], to_html('!!! transitional', format='html4').strip())
		self.assertEqual(doctypes['html5'][''], to_html('!!!', format='html5').strip())
	
	def testxmldoctype(self):
		self.assertEqual('<?xml version="1.0" encoding="utf-8"?>\n', to_html('!!! XML'))
		self.assertEqual('<?xml version="1.0" encoding="utf-16"?>\n', to_html('!!! XML utf-16'))
		self.assertEqual('<?xml version="1.0" encoding="utf-8"?>\n<!doctype html>\n', to_html('!!! XML\n!!!'))
	
	def testsanitize(self):
		self.assertEqual('cheese &amp; crackers\n', to_html("&= 'cheese & crackers'"))
		self.assertEqual('foo &lt; bar\n', to_html("&= 'foo < bar'"))
		self.assertEqual('foo &gt; bar\n', to_html("&='foo > bar'"))
	
	def testescapeopt(self):
		self.assertEqual('cheese & crackers\n', to_html("='cheese & crackers'", escape=False))
		self.assertEqual('cheese &amp; crackers\n', to_html("='cheese & crackers'", escape=True))
		self.assertEqual('foo &gt; bar\n', to_html("= 'foo > bar'", escape=True))
		self.assertEqual('foo < bar\n', to_html("= 'foo < bar'", escape=False))
	
	def testnosanitize(self):
		self.assertEqual('<&>\n', to_html("!='<&>'", escape=True))
		self.assertEqual('<&>\n', to_html("!='<&>'", escape=False))
	
	def testbackslashstart(self):
		self.assertEqual('#\n', to_html('\\#'))
		self.assertEqual('.foo\n%bar\n', to_html('\\.foo\n\\%bar'))
		self.assertEqual('<div>\\foo</div>\n', to_html('%div \\foo'))
	
	def testdictlocals(self):
		def foo():
			return 'bar'
		self.assertEqual('<p foo="bar"></p>\n', to_html("%p{'foo':foo}", {'foo':'bar'}))
		self.assertEqual('<p foo="bar"></p>\n', to_html("%p{'foo':foo()}", {'foo':foo}))
	
	def testscriptlocals(self):
		def foo():
			return 'bar'
		self.assertEqual('<p>bar</p>\n', to_html("%p=foo", {'foo':'bar'}))
		self.assertEqual('<p>bar</p>\n', to_html("%p=foo()", {'foo':foo}))

if __name__ == '__main__':
	unittest.main()
