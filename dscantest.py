import unittest
from dscan import DScan

class TestDScanParser(unittest.TestCase):

	def setUp(self):
		self.d = DScan()

	def test_parse(self):
		with open("tests/jita2.txt") as fh:
			data = fh.read()
		r = self.d.parseDscan(data)
		assert(r)

if __name__ == '__main__':
	unittest.main()
