from __future__ import absolute_import
from __future__ import annotations
from contextlib import contextmanager
from polydatum.errors import AlreadyExistsException
from polydatum.util import is_generator
from .resources import ResourceManager
from .context import _ctx_stack
from typing import Callable, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from functools import partial, update_wrapper

from polydatum.context import DataAccessContext


class DalMethodRequest:
    """
    Mutable request state. Middleware can modify this.
    """

    def __init__(
            self, ctx: DataAccessContext, path: Tuple[PathSegment, ...], args: Tuple[Any, ...], kwargs: Dict
    ):
        self.ctx = ctx
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.dal_method = None  # Not resolved yet


class DalMethodError(Exception):
    def __init__(self, request: DalMethodRequest, path: Optional[Tuple[PathSegment]] = None):
        self._request = request
        self._path = path


@dataclass
class PathSegment:
    """
    This structure represents a segment of an attribute path.

    For example, in this code:

        dal.my_service.sub_service.other_service.method()

    For the `dal` object, the entire attribute path would be:

        my_service.sub_service.other_service.method

    Which may be made up of PathSegments like:

        PathSegment(name="my_service"), PathSegment(name="sub_service"), etc.
    """
    name: str

    # A collection of meta properties.
    # Example:
    #   meta = {
    #       "enabled": True
    #   }
    meta: dict

    def __init__(self, name: str, **meta):
        self.name = name
        self.meta = meta


class DalMethodRequester:
    """
    A utility class that defers access to DAL attributes.

    Attribute access to the DAL is deferred so that the DAL can
    run method middleware before and after calling a method.

    Method middlewares may prevent method's from being called
    by raising exceptions.
    """

    # Defining type here allows subclasses to easily provide another class
    PathSegment = PathSegment

    def __init__(self, handler: Callable, path: Tuple[PathSegment, ...]):
        """
        Args:
            handler (Callable): A callable that handles calling the underlying
                attribute by wrapping it so that method middleware can run before
                and after calling a method
                TODO: Consider using a custom type for the handler to represent
                      or document the interface to that callable.
            path (Tuple[PathSegment, ...]): A tuple of PathSegments representing
                the current attribute path that has been requested.
        """
        self._handler = handler
        self._path = path

    def __getattr__(self, name: str) -> DalMethodRequester:
        return self.__class__(self._handler, self._path + (self.PathSegment(name=name),))

    def __call__(self, *args, **kwargs):
        return self._handler(self._path, *args, **kwargs)


class DalMethodResolverMiddleware:
    """
    TODO: Review the implementation of this class.
    """
    def walk_path(self, request: DalMethodRequest):  ## noqa
        service_or_method = request.ctx.dal._services  # noqa
        paths = list(request.path[:])
        # paths = (PathSegment("foo"), PathSegment("bar"), PathSegment("baz"))
        # location = [PathSegment("foo"), PathSegment("bar")] on second yield
        location = []
        while paths:
            path_segment = paths.pop(0)
            location.append(path_segment)
            # Third time through, service_or_method might be `None`, but we want
            # to continue walking the path. Everything after the first missing
            # service/method will be `(location, None)`.
            if service_or_method:
                if isinstance(service_or_method, dict):
                    # first time through, service_or_method is a dict of services
                    service_or_method = service_or_method.get(path_segment.name)
                else:
                    # second time through, service_or_method is
                    service_or_method = getattr(service_or_method, path_segment.name)
                yield location, service_or_method
            else:
                yield location, None

    def resolve(self, request: DalMethodRequest):
        service_or_method = None
        for (path_segments, service_or_method) in self.walk_path(request):
            if not service_or_method:
                # If this is None, this means we've walked too far down
                # the path, and don't have any other attributes to resolve.
                raise DalMethodError(request, path=path_segments)
        return service_or_method

    def __call__(self, request: DalMethodRequest, handler: Callable):
        """
        Args:
             request: Input from caller
             handler: Downstream middleware or actual DAL method handler
                Note: This is provided
        """
        service_or_method = self.resolve(request)
        if service_or_method and callable(service_or_method):
            request.dal_method = service_or_method
            return handler(request)
        else:
            raise DalMethodError(request)


def default_handle_dal_method(request: DalMethodRequest):
    """
    The default method middleware handler for a DalMethodRequester

    Args:
        request (DalMethodRequest): The method request context.

    Returns: Mixed
    """
    assert request.dal_method, "DAL method not resolved"
    return request.dal_method(*request.args, **request.kwargs)


class DataAccessLayer(object):
    """
    Gives you access to a DataManager's services.
    """

    # default middleware classes need to be instantiated before being
    # passed to the init function because the resulting object is called
    # directly (__call__).
    def __init__(
        self,
        data_manager,
        middleware=None,
        default_middleware=(DalMethodResolverMiddleware(),),
        handler=default_handle_dal_method
    ):
        self._services = {}
        self._data_manager = data_manager
        self._handler = handler
        middleware = middleware or []
        if default_middleware:
            middleware.extend(default_middleware)

        # Reverse middleware so that self._handler is the first middleware to call
        # and at the end of the stack is `self._handle_dal_method`
        for m in reversed(middleware):
            self._handler = update_wrapper(
                partial(m, handler=self._handler), self._handler
            )

    def register_services(self, **services):
        """
        Register Services that can be accessed by this DAL. Upon
        registration, the service is set up.

        :param **services: Keyword arguments where the key is the name
          to register the Service as and the value is the Service.
        """
        for key, service in services.items():
            if key in self._services:
                raise AlreadyExistsException('A Service for {} is already registered.'.format(key))

            self._init_service(key, service)
        return self

    def replace_service(self, key, service):
        """
        Replace a Service with another. Usually this is a bad
        idea but is often done in testing to replace a Service
        with a mock version. It's also used for practical
        reasons if you need to swap out services for different
        framework implementations (ex: Greenlet version vs
        threaded)

        :param key: Name of service
        :param service: Service
        """
        return self._init_service(key, service)

    def _init_service(self, key, service):
        service.setup(self._data_manager)
        self._services[key] = service
        return service

    def _call(self, path: Tuple[PathSegment, ...], *args, **kwargs):
        return self._handler(
            request=DalMethodRequest(
                self._data_manager.get_active_context(), path, args, kwargs
            )
        )

    def __getattr__(self, name: str) -> DalMethodRequester:
        assert self._data_manager.get_active_context(), "A DataAccessContext must be started to access the DAL."
        return DalMethodRequester(self._call, path=(PathSegment(name=name),))

    def __getitem__(self, path):
        """
        Get a service method by dot notation path. Useful for
        serializing DAL methods as strings.

        If the first part of the path is "dal", it is ignored.

        Example::

            dal['myservice.get'](my_id)
        """
        paths = path.split('.')
        p = paths.pop(0)
        if p == 'dal':
            p = paths.pop(0)
        loc = self._services[p]
        while 1:
            try:
                p = paths.pop(0)
            except IndexError:
                break
            else:
                loc = getattr(loc, p)
        return loc


class DataManager(object):
    """
    Registry for Services, Resources, and other DAL objects.
    """
    DataAccessLayer = DataAccessLayer

    def __init__(self, resource_manager=None):
        if not resource_manager:
            resource_manager = ResourceManager(self)

        self._resource_manager = resource_manager
        self._dal = self.DataAccessLayer(self)
        self._middleware = []

        # TODO Make _ctx_stack only exist on the DataManager
        self.ctx_stack = _ctx_stack

    def register_context_middleware(self, *middleware):
        """
        :param middleware: Middleware in order of execution
        """
        for m in middleware:
            if not is_generator(m):
                raise Exception('Middleware {} must be a Python generator callable.'.format(m))

        self._middleware.extend(middleware)

    def get_middleware(self, context):
        """
        Returns all middleware in order of execution

        :param context: The DataAccessContext. You could override the DataManager
            and return different middleware based on the context here.
        """
        return self._middleware

    def register_resources(self, **resources):
        """
        Register Resources with the ResourceManager.
        """
        self._resource_manager.register_resources(**resources)

    def replace_resource(self, key, resource):
        """
        Replace a Resources on the ResourceManager.
        """
        self._resource_manager.replace_resource(key, resource)

    def register_services(self, **services):
        """
        Register Services with the DataAccessLayer
        """
        self._dal.register_services(**services)

    def replace_service(self, key, service):
        """
        Replace a Service on the DataAccessLayer
        """
        self._dal.replace_service(key, service)

    def get_resource(self, name):
        if name in self._resource_manager:
            return self._resource_manager[name]

    def get_dal(self):
        return self._dal

    def context(self, meta=None):
        return DataAccessContext(self, meta=meta)

    def get_active_context(self):
        """
        Safely checks if there's a context active
        and returns it
        """
        if self.ctx_stack.top:
            return self.ctx_stack.top

    @contextmanager
    def dal(self, meta=None):
        """
        Start a new DataAccessContext.

        :returns: DataAccessLayer for this DataManager
        """
        with self.context(meta=meta):
            yield self._dal