import os
os.environ["STORAGE"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.repositories.factory as factory

@pytest.fixture()
def client():
    factory._MEM = None
    return TestClient(app)
