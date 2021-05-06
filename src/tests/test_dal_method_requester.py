import pytest

from polydatum.dal import DalMethodRequester, PathSegment


def test_deferred_attribute_access(path_arg):
    """
    Verify that we can access non-existent attributes on this class and
    that we can access arbitrarily deep non-existent attributes.
    """
    dmr = DalMethodRequester(lambda: None, path_arg())
    assert isinstance(dmr.foo, DalMethodRequester)
    assert isinstance(dmr.foo.bar, DalMethodRequester)
    assert isinstance(dmr.foo.bar.baz, DalMethodRequester)

    # Use a different non-existent service, to help make it clear that there
    # is nothing special about the `foo` service above.
    assert isinstance(dmr.anything, DalMethodRequester)
    assert isinstance(dmr.example, DalMethodRequester)


def test_dal_method_requester_handler_chain(path_arg):
    """
    Verify that the handler for a DalMethodRequester instance is preserved
    regardless of how deep a deferred attribute lookup chain is.

    Ultimately this class is responsible for deferring attribute access and
    calling the handler with a built up chain of PathSegments. We want to
    make sure that the handler is the same regardless of where in the
    deferred attribute access it is finally called.
    """

    # The impl here doesn't matter, we are only checking
    # for identity with this callable.
    # Even the signature of this callable doesn't matter right here.
    def specific_handler():
        pass

    dmr = DalMethodRequester(specific_handler, path_arg())
    assert dmr.foo._handler is specific_handler
    assert dmr.foo.bar._handler is specific_handler
    assert dmr.foo.bar.baz._handler is specific_handler


def test_dal_method_requester_handler_called(path_arg):
    """
    Verify that the handler for a DalMethodRequester gets called when the
    DalMethodRequester is called.
    """
    def handler(path_chain, *args, **kwargs):
        return path_chain, args, kwargs

    test_path_segment = path_arg()
    dmr = DalMethodRequester(handler, test_path_segment)
    test_args = ('foo', 'bar')
    test_kwargs = dict(example='test', other='monkey')
    for requester in [dmr, dmr.foo.bar, dmr.monkey.gorilla.orangutan]:
        called_path_segment, called_args, called_kwargs = requester(*test_args, **test_kwargs)
        assert isinstance(called_path_segment[0], PathSegment)
        assert called_path_segment[0].name == test_path_segment[0].name
        assert called_args == test_args
        assert called_kwargs == test_kwargs


def test_dal_method_requester_path_chaining(path_arg):
    """
    Verify that deeper attribute access on a DalMethodRequester will
    nest path segments when building up the path call chain.

    Maintaining order is important.

        dmr = DalMethodRequester()
        deep_dmr = dmr.foo.bar.baz.method
        assert deep_dmr.path = (PathSegment(name=foo), PathSegment(name=bar), ...)
        assert deep_dmr.non_existent.path == (deep_dmr.path + PathSegment(name=non_existent))
    """
    dmr = DalMethodRequester(lambda: None, path_arg('animals'))
    nested_dmr = dmr.foo.bar.baz.monkey.gorilla
    expected_path_chain = (
        PathSegment(name='animals'),
        PathSegment(name='foo'),
        PathSegment(name='bar'),
        PathSegment(name='baz'),
        PathSegment(name='monkey'),
        PathSegment(name='gorilla')
    )
    assert nested_dmr.path == expected_path_chain

