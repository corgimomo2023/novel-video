import json
import urllib.error
import urllib.request
from typing import Any


class RunPodError(RuntimeError):
    pass


class RunPodClient:
    def __init__(self, api_key: str, endpoint_id: str, *, opener=None, timeout: int = 30):
        if not api_key or not endpoint_id:
            raise ValueError("RunPod API key and endpoint ID are required")
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.opener = opener or urllib.request.build_opener()
        self.timeout = timeout

    def _request(self, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json", "User-Agent": "novel-video/0.1"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                content = response.read()
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as error:
            try:
                detail = error.read().decode("utf-8", "replace")[:500]
            except Exception:
                detail = ""
            raise RunPodError(f"RunPod API HTTP {error.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as error:
            raise RunPodError(f"RunPod API unavailable: {type(error).__name__}") from None

    def submit(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/run", method="POST", payload={"input": input_payload})

    def status(self, remote_job_id: str) -> dict[str, Any]:
        return self._request(f"/status/{remote_job_id}")

    def cancel(self, remote_job_id: str) -> dict[str, Any]:
        return self._request(f"/cancel/{remote_job_id}", method="POST")

    def health(self) -> dict[str, Any]:
        return self._request("/health")
