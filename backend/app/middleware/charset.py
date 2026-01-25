from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CharsetJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        content_type = response.headers.get("content-type")
        if content_type and content_type.startswith("application/json"):
            if "charset=" not in content_type:
                response.headers["content-type"] = f"{content_type}; charset=utf-8"
        elif response.media_type == "application/json":
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response
