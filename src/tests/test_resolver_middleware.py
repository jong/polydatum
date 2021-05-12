


def test_dal_resolver_middleware():
    """
    Verify that when using DalMethodResovlerMiddleware, that the middleware
    will accurately resolve the PathSegments that were build up in a
    DalMethodREquest to the correct service and method.
    """
    pass


def test_dal_resolver_middleware_invalid_method():
    """
    Verify that the DalMethodResolverMiddleware will raise an expected error
    when trying to call a method on a service that does not actually exist.
    """
    pass


def test_dal_resolver_middleware_service_recursion():
    """
    Verify one of the implementation details of the DalMethodResolverMiddleware
    accurately recurses through services and sub-services correctly.

    This functionality is tested implicitly in other tests, but it is worth
    verifying the details of how this is implemented.
    """
    pass