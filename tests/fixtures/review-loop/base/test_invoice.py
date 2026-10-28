import unittest

from invoice import total


class TotalTest(unittest.TestCase):
    def test_sums_lines(self):
        self.assertEqual(total([(2, 250), (1, 100)]), 600)


if __name__ == '__main__':
    unittest.main()
