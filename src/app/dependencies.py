from fastapi import Request


def get_resources(request: Request):
    """Return the shared-resources namespace attached by lifespan.

    Add per-resource factories below this function. Each one should:
      1. read from `request.app.state.resources.<name>`
      2. export an `Annotated[Type, Depends(get_<name>)]` alias
    Tests can override factories with `app.dependency_overrides`.

    Template for a real client:

        # def get_http_client(request: Request) -> httpx.AsyncClient:
        #     return request.app.state.resources.http
        # HTTPClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
    """
    return request.app.state.resources
