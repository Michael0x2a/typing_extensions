import abc
from abc import abstractmethod, abstractproperty
import collections
import contextlib
import sys
#import old_typing as typing
import typing
try:
    import collections.abc as collections_abc
except ImportError:
    import collections as collections_abc  # Fallback for PY3.2.
if sys.version_info[:2] >= (3, 6):
    import _collections_abc # Needed for private function _check_methods # noqa


# Please keep __all__ alphabetized within each category.
__all__ = [
    # Super-special typing primitives.
    'ClassVar',
    'Type',

    # ABCs (from collections.abc).
    'ContextManager',
    # The following are added depending on presence
    # of their non-generic counterparts in stdlib:
    'Awaitable',
    'AsyncIterator',
    'AsyncIterable',
    'Coroutine',
    'Collection',
    # 'AsyncGenerator',
    'AsyncContextManager',

    # Concrete collection types.
    'Counter',
    'Deque',

    # One-off things.
    'NewType',
    'overload',
    'Text',
    'TYPE_CHECKING',
]


# TODO
if hasattr(typing, 'NoReturn'):
    NoReturn = typing.NoReturn
elif hasattr(typing, '_FinalTypingBase'):
    class _NoReturn(typing._FinalTypingBase, _root=True): 
        """Special type indicating functions that never return.
        Example::

          from typing import NoReturn

          def stop() -> NoReturn:
              raise Exception('no way')

        This type is invalid in other positions, e.g., ``List[NoReturn]``
        will fail in static type checkers.
        """
        __slots__ = ()

        def __instancecheck__(self, obj):
            raise TypeError("NoReturn cannot be used with isinstance().")

        def __subclasscheck__(self, cls):
            raise TypeError("NoReturn cannot be used with issubclass().")

    NoReturn = _NoReturn(_root=True)
else:
    class NoReturnMeta(typing.TypingMeta):
        """Metaclass for NoReturn"""
        def __new__(cls, name, bases, namespace, _root=False):
            return super().__new__(cls, name, bases, namespace, _root=_root)

        def __instancecheck__(self, obj):
            raise TypeError("NoReturn cannot be used with isinstance().")

        def __subclasscheck__(self, cls):
            raise TypeError("NoReturn cannot be used with issubclass().")

    class NoReturn(typing.Final, metaclass=NoReturnMeta, _root=True):
        """Special type indicating functions that never return.
        Example::

          from typing import NoReturn

          def stop() -> NoReturn:
              raise Exception('no way')

        This type is invalid in other positions, e.g., ``List[NoReturn]``
        will fail in static type checkers.
        """
        __slots__ = ()


# TODO: Can we clean up any of these?
# Some unconstrained type variables.  These are used by the container types.
# (These are not for export.)
T = typing.TypeVar('T')  # Any type.
KT = typing.TypeVar('KT')  # Key type.
VT = typing.TypeVar('VT')  # Value type.
T_co = typing.TypeVar('T_co', covariant=True)  # Any type covariant containers.
V_co = typing.TypeVar('V_co', covariant=True)  # Any type covariant containers.
VT_co = typing.TypeVar('VT_co', covariant=True)  # Value type covariant containers.
T_contra = typing.TypeVar('T_contra', contravariant=True)  # Ditto contravariant.


def _gorg(a):
    """Return the farthest origin of a generic class (internal helper)."""
    assert isinstance(a, GenericMeta)
    while a.__origin__ is not None:
        a = a.__origin__
    return a


def _geqv(a, b):
    """Return whether two generic classes are equivalent (internal helper).

    The intention is to consider generic class X and any of its
    parameterized forms (X[T], X[int], etc.) as equivalent.

    However, X is not equivalent to a subclass of X.

    The relation is reflexive, symmetric and transitive.
    """
    assert isinstance(a, GenericMeta) and isinstance(b, GenericMeta)
    # Reduce each to its origin.
    return _gorg(a) is _gorg(b)


# TODO
if hasattr(typing, 'ClassVar'):
    ClassVar = typing.ClassVar
else:
    class ClassVar:
        """Special type construct to mark class variables.

        An annotation wrapped in ClassVar indicates that a given
        attribute is intended to be used as a class variable and
        should not be set on instances of that class. Usage::

          class Starship:
              stats: ClassVar[Dict[str, int]] = {} # class variable
              damage: int = 10                     # instance variable

        ClassVar accepts only types and cannot be further subscribed.

        Note that ClassVar is not a class itself, and should not
        be used with isinstance() or issubclass().
        """

        __slots__ = ('__type__',)

        def __init__(self, tp=None, **kwds):
            self.__type__ = tp

        def __getitem__(self, item):
            cls = type(self)
            cls_name = cls.__name__[1:]
            if self.__type__ is None:
                return cls(typing._type_check(item,
                           '{} accepts only single type.'.format(cls_name)))
            raise TypeError('{} cannot be further subscripted'
                            .format(cls_name))


def _overload_dummy(*args, **kwds):
    """Helper for @overload to raise when called."""
    raise NotImplementedError(
        "You should not call an overloaded function. "
        "A series of @overload-decorated functions "
        "outside a stub module should always be followed "
        "by an implementation that is not @overload-ed.")


# TODO: Keep?
def overload(func):
    """Decorator for overloaded functions/methods.

    In a stub file, place two or more stub definitions for the same
    function in a row, each decorated with @overload.  For example:

      @overload
      def utf8(value: None) -> None: ...
      @overload
      def utf8(value: bytes) -> bytes: ...
      @overload
      def utf8(value: str) -> bytes: ...

    In a non-stub file (i.e. a regular .py file), do the same but
    follow it with an implementation.  The implementation should *not*
    be decorated with @overload.  For example:

      @overload
      def utf8(value: None) -> None: ...
      @overload
      def utf8(value: bytes) -> bytes: ...
      @overload
      def utf8(value: str) -> bytes: ...
      def utf8(value):
          # implementation goes here
    """
    return _overload_dummy


# Internal type variable used for Type[].
CT_co = typing.TypeVar('CT_co', covariant=True, bound=type)


# TODO
# This is not a real generic class.  Don't use outside annotations.
class Type(typing.Generic[CT_co], extra=type):
    """A special construct usable to annotate class objects.

    For example, suppose we have the following classes::

      class User: ...  # Abstract base for User classes
      class BasicUser(User): ...
      class ProUser(User): ...
      class TeamUser(User): ...

    And a function that takes a class argument that's a subclass of
    User and returns an instance of the corresponding class::

      U = TypeVar('U', bound=User)
      def new_user(user_class: Type[U]) -> U:
          user = user_class()
          # (Here we could write the user object to a database)
          return user
      joe = new_user(BasicUser)

    At this point the type checker knows that joe has type BasicUser.
    """

    __slots__ = ()


# Various ABCs mimicking those in collections.abc.
# A few are simply re-exported for completeness.

def _get_extra(name):
    return getattr(collections_abc, name, None)

# TODO
if hasattr(typing, 'Awaitable'):
    Awaitable = typing.Awaitable
else:
    class Awaitable(typing.Generic[T_co], extra=_get_extra('Awaitable')):
        __slots__ = ()


# TODO
if hasattr(typing, 'Coroutine'):
    Coroutine = typing.Coroutine
else:
    class Coroutine(Awaitable[V_co], typing.Generic[T_co, T_contra, V_co],
                    extra=_get_extra('Coroutine')):
        __slots__ = ()


# TODO
if hasattr(typing, 'AsyncIterable'):
    AsyncIterable = typing.AsyncIterable
    AsyncIterator = typing.AsyncIterator
else:
    class AsyncIterable(typing.Generic[T_co],
                        extra=_get_extra('AsyncIterable')):
        __slots__ = ()

    class AsyncIterator(AsyncIterable[T_co],
                        extra=_get_extra('AsyncIterator')):
        __slots__ = ()


# TODO
if hasattr(typing, 'Collection'):
    Collection = typing.Collection
else:
    class Collection(typing.Sized,
                     typing.Iterable[T_co],
                     typing.Container[T_co],
                     extra=_get_extra('Collection')):
        __slots__ = ()


# TODO
if hasattr(typing, 'Deque'):
    Deque = typing.Deque
else:
    class Deque(collections.deque, typing.MutableSequence[T],
                extra=collections.deque):
        __slots__ = ()

        def __new__(cls, *args, **kwds):
            if _geqv(cls, Deque):
                return collections.deque(*args, **kwds)
            return _generic_new(collections.deque, cls, *args, **kwds)



# TODO
if hasattr(typing, 'ContextManager'):
    ContextManager = typing.ContextManager
elif hasattr(contextlib, 'AbstractContextManager'):
    class ContextManager(typing.Generic[T_co],
                         extra=contextlib.AbstractContextManager):
        __slots__ = ()
else:
    class ContextManager(typing.Generic[T_co]):
        __slots__ = ()

        def __enter__(self):
            return self

        @abc.abstractmethod
        def __exit__(self, exc_type, exc_value, traceback):
            return None

        @classmethod
        def __subclasshook__(cls, C):
            if cls is ContextManager:
                # In Python 3.6+, it is possible to set a method to None to
                # explicitly indicate that the class does not implement an ABC
                # (https://bugs.python.org/issue25958), but we do not support
                # that pattern here because this fallback class is only used
                # in Python 3.5 and earlier.
                if (any("__enter__" in B.__dict__ for B in C.__mro__) and
                    any("__exit__" in B.__dict__ for B in C.__mro__)):
                    return True
            return NotImplemented


if hasattr(typing, 'AsyncContextManager'):
    AsyncContextManager = typing.AsyncContextManager
    __all__.append('AsyncContextManager')
elif hasattr(contextlib, 'AbstractAsyncContextManager'):
    class AsyncContextManager(typing.Generic[T_co],
                              extra=contextlib.AbstractAsyncContextManager):
        __slots__ = ()

    __all__.append('AsyncContextManager')
elif sys.version_info[:2] >= (3, 5):
    exec("""
class AsyncContextManager(typing.Generic[T_co]):
    __slots__ = ()

    async def __aenter__(self):
        return self

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncContextManager:
            if sys.version_info[:2] >= (3, 6):
                return _collections_abc._check_methods(C, "__aenter__", "__aexit__")
            if (any("__aenter__" in B.__dict__ for B in C.__mro__) and
                    any("__aexit__" in B.__dict__ for B in C.__mro__)):
                return True
        return NotImplemented

__all__.append('AsyncContextManager')
""")


# TODO
if hasattr(typing, 'DefaultDict'):
    DefaultDict = typing.DefaultDict
else:
    class DefaultDict(collections.defaultdict, typing.MutableMapping[KT, VT],
                      extra=collections.defaultdict):

        __slots__ = ()

        def __new__(cls, *args, **kwds):
            if _geqv(cls, typing.DefaultDict):
                return collections.defaultdict(*args, **kwds)
            return _generic_new(collections.defaultdict, cls, *args, **kwds)


# TODO
if hasattr(typing, 'Counter'):
    Counter = typing.Counter
else:
    class Counter(collections.Counter, typing.Dict[T, int],
                  extra=collections.Counter):

        __slots__ = ()

        def __new__(cls, *args, **kwds):
            if _geqv(cls, Counter):
                return collections.Counter(*args, **kwds)
            return _generic_new(collections.Counter, cls, *args, **kwds)


# TODO
if hasattr(typing, 'ChainMap'):
    ChainMap = typing.ChainMap
    __all__.append('ChainMap')
elif hasattr(collections, 'ChainMap'):
    # ChainMap only exists in 3.3+
    class ChainMap(collections.ChainMap, typing.MutableMapping[KT, VT],
                   extra=collections.ChainMap):

        __slots__ = ()

        def __new__(cls, *args, **kwds):
            if _geqv(cls, ChainMap):
                return collections.ChainMap(*args, **kwds)
            return _generic_new(collections.ChainMap, cls, *args, **kwds)

    __all__.append('ChainMap')


# TODO
if hasattr(typing, 'AsyncGenerator'):
    AsyncGenerator = typing.AsyncGenerator
else:
    class AsyncGenerator(AsyncIterator[T_co], typing.Generic[T_co, T_contra],
                         extra=_get_extra('AsyncGenerator')):
        __slots__ = ()


# TODO
if hasattr(typing, 'NewType'):
    NewType = typing.NewType
else:
    def NewType(name, tp):
        """NewType creates simple unique types with almost zero
        runtime overhead. NewType(name, tp) is considered a subtype of tp
        by static type checkers. At runtime, NewType(name, tp) returns
        a dummy function that simply returns its argument. Usage::

            UserId = NewType('UserId', int)

            def name_by_id(user_id: UserId) -> str:
                ...

            UserId('user')          # Fails type check

            name_by_id(42)          # Fails type check
            name_by_id(UserId(42))  # OK

            num = UserId(5) + 1     # type: int
        """

        def new_type(x):
            return x

        new_type.__name__ = name
        new_type.__supertype__ = tp
        return new_type


# TODO
if hasattr(typing, 'Text'):
    Text = typing.Text
elif sys.version_info < (3, 0):
    # Python-version-specific alias (Python 2: unicode; Python 3: str)
    Text = unicode
else:
    Text = str


# TODO
if hasattr(typing, 'TYPE_CHECKING'):
    TYPE_CHECKING = typing.TYPE_CHECKING
else:
    # Constant that's True when type checking, but False here.
    TYPE_CHECKING = False

