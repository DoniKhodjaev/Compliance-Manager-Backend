import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/swift_messages.db')
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

# Default config
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 