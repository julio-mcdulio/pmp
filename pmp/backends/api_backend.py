 """HTTP API backend."""

 from __future__ import annotations

 import json
 import urllib.error
 import urllib.parse
 import urllib.request
 from typing import Dict, List, Optional

from ..errors import BackendError, PromptAlreadyExists, PromptNotFound
 from .base import PromptBackend


 class APIBackend(PromptBackend):
     """Delegates prompt storage to a remote HTTP API."""

     def __init__(self, url: Optional[str] = None, token: Optional[str] = None, timeout: float = 10.0):
         if not url:
             raise ValueError("api backend requires a url")
         self.base_url = url.rstrip("/")
         self.token = token
         self.timeout = float(timeout)

     def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         self._request(
             "POST",
             "/prompts",
             body={"name": name, "content": content, "metadata": metadata},
         )

     def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
         params = {}
         if version is not None:
             params["version"] = str(version)
         return self._request("GET", f"/prompts/{name}", params=params)

     def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         self._request(
             "PUT",
             f"/prompts/{name}",
             body={"content": content, "metadata": metadata},
         )

     def delete(self, name: str, version: Optional[int] = None) -> None:
         params = {}
         if version is not None:
             params["version"] = str(version)
         self._request("DELETE", f"/prompts/{name}", params=params)

     def list(self, filters: Optional[Dict[str, object]] = None) -> List[Dict[str, object]]:
         params = {}
         filters = filters or {}
         if filters.get("tag"):
             params["tag"] = filters["tag"]
         if filters.get("model"):
             params["model"] = filters["model"]
         return self._request("GET", "/prompts", params=params)

     # ---------------------------------------------------------------- helpers
     def _request(self, method: str, path: str, body: Optional[Dict[str, object]] = None, params: Optional[Dict[str, str]] = None):
         url = self.base_url + path
         if params:
             query = urllib.parse.urlencode(params)
             url = f"{url}?{query}"
         data = None
         headers = {"Accept": "application/json"}
         if body is not None:
             data = json.dumps(body).encode("utf-8")
             headers["Content-Type"] = "application/json"
         request = urllib.request.Request(url, data=data, method=method, headers=headers)
         if self.token:
             request.add_header("Authorization", f"Bearer {self.token}")
         try:
             with urllib.request.urlopen(request, timeout=self.timeout) as response:
                 payload = response.read().decode("utf-8")
                 if not payload:
                     return {}
                 return json.loads(payload)
         except urllib.error.HTTPError as exc:
             if exc.code == 404:
                 raise PromptNotFound("request failed: not found") from exc
             if exc.code == 409:
                 raise PromptAlreadyExists("request failed: duplicate prompt") from exc
             if exc.code == 400:
                 raise BackendError(exc.read().decode("utf-8") or "api rejected request") from exc
             raise BackendError(f"api error ({exc.code}): {exc.reason}") from exc
         except urllib.error.URLError as exc:
             raise BackendError(f"unable to reach api: {exc.reason}") from exc

