import os
import sys
import unittest
from haml import to_html

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

if __name__ == '__main__':
	unittest.main()
