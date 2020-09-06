from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIException(Exception):
    def __init__(self, name: str):
        self.name = name


# @v1.exception_handler(APIException)
def bad_request(request: Request, exc: APIException):
    # logger.error(error.to_dict())
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something. There goes a rainbow..."},
    )


def bad_request(error):
    # logger.error(response)
    return HTTPException(status_code=400, detail=error)


def internal_server_error(error):
    #     logger.error(response)
    return HTTPException(status_code=500, detail=error)


def forbidden(error):
    #     logger.error(response)
    return HTTPException(status_code=403, detail=error)
