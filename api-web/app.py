from flask import Flask
from routes.onu import onu_bp   # import blueprint

app = Flask(__name__)
app.register_blueprint(onu_bp, url_prefix="/onu")  # aktifkan route /onu

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
