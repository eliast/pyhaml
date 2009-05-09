import os
import sys
import unittest
import haml

parser = haml.haml_parser()

def to_html(s):
	return parser.to_html(s)

class TestHaml(unittest.TestCase):
	
	def testempty(self):
		self.assertEqual(to_html(''), '')
	
	def testattrs(self):
		self.assertEqual('<div style="ugly" class="atlantis"></div>\n', to_html('.atlantis{:style => "ugly"}'))
	
	def testoneline(self):
		self.assertEqual('<p>foo</p>\n', to_html('%p foo'))
	
	def teststripvalue(self):
		self.assertEqual('<p>strip</p>\n', to_html('%p       strip     '))
	
	def testmulti(self):
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
		self.assertEqual('<strong>foo</strong>\n', to_html('%strong foo'))
	
	def testhashwithnewline(self):
		self.assertEqual('<p a="b" c="d">foo</p>\n', to_html('%p{:a => "b",\n   :c => "d"} foo'))
		self.assertEqual('<p a="b" c="d"/>\n', to_html('%p{:a => "b",\n    :c => "d"}/'))
	
	def testtrim(self):
		self.assertEqual('<img/><img/><img/>\n', to_html('%img\n%img>\n%img'))
	
	def testselfclose(self):
		self.assertEqual('<sandwich/>\n', to_html('%sandwich/'))
	
	def testflextabs(self):
		html = '<p>\n  foo\n</p>\n<q>\n  bar\n  <a>\n    baz\n  </a>\n</q>\n'
		self.assertEqual(html, to_html('%p\n  foo\n%q\n  bar\n  %a\n    baz'))
		self.assertEqual(html, to_html('%p\n foo\n%q\n bar\n %a\n  baz'))
		self.assertEqual(html, to_html('%p\n\tfoo\n%q\n\tbar\n\t%a\n\t\tbaz'))

if __name__ == '__main__':
	unittest.main()
