from functools import wraps
from flask_ckeditor import CKEditor, CKEditorField
from flask import Flask, render_template, request, flash, redirect, session, url_for, logging
from sqlalchemy.sql.operators import isnot
from wtforms import *
from passlib.hash import sha256_crypt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
db = SQLAlchemy(app)
ckeditor = CKEditor(app)

app.app_context().push()

class Register(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(30))
    username = db.Column(db.String(30))
    password = db.Column(db.String(32))
    register_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, name, email, username, password) -> None:
        self.name = name
        self.email = email
        self.username = username
        self.password = password


class Articles(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(100))
    body = db.Column(db.Text())
    create_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, title, author, body) -> None:
        self.title = title
        self.author = author
        self.body = body


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/articles")
def articles():
    articles = Articles.query.all()
    if articles is not None:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No articles Found'
        return render_template("articles.html", msg=msg)


@app.route("/article/<string:id>/")
def article(id):
    article = Articles.query.get(id)

    return render_template('article.html', article=article)


class Register_form(Form):
    name = StringField("Name", [validators.Length(min=1, max=50)])
    username = StringField("Username", [validators.Length(min=4, max=25)])
    email = StringField("Email", [validators.Length(min=6, max=30)])
    password = PasswordField("Password", [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords Do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = Register_form(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        passwd = sha256_crypt.hash(str(form.password.data))
        new_user = Register(name=name, email=email,
                            username=username, password=passwd)
        db.session.add(new_user)
        db.session.commit()
        flash("You are now registerd and can login", 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    app.logger.info("in the login")
    if request.method == 'POST':
        username = request.form['username']
        passwd_candidate = request.form['password']
        data = Register.query.filter_by(username=username).first()
        if data is not None:
            password = data.password

            if sha256_crypt.verify(passwd_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = "Invalid Login"
                return render_template("login.html", error=error)
        else:
            error = "Username Not found"
            return render_template("login.html", error=error)

    return render_template("login.html")


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if ('logged_in' in session):
            return f(*args, **kwargs)
        else:
            flash("Please login", 'danger')
            return redirect(url_for("login"))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', "success")
    return redirect(url_for('login'))


@app.route("/dashboard")
@is_logged_in
def dashboard():
    articles = Articles.query.filter_by(author=session['username'])
    if articles is not None:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No articles Found'
        return render_template("dashboard.html", msg)


class Article_Form(Form):
    title = StringField("Title", [validators.Length(min=1, max=200)])
    body = CKEditorField("Body", [validators.Length(min=30)])


@app.route("/add_article", methods=['GET', 'POST'])
@is_logged_in
def addArticle():
    form = Article_Form(request.form)
    if request.method == "POST":
        title = form.title.data
        body = form.body.data

        new_article = Articles(
            title=title, author=session['username'], body=body)
        db.session.add(new_article)
        db.session.commit()

        flash("Article Created", "success")

        return redirect(url_for('dashboard'))

    return render_template('add_article.html.j2', form=form)


@app.route("/edit_article/<string:id>", methods=['GET', 'POST'])
@is_logged_in
def editArticle(id):
    article = Articles.query.get(id)
    form = Article_Form(request.form)

    form.title.data = article.title
    form.body.data = article.body

    if request.method == "POST":
        title = request.form['title']
        body = request.form['body']

        article.title = title
        article.body = body
        db.session.commit()

        flash("Article Updated", "success")

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html.j2', form=form)


@app.route("/delete_article/<string:id>", methods=['POST'])
@is_logged_in
def delete_article(id):
    article = Articles.query.get(id)
    db.session.delete(article)
    db.session.commit()

    flash("Article Deleted", "danger")
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.secret_key = "this is a top level secret"
    app.run(debug=True)
