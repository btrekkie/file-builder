class JsonUtil:
    """Provides static utility methods pertaining to JSON.

    A JSON value is said to be "sanitized" if it is a possible return
    value of ``json.loads(json.dumps(value))``. In particular, it may
    only have string keys, and it may only consist of ``dicts``,
    ``lists``, ``strs``, ``ints``, ``floats``, ``bools``, and ``None``.
    It may not contain subtypes of those types, and it may not contain
    ``tuples``.
    """

    @staticmethod
    def is_equal(value1, value2):
        """Return whether the specified JSON values are equal.

        The values must be sanitized, except they may contain ``tuples``
        (but not instances of subclasses of ``tuple``). This differs
        from ``==`` in that ``lists`` may be regarded as equal to
        ``tuples``, and ``bools`` are never regarded as equal to
        ``ints``.
        """
        class1 = value1.__class__
        class2 = value2.__class__
        if class1 == list or class1 == tuple:
            if ((class2 != list and class2 != tuple) or
                    len(value1) != len(value2)):
                return False
            for element1, element2 in zip(value1, value2):
                if not JsonUtil.is_equal(element1, element2):
                    return False
            return True
        elif class1 == dict:
            if class2 != dict or len(value1) != len(value2):
                return False
            for key, subvalue in value1.items():
                if (key not in value2 or
                        not JsonUtil.is_equal(subvalue, value2[key])):
                    return False
            return True
        elif (class1 == bool) != (class2 == bool):
            # Booleans are special, because True == 1 and False == 0
            return False
        else:
            return value1 == value2

    @staticmethod
    def to_hashable(value):
        """Return a hashable representation of the given sanitized JSON value.

        This operation preserves equality, in the sense that
        ``to_hashable(value1) == to_hashable(value2)`` if and only if
        ``is_equal(value1, value2)``.
        """
        cls = value.__class__
        if cls == list:
            return (0,) + tuple(
                [JsonUtil.to_hashable(element) for element in value])
        elif cls == dict:
            result = []
            for key in sorted(value.keys()):
                result.append(key)
                result.append(JsonUtil.to_hashable(value[key]))
            return tuple(result)
        elif cls == bool:
            # Booleans are special, because True == 1 and False == 0
            if value:
                return (1,)
            else:
                return (2,)
        else:
            return value

    @staticmethod
    def sanitize(value):
        """Return the result of sanitizing the specified JSON value.

        This is equivalent to ``json.loads(json.dumps(value))``.

        Raises:
            TypeError: If ``value`` is not a JSON value. (Any
                dictionaries in ``value`` are permitted to have keys of
                type ``int``, ``float``, ``bool``, or ``NoneType``.)
        """
        cls = value.__class__
        if (cls == str or cls == int or cls == float or cls == bool or
                value is None):
            return value

        if isinstance(value, (list, tuple)):
            return list([JsonUtil.sanitize(element) for element in value])
        elif isinstance(value, dict):
            result = {}
            for key, subvalue in value.items():
                result[JsonUtil._key_to_str(key)] = JsonUtil.sanitize(subvalue)
            return result
        elif isinstance(value, str):
            return str(value)
        elif isinstance(value, int):
            return int(value)
        elif isinstance(value, float):
            return float(value)
        else:
            raise TypeError('The value is not a JSON value')

    @staticmethod
    def _key_to_str(key):
        """Convert the specified JSON key to a string.

        This returns the string that ``json.dumps`` produces when
        serializing the specified object key. In other words, this is
        equivalent to
        ``list(json.loads(json.dumps({key: None})).keys())[0]``.
        """
        if key.__class__ == str:
            return key
        elif isinstance(key, str):
            return str(key)
        elif isinstance(key, bool):
            if bool(key):
                return 'true'
            else:
                return 'false'
        elif isinstance(key, int):
            return repr(key)
        elif isinstance(key, float):
            if key != key:
                return 'NaN'
            elif key == float('inf'):
                return 'Infinity'
            elif key == -float('inf'):
                return '-Infinity'
            else:
                return repr(key)
        elif key is None:
            return 'null'
        else:
            raise TypeError('The value is not a JSON value')
