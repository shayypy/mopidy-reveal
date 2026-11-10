from __future__ import annotations

import http
import json
from typing import TYPE_CHECKING, cast

import tornado.testing
import tornado.web

from mopidy_reveal.http import TranslateUriHandler, reveal_app_factory

if TYPE_CHECKING:
    import pytest
    from tornado.httpclient import HTTPResponse


class FakeFuture:
    def __init__(self, value: str | None) -> None:
        self._value = value

    def get(self) -> str | None:
        return self._value


class FakePlayback:
    def __init__(self, translated_uri: str | None) -> None:
        self._translated_uri = translated_uri

    def translate_uri(self, uri: str) -> FakeFuture:
        return FakeFuture(self._translated_uri)


class FakeBackend:
    def __init__(self, translated_uri: str | None) -> None:
        self.playback = FakePlayback(translated_uri)


class FakeBackends:
    def __init__(self, with_playback: dict[str, FakeBackend]) -> None:
        self.with_playback = with_playback


class FakeBackendsFuture:
    def __init__(self, with_playback: dict[str, FakeBackend]) -> None:
        self._backends = FakeBackends(with_playback)

    def get(self) -> FakeBackends:
        return self._backends


class FakeCore:
    def __init__(self, with_playback: dict[str, FakeBackend]) -> None:
        self.backends = FakeBackendsFuture(with_playback)


class TranslateUriHandlerTest(tornado.testing.AsyncHTTPTestCase):
    token: str | None = None
    enabled: bool = True
    with_playback: dict[str, FakeBackend] = {}  # noqa: RUF012

    def get_app(self) -> tornado.web.Application:
        core = FakeCore(self.with_playback)
        return tornado.web.Application(
            [
                (
                    r"/translate_uri",
                    TranslateUriHandler,
                    {
                        "core": core,
                        "token": self.token,
                        "enabled": self.enabled,
                    },
                ),
            ],
        )

    def post_json(
        self,
        body: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        return self.fetch(
            "/translate_uri",
            method="POST",
            body=json.dumps(body),
            headers=headers,
        )


class TestOpenAccess(TranslateUriHandlerTest):
    with_playback = {  # noqa: RUF012
        "local": FakeBackend("file:///music/track.mp3"),
        "declines": FakeBackend(None),
    }

    def test_known_scheme_returns_translated_uri(self) -> None:
        response = self.post_json({"uri": "local:track:abc"})
        assert response.code == http.HTTPStatus.OK
        assert json.loads(response.body) == {
            "uri": "local:track:abc",
            "translated_uri": "file:///music/track.mp3",
        }

    def test_backend_declining_returns_null(self) -> None:
        response = self.post_json({"uri": "declines:track:abc"})
        assert response.code == http.HTTPStatus.OK
        assert json.loads(response.body) == {
            "uri": "declines:track:abc",
            "translated_uri": None,
        }

    def test_unknown_scheme_returns_null(self) -> None:
        response = self.post_json({"uri": "nobackend:track:abc"})
        assert response.code == http.HTTPStatus.OK
        assert json.loads(response.body) == {
            "uri": "nobackend:track:abc",
            "translated_uri": None,
        }

    def test_missing_uri_field(self) -> None:
        response = self.post_json({})
        assert response.code == http.HTTPStatus.BAD_REQUEST

    def test_non_string_uri_field(self) -> None:
        response = self.post_json({"uri": 123})
        assert response.code == http.HTTPStatus.BAD_REQUEST

    def test_malformed_json_body(self) -> None:
        response = self.fetch("/translate_uri", method="POST", body="not json")
        assert response.code == http.HTTPStatus.BAD_REQUEST


class TestTokenRequired(TranslateUriHandlerTest):
    token = "secret-token"  # noqa: S105
    with_playback = {"local": FakeBackend("file:///music/track.mp3")}  # noqa: RUF012

    def test_missing_authorization_header(self) -> None:
        response = self.post_json({"uri": "local:track:abc"})
        assert response.code == http.HTTPStatus.UNAUTHORIZED

    def test_wrong_token(self) -> None:
        response = self.post_json(
            {"uri": "local:track:abc"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.code == http.HTTPStatus.UNAUTHORIZED

    def test_correct_token(self) -> None:
        response = self.post_json(
            {"uri": "local:track:abc"},
            headers={"Authorization": "Bearer secret-token"},
        )
        assert response.code == http.HTTPStatus.OK
        assert json.loads(response.body) == {
            "uri": "local:track:abc",
            "translated_uri": "file:///music/track.mp3",
        }

    def test_auth_checked_before_disabled_flag(self) -> None:
        self.enabled = False
        response = self.post_json({"uri": "local:track:abc"})
        assert response.code == http.HTTPStatus.UNAUTHORIZED


class TestDisabled(TranslateUriHandlerTest):
    enabled = False
    with_playback = {"local": FakeBackend("file:///music/track.mp3")}  # noqa: RUF012

    def test_disabled_returns_503(self) -> None:
        response = self.post_json({"uri": "local:track:abc"})
        assert response.code == http.HTTPStatus.SERVICE_UNAVAILABLE


def test_reveal_app_factory_shape() -> None:
    fake_config = {
        "reveal": {
            "token": "abc123",
            "backend.playback.translate_uri.enabled": True,
        },
    }
    core = FakeCore({})

    routes = reveal_app_factory(fake_config, core)  # type: ignore[arg-type]

    assert len(routes) == 1
    route = cast("tuple[str, type[TranslateUriHandler], dict[str, object]]", routes[0])
    path, handler, kwargs = route
    assert path == r"/translate_uri"
    assert handler is TranslateUriHandler
    assert kwargs["core"] is core
    assert kwargs["token"] == "abc123"  # noqa: S105
    assert kwargs["enabled"] is True


def test_reveal_app_factory_warns_on_blank_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_config = {
        "reveal": {
            "token": "",
            "backend.playback.translate_uri.enabled": True,
        },
    }
    core = FakeCore({})

    reveal_app_factory(fake_config, core)  # type: ignore[arg-type]

    assert any("unauthenticated" in message for message in caplog.messages)
