import pytest
from polydatum.dal import DalMethodError


def test_dal_resolver_middleware(sub_service_setup):
    """
    Verify the DalMethodResolverMiddleware
    accurately resolves through services and sub-services
    methods correctly.

    """
    dm = sub_service_setup()

    with dm.context() as ctx:
        demo = ctx.dal.users.profile.sample.example.demo.demo_test_method()
        assert demo == 'demo-nested-service'

        example = ctx.dal.users.profile.sample.example.example_test_method()
        assert example == 'example-nested-service'

        sample = ctx.dal.users.profile.sample.sample_test_method()
        assert sample == 'sample-nested-service'

        profile = ctx.dal.users.profile.profile_test_method()
        assert profile == 'profile-nested-service'

        users = ctx.dal.users.user_test_method()
        assert users == 'user-service'


def test_dal_resolver_middleware_invalid_method(sub_service_setup):
    """
    Verify that the DalMethodResolverMiddleware will raise an expected error
    when trying to call a method on a service that does not actually exist.
    """
    dm = sub_service_setup()

    with dm.context() as ctx:
        # Verify an invalid method on a real service raises exception
        with pytest.raises(DalMethodError):
            ctx.dal.users.profile.sample.example.demo.invalid_method()

        # Verify an invalid method on an invalid service raises exception
        with pytest.raises(DalMethodError):
            ctx.dal.users.invalid_service.invalid_method()
