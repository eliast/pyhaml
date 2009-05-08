import os
import sys
import unittest
import haml

lexer = haml.HamlLexer()
parser = haml.HamlParser()

def parse(s):
	parser.parse(s, lexer=lexer)
	return parser.html

class TestHaml(unittest.TestCase):
	
	def testempty(self):
		self.assertEqual(parse(''), '')
	
	def testattrs(self):
		self.assertEqual('<div class="atlantis" style="ugly"></div>\n', parse('.atlantis{:style => "ugly"}'))
	
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
	
	def testtrim(self):
		self.assertEqual('<img/><img/><img/>\n', parse('%img\n%img>\n%img'))
	
	def testselfclose(self):
		self.assertEqual('<sandwich/>\n', parse('%sandwich/'))

if __name__ == '__main__':
	unittest.main()
