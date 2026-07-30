"""Thin HTTP client for the ArqHub REST API (SPEC §9).

Reads the base URL and an optional PAT from the environment. Every call the MCP
server makes goes through here so auth and error handling live in one place.
"""

from __future__ import annotations

import os

import httpx

BASE_URL = os.environ.get("ARQHUB_API", "http://localhost:8000/api/v1")
PAT = os.environ.get("ARQHUB_PAT")


class ApiError(RuntimeError):
    pass


class ArqHubClient:
    def __init__(self, base_url: str = BASE_URL, token: str | None = PAT) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)

    def _request(self, method: str, path: str, **kw):
        resp = self._http.request(method, path, **kw)
        if resp.status_code >= 400:
            raise ApiError(f"{resp.status_code} {method} {path}: {resp.text}")
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    def get(self, path: str, params: dict | None = None):
        return self._request("GET", path, params=params or {})

    def post(self, path: str, json: dict | None = None, params: dict | None = None, content: str | None = None):
        return self._request("POST", path, json=json, params=params or {}, content=content)

    def patch(self, path: str, json: dict):
        return self._request("PATCH", path, json=json)
