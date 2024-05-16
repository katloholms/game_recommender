from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    platform = db.Column(db.String(50), nullable=True)
    genres = db.Column(db.String(250), nullable=True)
    liked_games = db.relationship('LikedGame', backref='user', lazy=True)

    def __init__(self, username, password, platform=None, genres=None):
        self.username = username
        self.password = password
        self.platform = platform
        self.genres = genres

class LikedGame(db.Model):
    __tablename__ = 'liked_games'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(150), nullable=False)
    game_name = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, game_id, game_name, user_id, rating=None):
        self.game_id = game_id
        self.game_name = game_name
        self.user_id = user_id
        self.rating = rating
