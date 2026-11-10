import logging
import pathlib
from importlib.metadata import version

from mopidy import config, ext

__version__ = version("mopidy-reveal")

# TODO: If you need to log, use loggers named after the current Python module
logger = logging.getLogger(__name__)


class Extension(ext.Extension):
    dist_name = "mopidy-reveal"
    ext_name = "reveal"
    version = __version__

    def get_default_config(self) -> str:
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self) -> config.ConfigSchema:
        schema = super().get_config_schema()

        schema["token"] = config.Secret(optional=True)
        schema["backend.playback.translate_uri.enabled"] = config.Boolean()
        return schema

    def setup(self, registry: ext.Registry) -> None:
        from .http import reveal_app_factory  # noqa: PLC0415

        registry.add(
            "http:app",
            {
                "name": self.ext_name,
                "factory": reveal_app_factory,
            },
        )
