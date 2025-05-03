from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship("User", back_populates="blogs")
    cmnts = relationship("Comment", back_populates="blag")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    cmntr_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    cmntr = relationship("User", back_populates="commenta")
    blag_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    blag = relationship("BlogPost", back_populates="cmnts")
    text = db.Column(db.Text, nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    blogs = relationship("BlogPost", back_populates="author")
    commenta = relationship("Comment", back_populates="cmntr")


# with app.app_context():
#     db.create_all()
#     db.session.commit()


login_manager = LoginManager(app)
usid = 0


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


def admin_only(fn1):
    global usid
    @wraps(fn1)
    def inner(*args, **kwargs):
        if usid==1:
            return fn1(*args, **kwargs)
        else:
            #return "<h2>Error 403: You are not authorize</h2>"
            return abort(403)
    return inner


@app.route('/')
def get_all_posts():
    global usid
    usid = current_user.get_id()
    if usid==None:
        usid = 0
    else:
        usid = int(usid)
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, uid = usid)


@app.route('/register', methods=["POST", "GET"])
def register():
    form1 = RegisterForm()
    if form1.validate_on_submit():
        eml = form1.email.data
        if User.query.filter_by(email=eml).first() != None:
            flash("You've already signed up with that email, login instead!")
            return redirect(url_for("login"))
        usr = User(
            #email = request.form.get("email"),
            email=eml,
            password = generate_password_hash(form1.password.data),
            name = form1.name.data
        )
        db.session.add(usr)
        db.session.commit()
        login_user(usr)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form1)


@app.route('/login', methods=["POST", "GET"])
def login():
    form1 = LoginForm()
    if form1.validate_on_submit():
        usr = User.query.filter_by(email=form1.email.data).first()
        if usr == None:
            flash("That email does not exist, please try again")
        elif check_password_hash(usr.password, form1.password.data):
            login_user(usr)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Password is incorrect, please try again")
    return render_template("login.html", form=form1)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form1 = CommentForm()
    if form1.validate_on_submit():
        if current_user != None and current_user.is_authenticated:
            nwcmnt = Comment(
                cmntr_id = current_user.id,
                blag_id = post_id,
                text = form1.body.data
            )
            db.session.add(nwcmnt)
            db.session.commit()
        else:
            flash("You need to login to submit your comment")
            return redirect(url_for("login"))
    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, uid=usid, form=form1)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            author_id = current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        db.session.commit()
        post.subtitle = edit_form.subtitle.data
        db.session.commit()
        post.img_url = edit_form.img_url.data
        db.session.commit()
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)




