from flask import Flask

from web.scrape_runner import init_background_loop


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-key-pokecard"

    init_background_loop()

    from web.routes import bp

    app.register_blueprint(bp)

    return app
