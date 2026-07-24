import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.providers.runpod import RunPodClient, RunPodError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self): return self.payload


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
    def open(self, request, timeout=0):
        self.requests.append((request, timeout))
        response = next(self.responses)
        if isinstance(response, Exception): raise response
        return response


def test_submit_uses_async_endpoint_and_bearer_header():
    opener = FakeOpener([FakeResponse({"id": "remote-123", "status": "IN_QUEUE"})])
    client = RunPodClient("rpa_test-secret", "endpoint-1", opener=opener)
    result = client.submit({"workflow": {"1": {"class_type": "Test"}}})
    request, timeout = opener.requests[0]
    assert request.full_url == "https://api.runpod.ai/v2/endpoint-1/run"
    assert request.method == "POST"
    assert request.headers["Authorization"] == "Bearer rpa_test-secret"
    assert json.loads(request.data) == {"input": {"workflow": {"1": {"class_type": "Test"}}}}
    assert timeout == 30
    assert result["id"] == "remote-123"


def test_status_and_cancel_use_expected_paths():
    opener = FakeOpener([FakeResponse({"id": "r1", "status": "COMPLETED", "output": {"images": []}}), FakeResponse({"id": "r1", "status": "CANCELLED"})])
    client = RunPodClient("rpa_test-secret", "endpoint-1", opener=opener)
    assert client.status("r1")["status"] == "COMPLETED"
    assert client.cancel("r1")["status"] == "CANCELLED"
    assert opener.requests[0][0].full_url.endswith("/status/r1")
    assert opener.requests[1][0].full_url.endswith("/cancel/r1")


def test_api_error_does_not_leak_key():
    error = HTTPError("https://api.runpod.ai/v2/e/run", 401, "Unauthorized", {}, BytesIO(b'{"error":"bad key"}'))
    client = RunPodClient("rpa_super-secret", "e", opener=FakeOpener([error]))
    with pytest.raises(RunPodError) as caught:
        client.submit({"workflow": {}})
    assert "401" in str(caught.value)
    assert "rpa_super-secret" not in str(caught.value)
