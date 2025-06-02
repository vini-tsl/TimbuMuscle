from flask import Flask

app = Flask(__name__)

app.secret_key = "3321iojkxc35320900wio1p2klosda1lpskal013io2jod0i2i13mdslakcx0oij1mcmvkiuhr311p2aslamqoqpald"

from route import *

if __name__ == "__main__":
    app.run(debug=True)