import os
import sys
import unittest


here = os.path.dirname(__file__)
sys.path.extend((
    os.path.join(here, os.path.pardir),
    os.path.join(here, 'versioned-libs')
))


class SimpleTestCase(unittest.TestCase):

    def test_basic_functionality(self):
        import using_testlib_10 as v1
        import using_testlib_20 as v2
        self.assertEqual(v1.a_function(), 'from version 1.0')
        self.assertEqual(v2.a_function(), 'from version 2.0')

        self.assert_('testlib' in sys.modules)

    def test_proxy(self):
        # trigger proxy
        import using_testlib_10 as v1
        import multiversion
        self.assertEqual(v1.a_function(), 'from version 1.0')

        import testlib
        try:
            testlib.a_function
        except AttributeError:
            pass
        else:
            self.fail('failed')

        multiversion.require_version('testlib', '1.0',
                                     globals=globals())
        self.assertEqual(testlib.a_function(), 'from version 1.0')


if __name__ == '__main__':
    unittest.main()
