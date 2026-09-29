"""Bound multipart bodies before the parser can spool arbitrary data to disk."""

import uuid

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, limit=21 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "body_too_large",
                            "message": "Request body exceeds 21 MiB including multipart headers",
                            "trace_id": str(uuid.uuid4()),
                            "details": [],
                        }
                    },
                    status_code=413,
                )
                return await response(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0

        async def replay():
            nonlocal index
            if index < len(chunks):
                item = chunks[index]
                index += 1
                return item
            return await receive()

        return await self.app(scope, replay, send)
