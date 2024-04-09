import unittest
from kryptone.signals import Signal, function_to_receiver

signal_to_test = Signal()


@function_to_receiver(signal_to_test)
def receiver_to_test(sender, text, **kwargs):
    sender.assertEqual(text, 'Text')
    return True


class TestSignal(unittest.TestCase):
    def test_receiver(self):
        result = signal_to_test.send(self, text='Text')
        first_receiver = result[0]
        func, func_result = first_receiver
        self.assertTrue(isinstance(func_result, bool))


if __name__ == '__main__':
    unittest.main()
