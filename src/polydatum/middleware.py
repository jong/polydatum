from __future__ import annotations
from typing import Callable, Tuple, List, Dict, Optional
from dataclasses import dataclass
from functools import partial, update_wrapper

from polydatum.context import DataAccessContext


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


class DalMethodRequest:
    """
    Mutable request state. Middleware can modify this.
    """

    def __init__(
        self, ctx: DataAccessContext, path: Tuple[PathSegment, ...], args: List, kwargs: Dict
    ):
        self.ctx = ctx
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.dal_method = None  # Not resolved yet


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


# MethodMiddleware will call this `handler` callable during middleware.
def default_handle_dal_method(request: DalMethodRequest):
    """
    The default method middleware handler for a DalMethodRequester

    Args:
        request (DalMethodRequest): The method request context.

    Returns: Mixed
    """
    assert request.dal_method, "DAL method not resolved"
    return request.dal_method(*request.args, **request.kwargs)


class DataAccessLayer:
    def __init__(
        self,
        dm,
        middleware=None,
        default_middleware=(DalMethodResolverMiddleware,),
        handler=default_handle_dal_method,
    ):
        """
        Normally people don't want to think about `dal_method_resolver_middleware`
        because they want the default. Sometimes they want to change the order it
        happens or replace it. In that case:

        DataAccessLayer(middleware=[custom_resolver], default_middleware=None)
        DataAccessLayer(middleware=[
            pre_resolver,
            dal_method_resolver_middleware,
            post_resolve
        ], default_middleware=None)
        """
        self._data_manager = dm
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

    def _call(self, path: Tuple[PathSegment, ...], *args, **kwargs):
        return self._handler(
            request=DalMethodRequest(
                self._data_manager.get_active_context(), path, *args, **kwargs
            )
        )

    def __getattr__(self, name: str) -> DalMethodRequester:
        import pdb;pdb.set_trace()
        assert (
            self._data_manager.get_active_context()
        ), "A DataAccessContext must be started to access the DAL."
        return DalMethodRequester(self._call, path=(PathSegment(name=name),))
