from flask import Flask
from config import Config
from models import db
from routes import routes

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(routes)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
