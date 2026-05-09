import importlib.metadata
from pathlib import Path
from typing import ClassVar, Tuple, Type

from pydantic import BaseModel, Field, constr, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class CORSConfig(BaseModel):
    enabled: bool = False
    allow_origins: list[str] = Field(default_factory=list)
    allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = False


class Deployment(BaseModel):
    CONFIG_NAME: constr(to_upper=True)
    DEBUG: bool
    cors: CORSConfig = Field(default_factory=CORSConfig)


class Config(BaseSettings):
    _toml_file: str = "config.toml"
    VALID_FASTAPI_ENVS: ClassVar[tuple[str, ...]] = ("DEV", "PROD", "STAGE", "TEST")

    FASTAPI_ENV: constr(to_upper=True) = Field(default="DEV")
    BASEDIR: str = str(Path(__file__).resolve().parent)
    ROOTDIR: str = str(Path(__file__).resolve().parents[2])
    VERSION: str = importlib.metadata.version("fastapi_skeleton")

    DEV: Deployment
    PROD: Deployment
    STAGE: Deployment
    TEST: Deployment

    model_config = SettingsConfigDict(toml_file=[_toml_file], env_prefix="")

    @field_validator("FASTAPI_ENV")
    @classmethod
    def validate_fastapi_env(cls, value: str) -> str:
        if value not in cls.VALID_FASTAPI_ENVS:
            expected = ", ".join(cls.VALID_FASTAPI_ENVS)
            raise ValueError(f"Invalid FASTAPI_ENV {value!r}. Expected one of: {expected}")
        return value

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
    def api_mode(self) -> Deployment:
        return getattr(self, self.FASTAPI_ENV)
