from mopidy_reveal import Extension


def test_get_default_config() -> None:
    ext = Extension()

    config = ext.get_default_config()

    assert "[reveal]" in config
    assert "enabled = true" in config


def test_get_config_schema() -> None:
    ext = Extension()

    schema = ext.get_config_schema()

    assert "token" in schema
    assert "backend.playback.translate_uri.enabled" in schema


def test_default_config_passes_schema_validation() -> None:
    """The shipped `token =` default must deserialize without raising.

    `token` must stay `optional=True` since `ext.conf` ships it blank.
    """
    ext = Extension()

    schema = ext.get_config_schema()
    default_config = ext.get_default_config()

    raw_values = {}
    for raw_line in default_config.splitlines():
        stripped_line = raw_line.strip()
        if (
            not stripped_line
            or stripped_line.startswith("[")
            or "=" not in stripped_line
        ):
            continue
        key, _, value = stripped_line.partition("=")
        raw_values[key.strip()] = value.strip()

    _, errors = schema.deserialize(raw_values)
    assert errors == {}
