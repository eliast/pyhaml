import os
import sys
import unittest
import haml

parser = haml.HamlParser()
lexer = haml.HamlLexer()

def parse(s):
	parser.parse(s, lexer=lexer)
	return parser.html

class TestHaml(unittest.TestCase):
	
	def testempty(self):
		self.assertEqual(parse(''), '')
	
	def testattrs(self):
		self.assertEqual('<div style="ugly" class="atlantis"></div>\n', parse('.atlantis{:style => "ugly"}'))
	
	def testoneline(self):
		self.assertEqual('<p>foo</p>\n', parse('%p foo'))
	
	def teststripvalue(self):
		self.assertEqual('<p>strip</p>\n', parse('%p       strip     '))
	
	def testmulti(self):
		self.assertEqual('<strong>foo</strong>\n', parse('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', parse('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', parse('%strong foo'))
	
	def testhashwithnewline(self):
		self.assertEqual('<p a="b" c="d">foo</p>\n', parse('%p{:a => "b",\n   :c => "d"} foo'))
		self.assertEqual('<p a="b" c="d"/>\n', parse('%p{:a => "b",\n    :c => "d"}/'))
	
	def testtrim(self):
		self.assertEqual('<img/><img/><img/>\n', parse('%img\n%img>\n%img'))
	
	def testselfclose(self):
		self.assertEqual('<sandwich/>\n', parse('%sandwich/'))
	
	def testflextabs(self):
		html = '<p>\n  foo\n</p>\n<q>\n  bar\n  <a>\n    baz\n  </a>\n</q>\n'
		self.assertEqual(html, parse('%p\n  foo\n%q\n  bar\n  %a\n    baz'))
		self.assertEqual(html, parse('%p\n foo\n%q\n bar\n %a\n  baz'))
		self.assertEqual(html, parse('%p\n\tfoo\n%q\n\tbar\n\t%a\n\t\tbaz'))

if __name__ == '__main__':
	unittest.main()
