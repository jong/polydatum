import pytest
from polydatum import DataAccessLayer, DataManager, Service



def test_service_call():
    """
    Verify dal method calls
    """
    dm = DataManager()

    class ExampleService(Service):
        def get_user(self):
            return True

    dm.register_services(test=ExampleService())

    with dm.context() as ctx:
        assert ctx.dal.test.get_user()
