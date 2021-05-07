from polydatum import DataAccessLayer, DataManager, Service
from polydatum.middleware import DataAccessLayer as MiddlewareDataAccessLayer


def test_middleware_dal():
    """
    Verify middleware DataAccessLayer can be passed to DataManager
    """

    class Example(DataManager):
        """
        DataManager wrapper for test
        """
        DataAccessLayer = MiddlewareDataAccessLayer

        def __init__(self, resource_manager=None):
            super(Example, self).__init__(resource_manager)

    # Verify self._dal is set to the default DataAccessLayer class
    dm = DataManager()
    assert isinstance(dm._dal, DataAccessLayer)

    # Verify self._dal is set to the optional DataAccessLayer class i.e. TestDal class
    dm = Example()
    assert isinstance(dm._dal, MiddlewareDataAccessLayer)


def test_service_call():
    """
    Verify dal method calls
    """
    class Example(DataManager):
        """
        DataManager wrapper for test
        """
        DataAccessLayer = MiddlewareDataAccessLayer

        def __init__(self, resource_manager=None):
            super(Example, self).__init__(resource_manager)

    class ExampleService(Service):
        def get_user(self):
            return self._ctx.meta.user

    dm = Example()
    dm.register_services(test=ExampleService())

    with dm.context() as ctx:
        assert ctx.dal.test.get_user()
