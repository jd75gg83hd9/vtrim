import unittest

from server_autobahn import to_timestamp

class TestTimestamp(unittest.TestCase):
    def test_upper(self):
        self.assertEqual('00:00:07', to_timestamp('7'))
        self.assertEqual('00:00:10', to_timestamp('10'))
        self.assertEqual('00:01:01', to_timestamp('101'))
        self.assertEqual('00:00:01', to_timestamp('001'))
        self.assertEqual('00:34:54', to_timestamp('3454'))
        self.assertEqual('00:34:54', to_timestamp('03454'))
        self.assertEqual('17:34:41', to_timestamp('173441'))

        self.assertRaises(ValueError, to_timestamp, '1173441')
        self.assertRaises(ValueError, to_timestamp, '60')
        self.assertRaises(ValueError, to_timestamp, '61')
        self.assertRaises(ValueError, to_timestamp, '80')
        self.assertRaises(ValueError, to_timestamp, '6001')
        self.assertRaises(ValueError, to_timestamp, '7001')
        self.assertRaises(ValueError, to_timestamp, 'a')
        self.assertRaises(ValueError, to_timestamp, 'qqqqqqqqqqqqqqqqq')
        self.assertRaises(ValueError, to_timestamp, '2222222222')
