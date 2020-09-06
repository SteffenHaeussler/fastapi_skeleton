from fastapi import HTTPException


def bad_request(error):
    # logger.error(response)
    return HTTPException(status_code=400, detail=error)


def internal_server_error(error):
    #     logger.error(response)
    return HTTPException(status_code=500, detail=error)


def forbidden(error):
    #     logger.error(response)
    return HTTPException(status_code=403, detail=error)
