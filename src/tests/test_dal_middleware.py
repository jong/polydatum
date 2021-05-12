import pytest


def test_dal_middleware_custom_middleware():
    """
    Verify determining all middleware for the DAL to manage will
    use our default middleware if none is specified, AND if any is
    specified, our default middleware will be added as the last
    middleware.

    We also need to verify that these middlewares chain each other
    in the order that we expect (reversed) and that they ultimately
    use the default handler for dal methods.
    """
    pass


def test_dal_method_middleware():
    """
    Verify that when calling a method on a service off the DAL,
    the method middlewares run, in the correct order and run
    before the method itself is called.


    We deliberately do not use the DalMethodResolverMiddleware here,
    because we are testing middleware call chains, not functionality
    of that class.

        class OuterMiddleware:
            def __call__(self, request, handler):
                assert handler == DataAccessLayer._call
                return handler(request)

        class TestMiddleare:
            def __call__(self, request, handler):
                # setup some test state
                asserty handler == OuterMiddleware
                result = handler(request)
                # verify some test state?
                return result

        with ctx as ctx:
            ctx.dal.fake.service.method()
    """
    pass


def test_dal_method_middleware_abort():
    """
    Verify that when method middleware runs, any middleware that
    raises an exception will prevent the method from getting called.
    """
    pass




def test_dal_attribute_access_returns_dal_method_requester():
    """
    Verify that accessing an attribute on the DAL that does not
    exist returns an instance of DalMethodRequester.

    This is important because this starts building the call chain
    which is used to resolve methods later.

        # need to think about how to do a negative test.
        dal.real = "real attribute"
        del dal.real
        assert isinstance(dal.real, DalMethodRequester)

        thing = dal.foo.bar.fake
        assert isinstance(thing, DalMethodRequester)

        # also make sure to verify the error case where a context
        # has not been started yet.
    """
    # there might already be a test for this that needs updating
    pass


@pytest.mark.skip(reason="Not implemented yet, but needs to be.")
def test_dal_getitem_attribute_access():
    """
    Note: We need to account for this, but I'm not sure how it will work yet.
    Consider this test a placeholder for testing that method, which will need
    to change, but we haven't touched yet.
    """
    assert False


def test_default_dal_handler():
    """
    Verify that the default dal handler performs validation on the request,
    and then calls the dal method that was resolved.

        called_args = []
        def my_method(*args):
            args.append(args)

        request = DalMethodRequest(
            dal_method=my_method,
            args=['foo'],
            kwargs=dict(foo='bar')
        )
        default_handle_dal_method(request)

        assert called_args[0] == whatever


        request = DalMethodRequest()
        with pytest.raises(assertionError):
            default_handle_dal_method(request)
    """
    pass


