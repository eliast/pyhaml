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

if __name__ == '__main__':
	unittest.main()
