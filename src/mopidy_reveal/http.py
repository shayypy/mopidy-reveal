from __future__ import annotations

import hmac
import logging
import urllib.parse
from typing import TYPE_CHECKING, Any, cast

import tornado.escape
import tornado.web

if TYPE_CHECKING:
    from mopidy.config import Config
    from mopidy.core import CoreProxy

logger = logging.getLogger(__name__)

type RequestRule = (
    tuple[str, type[tornado.web.RequestHandler]]
    | tuple[str, type[tornado.web.RequestHandler], dict[str, Any]]
)

rpc_version = "2.0"

class RevealBaseHandler(tornado.web.RequestHandler):
    _token: str | None

    def initialize(self, *, token: str | None) -> None:
        self._token = token

    def write_json_error(self, id: int | None, status_code: int, message: str, error_code: int) -> None:
        self.set_status(status_code)
        self.set_header("Content-Type", "application/json")
        self.finish({
            "jsonrpc": rpc_version,
            "id": id,
            "error": {
                "code": error_code,
                "message": message,
            },
        })

    def check_auth(self) -> bool:
        if not self._token:
            return True

        header = self.request.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            self.write_json_error(401, "Missing or invalid Authorization header")
            return False

        supplied = header[len(prefix) :]
        if not hmac.compare_digest(supplied.encode(), self._token.encode()):
            self.write_json_error(401, "Invalid token")
            return False

        return True


RpcErrorCodes = {
    "ParseError": -32700,
    "InvalidRequest": -32600,
    "MethodNotFound": -32601,
    "InvalidParams": -32602,
    "InternalError": -32603,
}


class RpcHandler(RevealBaseHandler):
    _core: CoreProxy
    _config: Dict[str, Any]

    def initialize(  # type: ignore[override]
        self,
        *,
        core: CoreProxy,
        token: str | None,
        config: Dict[str, Any],
    ) -> None:
        super().initialize(token=token)
        self._core = core
        self._config = config

    def post(self) -> None:
        if not self.check_auth():
            return

        try:
            payload = tornado.escape.json_decode(self.request.body or b"{}")
        except ValueError:
            self.write_json_error(None, 400, "Request body must be valid JSON", RpcErrorCodes["ParseError"])
            return
        if not isinstance(payload, dict):
            self.write_json_error(None, 400, "Must provide dictionary-shaped body", RpcErrorCodes["InvalidRequest"])

        id = payload.get("id")
        if not isinstance(id, int):
            self.write_json_error(None, 400, "ID must be an integer", RpcErrorCodes["InvalidRequest"])

        method = payload.get("method")
        if not method or not isinstance(method, str):
            self.write_json_error(id, 400, "method must be supplied and a string", RpcErrorCodes["InvalidRequest"])
            return

        params = payload.get("params")
        if not isinstance(params, dict):
            self.write_json_error(None, 400, "params must be a dictionary", RpcErrorCodes["InvalidRequest"])

        if not method.startswith("reveal."):
            is_enabled = self._config.get(f"{method}.enabled")
            if is_enabled != True:
                self.write_json_error(id, 503, f"{method} is disabled by configuration", RpcErrorCodes["MethodNotFound"])
                return

        result = None
        match method:
            case "reveal.core.get_enabled_methods":
                result = reveal_core_get_enabled_methods(self)
            case "backend.playback.translate_uri":
                result = backend_playback_translate_uri(params, id, self)
            case _:
                self.write_json_error(id, 404, "Unknown method", RpcErrorCodes["MethodNotFound"])
                return

        if result == False:
            # error by handler, it should have written a json error
            return
        elif not result:
            self.write_json_error(id, 500, "No result could be resolved", RpcErrorCodes["InternalError"])
            return

        self.set_header("Content-Type", "application/json")
        self.finish({
            "id": id,
            "jsonrpc": rpc_version,
            "result": result,
        })


def backend_playback_translate_uri(params: dict, id: int, handler: RpcHandler):
    uri = params.get("uri")
    if not uri or not isinstance(uri, str):
        handler.write_json_error(id, 400, "Invalid or missing uri", RpcErrorCodes["InvalidParams"])
        return False

    scheme = urllib.parse.urlparse(uri).scheme
    backends = handler._core.backends.get()
    backend = backends.with_playback.get(scheme)

    if not backend:
        handler.write_json_error(id, 404, f"Unknown scheme (no backend found) for {uri}", -32010)
        return

    error = None
    try:
        translated_uri = backend.playback.translate_uri(uri).get() if backend else None
    except Exception as e:
        translated_uri = None
        error = str(e)

    if not translated_uri:
        handler.write_json_error(
            id,
            # i'm doubtful of false flags for this check
            # for a more rigorous check, i think i would need to try to import
            # (or at least name) error classes from each "supported" backend
            # to check against, which is annoying
            404 if error and "not found" in error else 500,
            error or "Failed to translate URI",
            -32011,
        )
        return False

    return { "uri": uri, "translated": translated_uri }


def reveal_core_get_enabled_methods(handler: RpcHandler) -> None:
    methods = [
        "backend.playback.translate_uri",
    ]
    return {
        method: handler._config.get(f"{method}.enabled") == True for method in methods
    }


def reveal_app_factory(config: Config, core: CoreProxy) -> list[RequestRule]:
    reveal_config = cast("dict[str, Any]", config["reveal"])
    token = reveal_config.get("token")
    if not token:
        logger.warning(
            "mopidy-reveal: no token configured; HTTP routes are unauthenticated",
        )

    return [
        (
            r"/rpc",
            RpcHandler,
            { "core": core, "token": token, "config": reveal_config },
        ),
    ]
