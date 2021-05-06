import pytest

from polydatum import DataAccessLayer, Service
from polydatum.dal import DalMethodResolverMiddleware, MethodMiddleware, InvalidMiddleware, DalMethodRequest, \
    default_handle_dal_method, DataManager, PathSegment, DalMethodRequester


def test_dal_middleware_requires_method_middleware():
    """
    Verify that the DAL will raise an error if you try to
    register method middleware that does not subclass the
    base class for method middleware: MethodMiddleware.
    """
    class FooMiddleware:
        pass

    with pytest.raises(InvalidMiddleware):
        DataAccessLayer(data_manager=None, middleware=[FooMiddleware()])


def test_dal_middleware_instantiation_not_needed():
    """
    Verify that you can specify method middleware as either an instance
    or a class (as a convenience).
    """
    class FooMiddleware(MethodMiddleware):
        pass

    dal = DataAccessLayer(data_manager=None, middleware=[FooMiddleware], default_middleware=None)
    assert isinstance(dal._reversed_middleware[0], FooMiddleware)

    dal = DataAccessLayer(data_manager=None, middleware=[FooMiddleware()], default_middleware=None)
    assert isinstance(dal._reversed_middleware[0], FooMiddleware)


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
    # Verify default behavior first.
    # Passing an empty DM here because we don't care about this
    # for the purposes of the test, and it's not used.
    dal = DataAccessLayer(data_manager=None)
    assert len(dal._reversed_middleware) == 1
    assert isinstance(dal._reversed_middleware[0], DalMethodResolverMiddleware)

    # Verify custom default middleware
    class ExampleMiddleware(MethodMiddleware):
        pass

    dal = DataAccessLayer(data_manager=None, default_middleware=(ExampleMiddleware,))
    assert len(dal._reversed_middleware) == 1
    assert isinstance(dal._reversed_middleware[0], ExampleMiddleware)

    # Verify that even if you specify middleware, the default
    # middleware gets appended to the end of the middleware stack.
    # We test for this specifically because the default middleware
    # needs to be run 'last'.

    class FooMiddleware(MethodMiddleware):
        pass

    class BarMiddleware(MethodMiddleware):
        pass

    class BazMiddleware(MethodMiddleware):
        pass

    middlewares = [FooMiddleware, BarMiddleware, BazMiddleware]
    dal = DataAccessLayer(data_manager=None, middleware=list(middlewares))

    # The DAL handles making sure all of these are instantiated, but
    # we have to manually do it for testing here.
    middlewares.append(DalMethodResolverMiddleware)
    expected_middlewares = []
    for m in reversed(middlewares):
        expected_middlewares.append(m())

    # Verify if the objects in dal._reversed_middleware are instances of the
    # expected middleware types in the right order
    for i in range(0, len(expected_middlewares)):
        assert isinstance(dal._reversed_middleware[0], type(expected_middlewares[0]))


def test_dal_method_middleware():
    """
    Verify that when calling a method on a service off the DAL,
    the method middlewares run, in the correct order and run
    before the method itself is called.


    We deliberately do not use the DalMethodResolverMiddleware here,
    because we are testing middleware call chains, not functionality
    of that class.
    """
    middleware_requests = []

    def test_method():
        middleware_requests.append(('default-handler-call', None))

    class OuterMiddleware(MethodMiddleware):
        def __call__(self, request, handler):
            middleware_requests.append(('outer-middleware-ingress', request))
            result = handler(request)
            middleware_requests.append(('outer-middleware-egress', request))
            return result

    class SecondMiddleware(MethodMiddleware):
        def __call__(self, request, handler):
            middleware_requests.append(('second-middleware-ingress', request))
            result = handler(request)
            middleware_requests.append(('second-middleware-egress', request))
            return result

    # Verify custom default middleware
    class DefaultMiddleware(MethodMiddleware):
        def __call__(self, request, handler):
            middleware_requests.append(('default-middleware-ingress', request))
            # We need to get past the DalMethodResolverMiddleware
            # which sets the `dal_method` attribute to
            # the method that has to be called
            request.dal_method = test_method
            result = handler(request)
            middleware_requests.append(('default-middleware-egress', request))
            return result

    dm = DataManager()

    dal = DataAccessLayer(data_manager=dm, middleware=[OuterMiddleware, SecondMiddleware],
                          default_middleware=(DefaultMiddleware,))

    with dm.context():
        dal.fake.service.method()

    first_middleware_to_run = middleware_requests[0]
    assert first_middleware_to_run[0] == 'outer-middleware-ingress'
    second_middleware_to_run = middleware_requests[1]
    assert second_middleware_to_run[0] == 'second-middleware-ingress'
    default_middleware_to_run = middleware_requests[2]
    assert default_middleware_to_run[0] == 'default-middleware-ingress'

    default_method_to_run = middleware_requests[3]
    assert default_method_to_run[0] == 'default-handler-call'

    default_middleware_to_run_egress = middleware_requests[4]
    assert default_middleware_to_run_egress[0] == 'default-middleware-egress'
    second_middleware_to_run_egress = middleware_requests[5]
    assert second_middleware_to_run_egress[0] == 'second-middleware-egress'
    first_middleware_to_run_egress = middleware_requests[6]
    assert first_middleware_to_run_egress[0] == 'outer-middleware-egress'


def test_dal_method_middleware_abort():
    """
    Verify that when method middleware runs, any middleware that
    raises an exception will prevent the method from getting called.
    """

    middleware_requests = []

    class SpecificException(Exception):
        pass

    def test_method():
        middleware_requests.append("test_method_called")
        return True

    class AuthMiddleware(MethodMiddleware):
        """
        An example middleware for authentication purposes
        """

        def user_is_authenticated(self, path):
            """
            Simulating an authenticated method to check for
            no exception cases
            """
            return path[-1].name == 'authenticated_method'

        def __call__(self, request, handler):
            if self.user_is_authenticated(request.path):
                result = handler(request)
                return result
            raise SpecificException

    # Verify custom default middleware
    class DefaultMiddleware(MethodMiddleware):
        def __call__(self, request, handler):
            # We need to get past the DalMethodResolverMiddleware
            # which sets the `dal_method` attribute to
            # the method that has to be called
            request.dal_method = test_method
            result = handler(request)
            return result

    dm = DataManager()

    dal = DataAccessLayer(data_manager=dm, middleware=[AuthMiddleware],
                          default_middleware=(DefaultMiddleware,))

    with dm.context():
        assert dal.fake.authenticated_method()
        assert middleware_requests[0] == "test_method_called"
        with pytest.raises(SpecificException):
            dal.fake.service.method()


def test_dal_attribute_access_returns_dal_method_requester():
    """
    Verify that accessing an attribute on the DAL that does not
    exist returns an instance of DalMethodRequester.

    This is important because this starts building the call chain
    which is used to resolve methods later.
    """
    dm = DataManager()
    dal = DataAccessLayer(data_manager=dm)

    # Explicitly show that an attribute that is reset returns a
    # DMR instance
    dal.real = "real attribute"
    del dal.real
    with dm.context():
        assert isinstance(dal.real, DalMethodRequester)

    with dm.context():
        thing = dal.foo.bar.fake
        thing2 = dal.service.foo.test.example
        thing3 = dal.method
        assert isinstance(thing, DalMethodRequester)
        assert isinstance(thing2, DalMethodRequester)
        assert isinstance(thing3, DalMethodRequester)
        thing4 = getattr(dal, 'random')
        assert isinstance(thing4, DalMethodRequester)

    # also make sure to verify the error case where a context
    # has not been started yet.
    with pytest.raises(AssertionError):
        dal.foo.bar.fake


@pytest.mark.skip(reason="Not implemented yet, but needs to be.")
def test_dal_getitem_attribute_access():
    """
    Note: We need to account for this, but I'm not sure how it will work yet.
    Consider this test a placeholder for testing that method, which will need
    to change, but we haven't touched yet.
    """
    assert False


def test_default_dal_handler(path_arg):
    """
    Verify that the default dal handler performs validation on the request,
    and then calls the dal method that was resolved.
    """
    called_args = []

    def my_method(*args, **kwargs):
        called_args.append((args, kwargs))

    dm = DataManager()

    expected_args = ['foo']
    expected_kwargs = dict(test='bar')
    with dm.context() as ctx:
        request = DalMethodRequest(
            ctx,
            path_arg(),
            args=expected_args,


            kwargs=expected_kwargs
        )
        request.dal_method = my_method

    default_handle_dal_method(request)

    assert len(called_args) == 1
    assert expected_args, expected_kwargs == called_args[0]


@pytest.mark.xfail(reason="monkeypatching dal instance doesn't work")
def test_dal_middleware_monkeypatch(monkeypatch, sub_service_setup):
    """
    Verify that pytest monkeypatching still works with dal services and methods.
    """

    def mock_user_test_method():
        return 'mock value'

    dm = sub_service_setup()
    with dm.context() as ctx:
        monkeypatch.setattr(ctx.dal.users, 'user_test_method', mock_user_test_method)
        result = ctx.dal.users.user_test_method()
        assert result == 'mock value'