import unittest

from invoice import discounted_total, total


class TotalTest(unittest.TestCase):
    def test_sums_lines(self):
        self.assertEqual(total([(2, 250), (1, 100)]), 600)

    def test_discount(self):
        self.assertEqual(discounted_total([(1, 1000)], 10), 900)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            discounted_total([(1, 1000)], 101)


if __name__ == '__main__':
    unittest.main()
