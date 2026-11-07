"""Pure path selection for the supported checkout and API-container layouts."""

import pathlib


def application_root(config_file: pathlib.PurePath) -> pathlib.PurePath:
    api_root = config_file.parents[2]
    if api_root.name == "api" and api_root.parent.name == "apps":
        return api_root.parent.parent
    return api_root
