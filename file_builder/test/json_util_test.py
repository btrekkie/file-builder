import unittest

from ..json_util import JsonUtil


class MyDict(dict):
    pass


class MyList(list):
    pass


class MyTuple(tuple):
    pass


class MyStr(str):
    pass


class MyInt(int):
    pass


class MyFloat(float):
    pass


class JsonUtilTest(unittest.TestCase):
    """Tests the ``JsonUtil`` class."""

    def _check_is_equal_to_hashable(self, value1, value2, is_equal):
        """Check ``is_equal`` and ``to_hashable`` on the specified values.

        Check the results of ``JsonUtil.is_equal(value1, value2)``,
        ``JsonUtil.to_hashable(value1)``, and
        ``JsonUtil.to_hashable(value2)``.

        Arguments:
            value1: The first value.
            value2: The second value.
            is_equal: Whether the values are equal, as in
                ``JsonUtil.is_equal``.
        """
        self.assertEqual(is_equal, JsonUtil.is_equal(value1, value2))

        hashable1 = JsonUtil.to_hashable(value1)
        hashable2 = JsonUtil.to_hashable(value2)
        self.assertEqual(is_equal, hashable1 == hashable2)
        hash(hashable1)
        hash(hashable2)

    def test_is_equal_to_hashable(self):
        """Test ``JsonUtil.is_equal`` and ``JsonUtil.to_hashable``."""
        self._check_is_equal_to_hashable(None, None, True)
        self._check_is_equal_to_hashable(True, True, True)
        self._check_is_equal_to_hashable(True, 1, False)
        self._check_is_equal_to_hashable(7.5, 7.5, True)
        self._check_is_equal_to_hashable(7.0, 7, True)
        self._check_is_equal_to_hashable(42, 42, True)
        self._check_is_equal_to_hashable('foo', 'foo', True)
        self._check_is_equal_to_hashable('', '', True)
        self._check_is_equal_to_hashable('', None, False)
        self._check_is_equal_to_hashable(None, False, False)
        self._check_is_equal_to_hashable(False, [], False)
        self.assertTrue(JsonUtil.is_equal([], ()))
        self._check_is_equal_to_hashable({}, [], False)
        self._check_is_equal_to_hashable(
            [17, ['foo'], None], [17, ['foo'], None], True)
        self.assertTrue(
            JsonUtil.is_equal([17, ('foo',), None], [17, ['foo'], None]))
        self._check_is_equal_to_hashable(
            [17, [0], None], [17, [False], None], False)
        self._check_is_equal_to_hashable(
            [17, ['foo'], None], [17, ['foo'], None, None], False)
        self._check_is_equal_to_hashable({}, {}, True)
        self._check_is_equal_to_hashable({'foo': 'bar'}, {'foo': 'bar'}, True)
        self._check_is_equal_to_hashable(
            {'foo': 5, 'bar': 7}, {'bar': 7, 'foo': 5}, True)
        self._check_is_equal_to_hashable(
            {'foo': 5, 'bar': 7}, {'bar': 7}, False)
        self._check_is_equal_to_hashable(
            {'foo': 5, 'bar': 7}, {'foo': 5, 'baz': 7}, False)
        self._check_is_equal_to_hashable(
            {'foo': 5, 'bar': 7}, {'foo': 5, 'bar': 8}, False)
        self._check_is_equal_to_hashable({'foo': None}, {'foo': None}, True)
        self._check_is_equal_to_hashable({'foo': None}, {}, False)
        self._check_is_equal_to_hashable(
            {'foo': ['e', {'bar': None, 'baz': True}]},
            {'foo': ['e', {'bar': None, 'baz': True}]}, True)
        self._check_is_equal_to_hashable(
            {'foo': ['e', {'bar': None, 'baz': 1}]},
            {'foo': ['e', {'bar': None, 'baz': True}]}, False)

        value1 = {}
        self._check_is_equal_to_hashable(value1, value1, True)
        value2 = ()
        self.assertTrue(JsonUtil.is_equal(value2, value2))
        value3 = {'foo': ['bar']}
        self._check_is_equal_to_hashable(value3, value3, True)

    def _assert_types_are_sanitized(self, value):
        """Assert that the specified value only contains sanitized types.

        It may only have string keys, and it may only consist of
        ``dicts``, ``lists``, ``strs``, ``ints``, ``floats``, ``bools``,
        and ``None``. It may not contain subtypes of those types, and it
        may not contain ``tuples``.
        """
        self.assertIn(
            value.__class__, (dict, list, str, int, float, bool, type(None)))
        if isinstance(value, dict):
            for key, subvalue in value.items():
                self.assertIs(str, key.__class__)
                self._assert_types_are_sanitized(subvalue)
        elif isinstance(value, list):
            for element in value:
                self._assert_types_are_sanitized(element)

    def test_sanitize(self):
        """Test ``JsonUtil.sanitize``."""
        self.assertIsNone(JsonUtil.sanitize(None))
        self.assertIs(True, JsonUtil.sanitize(True))
        self.assertEqual(1, JsonUtil.sanitize(1))
        self.assertEqual([42], JsonUtil.sanitize([42]))
        self.assertEqual([], JsonUtil.sanitize([]))
        self.assertEqual({'foo': 'bar'}, JsonUtil.sanitize({'foo': 'bar'}))
        self.assertEqual({}, JsonUtil.sanitize({}))
        self.assertEqual([], JsonUtil.sanitize(()))
        self.assertEqual(
            [17, [4], 'foo'], JsonUtil.sanitize((17, (4,), 'foo')))

        my_dict = MyDict()
        my_dict['bar'] = 7
        my_list = MyList()
        my_list.append(True)
        my_list.append(False)
        value = JsonUtil.sanitize({
            42: [
                4, my_dict, my_list, MyStr('abc'), MyInt(23), MyFloat(8.7),
                None, -4.8, float('inf'), -float('inf'), (1,), MyTuple()],
            8: 3,
            '8': 3,
            float('inf'): None,
            None: 17,
            False: False,
        })

        expected = {
            '8': 3,
            '42': [
                4, {'bar': 7}, [True, False], 'abc', 23, 8.7, None, -4.8,
                float('inf'), -float('inf'), [1], []],
            'false': False,
            'Infinity': None,
            'null': 17,
        }
        self.assertEqual(expected, value)
        self._assert_types_are_sanitized(value)
        self.assertIs(True, value['42'][2][0])
        self.assertIs(False, value['42'][2][1])
        self.assertIs(int, value['42'][10][0].__class__)
        self.assertIs(False, value['false'])
