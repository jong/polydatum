def test_deferred_attribute_access():
    """
    Verify that we can access non-existent attributes on this class and
    that we can access arbitrarily deep non-existent attributes.

        def whatever():
            pass

        dmr = DalMethodRequester(whatever, (PathSegment(name='root'),)
        assert isinstance(dmr.foo, DalMethodRequester)
        assert isinstance(dmr.foo.bar, DalMethodRequester)
        assert isinstance(dmr.foo.bar.baz, DalMethodRequester)
    """
    pass

def test_dal_method_requester_handler_chain():
    """
    Verify that the handler for a DalMethodRequester instance is preserved
    regardless of how deep a deferred attribute lookup chain is.

    Ultimately this class is responsible for deferring attribute access and
    calling the handler with a built up chain of PathSegments. We want to
    make sure that the handler is the same regardless of where in the
    deferred attribute access it is finally called.

        def whatever():
            pass

        dmr = DalMethodRequester(whatever, (PathSegment(name='root'),)
        assert dmr.foo._handler === whatever
        assert dmr.foo.bar._handler === whatever
        assert dmr.foo.bar.baz._handler === whatever
    """

def test_dal_method_requester_handler_called():
    """
    Verify that the handler for a DalMethodRequester gets called when the
    DalMethodRequester is called.

        args = []

        def handler(path_chain, *args, **kwargs):
            args.append([path_chain, args, kwargs])

        dmr = DalMethodRequester(handler, ...)
        dmr.foo.('test', thing='whatever')
        assert len(args) == 1
        assert args[0][0] == tuple of PathSegment
        assert args[0][1] == 'test'
        assert args[0][2] == dict(thing='wahtever')

        # assert a different length call chain here, just to be exhaustive
        dmr.foo.bar.baz('test', thing='whatever')
        assert len(args) == 1
        assert args[0][0] == tuple of PathSegment
        assert args[0][1] == 'test'
        assert args[0][2] == dict(thing='wahtever')
    """
    pass


def test_dal_method_requester_path_chaining():
    """
    Verify that deeper attribute access on a DalMethodRequester will
    nest path segments when building up the path call chain.

    Maintaining order is important.

        dmr = DalMethodRequester()
        deep_dmr = dmr.foo.bar.baz.method
        assert deep_dmr._path = (PathSegment(name=foo), PathSegment(name=bar), ...)
        assert deep_dmr.non_existent._path == (deep_dmr._path + PathSegment(name=non_existent))
    """
    pass


