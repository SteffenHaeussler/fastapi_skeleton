from types import SimpleNamespace

from fastapi import FastAPI

from src.app.dependencies import get_resources


def test_get_resources_reads_from_app_state():
    request = type(
        "FakeReq",
        (),
        {
            "app": type(
                "FakeApp",
                (),
                {"state": SimpleNamespace(resources=SimpleNamespace(http="sentinel"))},
            )()
        },
    )()
    resources = get_resources(request)
    assert resources.http == "sentinel"


def test_get_resources_is_usable_as_fastapi_dependency():
    from fastapi import Depends
    from fastapi.testclient import TestClient

    from src.app.lifespan import lifespan

    app = FastAPI(lifespan=lifespan)

    @app.get("/probe")
    def probe(resources=Depends(get_resources)):
        return {"has_resources": resources is not None}

    with TestClient(app) as client:
        r = client.get("/probe")
    assert r.status_code == 200
    assert r.json() == {"has_resources": True}
