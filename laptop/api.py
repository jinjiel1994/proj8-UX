# Laptop Service

import flask
import os
import pymongo

from flask import Flask, abort, request, jsonify, g, render_template, session
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_restful import Resource, Api
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Length

# Instantiate the app
from passlib.apps import custom_app_context as pwd_context
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from pymongo import MongoClient
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

# initialization
from werkzeug.utils import redirect

app = Flask(__name__)
api = Api(app)
csrf = CSRFProtect(app)
csrf.init_app(app)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

# extensions
db = SQLAlchemy(app)
auth = HTTPBasicAuth()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

client = MongoClient('db', 27017)
db_time = client.time


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired('A username is required!'), Length(min=3, max=10,
                                                                                                    message='Must be between 3 and 10 characters.')])
    password = PasswordField('password', validators=[InputRequired('Password is required!')])
    remember = BooleanField('Remember me')


class RegisterForm(FlaskForm):
    username = StringField('username', validators=[InputRequired('A username is required!'), Length(min=3, max=10,
                                                                                                    message='Must be between 3 and 10 characters.')])
    password = PasswordField('password', validators=[InputRequired('Password is required!')])


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.

    if current_user.is_authenticated:
        return render_template('logined.html')

    form = LoginForm()
    session['next'] = request.args.get('next')
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        # login_user(user)
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if user.verify_password(form.password.data):
                flask.flash('Logged in successfully.')

                login_user(user, remember= form.remember.data)
                return render_template('logined.html')
            else:
                return ' <h1> Wrong user/password! </h1>'

        return '<h1> No such user </h1>'

    return flask.render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')


@app.route('/api/resource')
@login_required
def get_resource():
    return render_template('index.php')


class listAll(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]

        return {'km': [item['km'] for item in items],
                'open': [item["open"] for item in items],
                'close': [item["close"] for item in items]
                }


class listOpenOnly(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]

        return {'open': [item["open"] for item in items]
                }


class listCloseOnly(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]

        return {'close': [item["close"] for item in items]
                }


class listAllcsv(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]
        csv = 'open, close\n'
        for item in items:
            csv += '%s, %s\n' % (item['open'], item['close'])
        csv = csv.strip('\n')
        csv = csv.split('\n')
        return csv


class listOpenOnlycsv(Resource):
    def get(self):

        top = flask.request.args.get("top", type=int)
        if top is None:
            _items = db_time.time.find()
        else:
            _items = db_time.time.find().sort("open", pymongo.ASCENDING).limit(top)

        items = [item for item in _items]
        csv = 'open\n'
        for item in items:
            csv += '%s\n' % item['open']
        csv = csv.strip('\n')
        csv = csv.split('\n')
        return csv


class listCloseOnlycsv(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]
        csv = 'close\n'
        for item in items:
            csv += '%s\n' % item['close']
        csv = csv.strip('\n')
        csv = csv.split('\n')
        return csv


class listAlljson(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]
        json = []
        for item in items:
            json.append({'km': item['km'],
                         'open': item['open'],
                         'close': item['close']
                         })
        return json


class listOpenOnlyjson(Resource):
    def get(self):
        top = flask.request.args.get("top", type=int)
        if top is None:
            _items = db_time.time.find()
        else:
            _items = db_time.time.find().sort("open", pymongo.ASCENDING).limit(top)

        items = [item for item in _items]
        json = []
        for item in items:
            json.append({'km': item['km'],
                         'open': item['open']
                         })
        return json


class listCloseOnlyjson(Resource):
    def get(self):
        _items = db_time.time.find()
        items = [item for item in _items]
        json = []
        for item in items:
            json.append({'km': item['km'],
                         'close': item['close']
                         })
        return json


# Create routes
# Another way, without decorators
api.add_resource(listAll, '/listAll')
api.add_resource(listOpenOnly, '/listOpenOnly')
api.add_resource(listCloseOnly, '/listCloseOnly')
api.add_resource(listAllcsv, '/listAll/csv')
api.add_resource(listOpenOnlycsv, '/listOpenOnly/csv')
api.add_resource(listCloseOnlycsv, '/listCloseOnly/csv')
api.add_resource(listAlljson, '/listAll/json')
api.add_resource(listOpenOnlyjson, '/listOpenOnly/json')
api.add_resource(listCloseOnlyjson, '/listCloseOnly/json')


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(64))

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=600):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/')
def index():
    return redirect('/login')


@app.route('/register_page')
def register_page():
    form = RegisterForm()
    return render_template('register.html' , form=form)


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm()
    if form.validate_on_submit():
        # register and validate the user.
        # user should be an instance of your `User` class
        # login_user(user)
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            return '<h1> User exists! </h1>'
        else:
            user = User(username=form.username.data)
            user.hash_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            return render_template('suc_reg.html')
    return flask.render_template('register.html', form=form)


@app.route('/api/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['pass']
    if username is '' or password is '':
        abort(400)  # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)  # existing user
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return render_template('suc_reg.html')


@app.route('/api/token')
@login_required
def get_auth_token():
    token = g.user.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


# Run the application
if __name__ == '__main__':
    if not os.path.exists('db.sqlite'):
        db.create_all()
    app.run(host='0.0.0.0', port=80, debug=True)
