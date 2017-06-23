import abc
from abc import abstractmethod, abstractproperty
import collections
import contextlib
import functools
import sys
import types
#import old_typing as typing
import typing
try:
    import collections.abc as collections_abc
except ImportError:
    import collections as collections_abc  # Fallback for PY3.2.
if sys.version_info[:2] >= (3, 6):
    import _collections_abc  # Needed for private function _check_methods # noqa


# Please keep __all__ alphabetized within each category.
__all__ = [
    # Super-special typing primitives.
    'ClassVar',
    'Type',

    # ABCs (from collections.abc).
    'GenericMeta',  # subclass of abc.ABCMeta and a metaclass
                    # for 'Generic' and ABCs below.
    'ContextManager',
    # The following are added depending on presence
    # of their non-generic counterparts in stdlib:
    # Awaitable,
    # AsyncIterator,
    # AsyncIterable,
    # Coroutine,
    # Collection,
    # AsyncGenerator,
    # AsyncContextManager

    # Concrete collection types.
    'Counter',
    'Deque',

    # One-off things.
    'NewType',
    'no_type_check',
    'overload',
    'Text',
    'TYPE_CHECKING',
]

# The pseudo-submodules 're' and 'io' are part of the public
# namespace, but excluded from __all__ because they might stomp on
# legitimate imports of those modules.


def _qualname(x):
    if sys.version_info[:2] >= (3, 3):
        return x.__qualname__
    else:
        # Fall back to just name.
        return x.__name__


def _trim_name(nm):
    whitelist = ('_TypeAlias', '_ForwardRef', '_TypingBase', '_FinalTypingBase')
    if nm.startswith('_') and nm not in whitelist:
        nm = nm[1:]
    return nm


class _TypingBase(metaclass=typing.TypingMeta, _root=True):
    """Internal indicator of special typing constructs."""

    __slots__ = ('__weakref__',)

    def __init__(self, *args, **kwds):
        pass

    def __new__(cls, *args, **kwds):
        """Constructor.

        This only exists to give a better error message in case
        someone tries to subclass a special typing object (not a good idea).
        """
        if (len(args) == 3 and
                isinstance(args[0], str) and
                isinstance(args[1], tuple)):
            # Close enough.
            raise TypeError("Cannot subclass %r" % cls)
        return super().__new__(cls)

    # Things that are not classes also need these.
    def _eval_type(self, globalns, localns):
        return self

    def _get_type_vars(self, tvars):
        pass

    def __repr__(self):
        cls = type(self)
        qname = _trim_name(_qualname(cls))
        return '%s.%s' % (cls.__module__, qname)

    def __call__(self, *args, **kwds):
        raise TypeError("Cannot instantiate %r" % type(self))


class _FinalTypingBase(_TypingBase, _root=True):
    """Internal mix-in class to prevent instantiation.

    Prevents instantiation unless _root=True is given in class call.
    It is used to create pseudo-singleton instances Any, Union, Optional, etc.
    """

    __slots__ = ()

    def __new__(cls, *args, _root=False, **kwds):
        self = super().__new__(cls, *args, **kwds)
        if _root is True:
            return self
        raise TypeError("Cannot instantiate %r" % cls)

    def __reduce__(self):
        return _trim_name(type(self).__name__)


class _ForwardRef(_TypingBase, _root=True):
    """Internal wrapper to hold a forward reference."""

    __slots__ = ('__forward_arg__', '__forward_code__',
                 '__forward_evaluated__', '__forward_value__')

    def __init__(self, arg):
        super().__init__(arg)
        if not isinstance(arg, str):
            raise TypeError('Forward reference must be a string -- got %r' % (arg,))
        try:
            code = compile(arg, '<string>', 'eval')
        except SyntaxError:
            raise SyntaxError('Forward reference must be an expression -- got %r' %
                              (arg,))
        self.__forward_arg__ = arg
        self.__forward_code__ = code
        self.__forward_evaluated__ = False
        self.__forward_value__ = None

    def _eval_type(self, globalns, localns):
        if not self.__forward_evaluated__ or localns is not globalns:
            if globalns is None and localns is None:
                globalns = localns = {}
            elif globalns is None:
                globalns = localns
            elif localns is None:
                localns = globalns
            self.__forward_value__ = _type_check(
                eval(self.__forward_code__, globalns, localns),
                "Forward references must evaluate to types.")
            self.__forward_evaluated__ = True
        return self.__forward_value__

    def __eq__(self, other):
        if not isinstance(other, _ForwardRef):
            return NotImplemented
        return (self.__forward_arg__ == other.__forward_arg__ and
                self.__forward_value__ == other.__forward_value__)

    def __hash__(self):
        return hash((self.__forward_arg__, self.__forward_value__))

    def __instancecheck__(self, obj):
        raise TypeError("Forward references cannot be used with isinstance().")

    def __subclasscheck__(self, cls):
        raise TypeError("Forward references cannot be used with issubclass().")

    def __repr__(self):
        return '_ForwardRef(%r)' % (self.__forward_arg__,)


def _eval_type(t, globalns, localns):
    if isinstance(t, TypingMeta) or isinstance(t, _TypingBase):
        return t._eval_type(globalns, localns)
    return t


def _type_check(arg, msg):
    """Check that the argument is a type, and return it (internal helper).

    As a special case, accept None and return type(None) instead.
    Also, _TypeAlias instances (e.g. Match, Pattern) are acceptable.

    The msg argument is a human-readable error message, e.g.

        "Union[arg, ...]: arg should be a type."

    We append the repr() of the actual value (truncated to 100 chars).
    """
    if arg is None:
        return type(None)
    if isinstance(arg, str):
        arg = _ForwardRef(arg)
    if (
        isinstance(arg, _TypingBase) and type(arg).__name__ == '_ClassVar' or
        not isinstance(arg, (type, _TypingBase)) and not callable(arg)
    ):
        raise TypeError(msg + " Got %.100r." % (arg,))
    # Bare Union etc. are not valid as type arguments
    if (
        type(arg).__name__ in ('_Union', '_Optional') and
        not getattr(arg, '__origin__', None) or
        isinstance(arg, TypingMeta) and _gorg(arg) in (typing.Generic, typing._Protocol)
    ):
        raise TypeError("Plain %s is not valid as type argument" % arg)
    return arg


def _type_repr(obj):
    """Return the repr() of an object, special-casing types (internal helper).

    If obj is a type, we return a shorter version than the default
    type.__repr__, based on the module and qualified name, which is
    typically enough to uniquely identify a type.  For everything
    else, we fall back on repr(obj).
    """
    if isinstance(obj, type) and not isinstance(obj, TypingMeta):
        if obj.__module__ == 'builtins':
            return _qualname(obj)
        return '%s.%s' % (obj.__module__, _qualname(obj))
    if obj is ...:
        return('...')
    if isinstance(obj, types.FunctionType):
        return obj.__name__
    return repr(obj)


class _NoReturn(_FinalTypingBase, _root=True):
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


# TODO
NoReturn = _NoReturn(_root=True)


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


class _ClassVar(_FinalTypingBase, _root=True):
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
        if self.__type__ is None:
            return cls(_type_check(item,
                       '{} accepts only single type.'.format(cls.__name__[1:])),
                       _root=True)
        raise TypeError('{} cannot be further subscripted'
                        .format(cls.__name__[1:]))

    def _eval_type(self, globalns, localns):
        new_tp = _eval_type(self.__type__, globalns, localns)
        if new_tp == self.__type__:
            return self
        return type(self)(new_tp, _root=True)

    def __repr__(self):
        r = super().__repr__()
        if self.__type__ is not None:
            r += '[{}]'.format(_type_repr(self.__type__))
        return r

    def __hash__(self):
        return hash((type(self).__name__, self.__type__))

    def __eq__(self, other):
        if not isinstance(other, _ClassVar):
            return NotImplemented
        if self.__type__ is not None:
            return self.__type__ == other.__type__
        return self is other


# TODO
ClassVar = _ClassVar(_root=True)


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


# Various ABCs mimicking those in collections.abc.
# A few are simply re-exported for completeness.


if hasattr(collections_abc, 'Awaitable'):
    class Awaitable(typing.Generic[T_co], extra=collections_abc.Awaitable):
        __slots__ = ()

    __all__.append('Awaitable')


# TODO
if hasattr(collections_abc, 'Coroutine'):
    class Coroutine(Awaitable[V_co], typing.Generic[T_co, T_contra, V_co],
                    extra=collections_abc.Coroutine):
        __slots__ = ()

    __all__.append('Coroutine')


# TODO
if hasattr(collections_abc, 'AsyncIterable'):

    class AsyncIterable(typing.Generic[T_co], extra=collections_abc.AsyncIterable):
        __slots__ = ()

    class AsyncIterator(AsyncIterable[T_co],
                        extra=collections_abc.AsyncIterator):
        __slots__ = ()

    __all__.append('AsyncIterable')
    __all__.append('AsyncIterator')


# TODO
if hasattr(collections_abc, 'Collection'):
    class Collection(Sized, Iterable[T_co], Container[T_co],
                     extra=collections_abc.Collection):
        __slots__ = ()

    __all__.append('Collection')

# TODO
class Deque(collections.deque, typing.MutableSequence[T], extra=collections.deque):

    __slots__ = ()

    def __new__(cls, *args, **kwds):
        if _geqv(cls, Deque):
            return collections.deque(*args, **kwds)
        return _generic_new(collections.deque, cls, *args, **kwds)


if hasattr(contextlib, 'AbstractContextManager'):
    class ContextManager(typing.Generic[T_co], extra=contextlib.AbstractContextManager):
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


if hasattr(contextlib, 'AbstractAsyncContextManager'):
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


class DefaultDict(collections.defaultdict, typing.MutableMapping[KT, VT],
                  extra=collections.defaultdict):

    __slots__ = ()

    def __new__(cls, *args, **kwds):
        if _geqv(cls, typing.DefaultDict):
            return collections.defaultdict(*args, **kwds)
        return _generic_new(collections.defaultdict, cls, *args, **kwds)


class Counter(collections.Counter, typing.Dict[T, int],
              extra=collections.Counter):

    __slots__ = ()

    def __new__(cls, *args, **kwds):
        if _geqv(cls, Counter):
            return collections.Counter(*args, **kwds)
        return _generic_new(collections.Counter, cls, *args, **kwds)


if hasattr(collections, 'ChainMap'):
    # ChainMap only exists in 3.3+
    __all__.append('ChainMap')

    class ChainMap(collections.ChainMap, typing.MutableMapping[KT, VT],
                   extra=collections.ChainMap):

        __slots__ = ()

        def __new__(cls, *args, **kwds):
            if _geqv(cls, ChainMap):
                return collections.ChainMap(*args, **kwds)
            return _generic_new(collections.ChainMap, cls, *args, **kwds)


# TODO
if hasattr(collections_abc, 'AsyncGenerator'):
    class AsyncGenerator(AsyncIterator[T_co], typing.Generic[T_co, T_contra],
                         extra=collections_abc.AsyncGenerator):
        __slots__ = ()

    __all__.append('AsyncGenerator')


# TODO
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
# Python-version-specific alias (Python 2: unicode; Python 3: str)
Text = str


# TODO
# Constant that's True when type checking, but False here.
TYPE_CHECKING = False

