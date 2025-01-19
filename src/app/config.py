import importlib.metadata
from pathlib import Path
from typing import Tuple, Type

from pydantic import BaseModel, Field, constr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class Deployment(BaseModel):
    CONFIG_NAME: constr(to_upper=True)
    DEBUG: bool


class Config(BaseSettings):
    _toml_file: str = "config.toml"

    FASTAPI_ENV: constr(to_upper=True) = Field(default="DEV")
    BASEDIR: str = str(Path(__file__).resolve().parent)
    ROOTDIR: str = str(Path(__file__).resolve().parents[2])
    VERSION: str = importlib.metadata.version("fastapi_skeleton")

    DEV: Deployment
    PROD: Deployment
    STAGE: Deployment
    TEST: Deployment

    model_config = SettingsConfigDict(toml_file=[_toml_file], env_prefix="")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )

    @property
    def api_mode(self) -> str:
        return dict(self).get(self.FASTAPI_ENV)
