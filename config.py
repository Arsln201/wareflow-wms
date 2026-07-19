class Config:
    SECRET_KEY = "wareflow-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///wareflow.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    