from datetime import datetime
from uuid import uuid4

from .models import db, TimestampMixin


class Config(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
    histories = db.relationship('ConfigHistory', backref='config', lazy=True)

    @staticmethod
    def set(key, value):
        config = db.session.execute(db.select(Config).where(Config.key == key)).first()
        if not config:
            config = Config(key=key, value=value)
            db.session.add(config)
        else:
            history = ConfigHistory(value=config.value, config_id=config.id)
            db.session.add(history)
            config.value = value
        db.session.commit()

    @staticmethod
    def get(key):
        config = db.session.execute(db.select(Config).where(Config.key == key)).first()
        return config.value if config else None

    @classmethod
    def get_current_as_dict(cls):
        data = {}
        configs = db.session.execute(db.select(Config)).scalars()
        for config in configs:
            data[config.key] = config.value
        return data

class ConfigHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    value = db.Column(db.String, nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey('config.id'), nullable=False)
