import random
import unittest
from math import prod

from pynapl import APL
from pynapl.Array import APLArray


def makeRandomArray():
    """Generate a (smallish) random higher-order array"""

    # generate a random rank
    rank = random.randint(2, 4)

    # generate some random dimensions
    rho = []
    for _ in range(rank):
        rho.append(random.randint(2, 4))

    # generate some random data
    data = []
    for _ in range(prod(rho)):
        data.append(random.randint(0, 100))

    # generate array
    return APLArray(rho=rho, data=data)


def makeRandomIndex(array):
    """Generate a random index into an array"""
    return [random.randint(0, d - 1) for d in array.rho]


def makeRandomNestedArray():
    """Generate a (smallish) random nested higher-order array"""

    arr = makeRandomArray()
    for idx in [x(arr) for x in [makeRandomIndex] * 10]:
        arr[idx] = makeRandomArray()
    return arr


class TestArrayAPL(unittest.TestCase):
    def setUp(self):
        # set up an APL
        self.apl = APL.APL()

        # generate random array
        self.rarr = makeRandomArray()

        # generate complex random array
        self.cplx_arr = makeRandomNestedArray()

    def tearDown(self):
        self.apl.stop()

    def test_split_apl(self):
        """Array.split should be equivalent to ↓"""
        aplsplit = self.apl.fn("↓", raw=True)
        self.assertEqual(self.rarr.split(), aplsplit(self.rarr))

    def test_round_trip(self):
        """Sending a complex array over the wire should give us the same
        array back."""
        identity = self.apl.fn("⊢", raw=True)
        self.assertEqual(self.cplx_arr, identity(self.cplx_arr))


class TestArraySerializer(unittest.TestCase):
    def setUp(self):
        self.cplx_arr = makeRandomNestedArray()

    def test_serializer(self):
        """Test that serializing and deserializing an APLArray gives the same
        array back."""
        self.assertEqual(
            self.cplx_arr, APLArray.fromJSONString(self.cplx_arr.dumps())
        )


class TestArray(unittest.TestCase):
    def setUp(self):
        self.rarr = makeRandomArray()

    def test_split_singleton(self):
        """↓ on a singleton does nothing"""
        arr = APLArray(rho=[], data=[42])
        self.assertEqual(arr, arr.split())

    def test_split_rho(self):
        """↓ should drop the first element"""
        self.assertEqual(self.rarr.rho[:-1], self.rarr.split().rho)


class TestConversion(unittest.TestCase):
    def setUp(self):
        self.apl = APL.APL()

        # Python 2.7 doesn't support subTest
        if not hasattr(self, "subTest"):

            class Dummy(object):
                def __enter__(self, *a, **kwa):
                    return

                def __exit__(self, *a, **kwa):
                    return

            self.subTest = lambda *a, **kwa: Dummy()

    def test_conversion(self):
        """APL-Python data conversion"""

        # conversion should be on by default unless raw=True is given
        identity = self.apl.fn("⊢")

        d = {"a": 1, "b": 2, "c": [3, 4, 5], "d": {"e": 4, "f": 5}}

        with self.subTest(msg="None should be ⍬"):
            self.assertEqual(identity(None), [])

        with self.subTest(msg="Dictionaries come back in one piece"):
            self.assertEqual(identity(d), d)

        with self.subTest(msg="Dictionaries can be indexed as namespaces in APL"):
            self.assertEqual(d["d"]["f"], self.apl.fn("{⍵.d.f}")(d))

        with self.subTest(msg="Lists come back as lists"):
            self.assertEqual(identity([1, 2, [3, 4]]), [1, 2, [3, 4]])

        with self.subTest(msg="Tuples also come back as lists"):
            self.assertEqual(identity((1, 2, (3, 4))), [1, 2, [3, 4]])

        with self.subTest(msg="Numbers come back as numbers"):
            self.assertEqual(identity(42), 42)

        with self.subTest(msg="Strings come back as strings"):
            self.assertEqual(identity("Hello"), "Hello")

        with self.subTest(msg="Booleans are integers"):
            self.assertEqual(identity(False), 0)
            self.assertEqual(identity(True), 1)

        with self.subTest(msg="Iterables turn up as lists"):
            self.assertEqual(identity(range(5)), [0, 1, 2, 3, 4])
