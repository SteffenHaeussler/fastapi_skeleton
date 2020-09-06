import os
from os.path import abspath, dirname

from pydantic import BaseSettings


class BaseConfig:
    """Base configuration."""

    VERSION = "0.1.0"

    CONFIG_NAME = ""
    DEBUG = True
    ON_PREMISE = False

    BASEDIR = abspath(dirname(__file__))

    # credentials if needed
    # GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME")
    # GITLAB_PASSWORD = os.environ.get("GITLAB_PASSWORD")

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(BaseConfig):
    CONFIG_NAME = "prod"
    DEBUG = False

    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)


class DevelopmentConfig(BaseConfig):
    CONFIG_NAME = "develop"
    DEBUG = True

    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)


class StagingConfig(BaseConfig):
    CONFIG_NAME = "staging"
    DEBUG = False

    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)


class TestingConfig(BaseConfig):
    CONFIG_NAME = "testing"
    DEBUG = True

    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)


config = {
    "prod": ProductionConfig,
    "develop": DevelopmentConfig,
    "staging": StagingConfig,
    "testing": TestingConfig,
}
