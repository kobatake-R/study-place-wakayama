from flask import Flask, render_template, request, redirect, url_for, abort
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from urllib.parse import quote
from sqlalchemy import or_
from sqlalchemy.orm import relationship
from flask_login import UserMixin,LoginManager, current_user, login_user, logout_user,login_required
from werkzeug.security import generate_password_hash, check_password_hash
import os

#SQLとSECRETの追加
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = os.urandom(24)
Login_Manager = LoginManager()
Login_Manager.init_app(app)



#コメント機能SQL
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



#投稿用SQL
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.String(200))
    due = db.Column(db.DateTime, nullable=False)
    place = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(30), nullable=False)
    money = db.Column(db.String(30), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 外部キー：ユーザー情報
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

    #グーグルマップ用URL
    @property
    def place_map_link(self):
        return f"https://www.google.com/maps/place/{quote(self.title)}"



#ユーザー情報SQL
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(12))
    posts = db.relationship('Post', backref='user', lazy=True)



#問い合わせ用SQL
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(100), nullable=False)

    def __init__(self, email, **kwargs):
        if not self.is_alphanumeric(email):
            raise ValueError("Email must contain only alphanumeric characters")
        self.email = email
        super(Contact, self).__init__(**kwargs)


    
#ログイン機能の関数
@Login_Manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
#最新の投稿表示用
def is_recent(due_date, today):
    return 0 <= (today - due_date.date()).days <= 7


def is_acount(username, post_id):
    post = Post.query.get(post_id)
    return post.user.username == username

def is_acount(username, post_id):
    post = Post.query.get(post_id)
    return post.user.username == username if post else False



#トップページ部分
@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':
        #posts = Post.query.all()
        posts = Post.query.order_by(Post.due).all()
        return render_template('index.html', posts=posts, today=date.today(), is_recent=is_recent)
    
    elif request.method == 'POST':
        title_search_term = request.form.get('search')
        
        # 検索条件が指定されている場合のみフィルタリング
        if title_search_term:
            posts = Post.query.filter(or_(Post.title.ilike(f'%{title_search_term}%'), Post.place.ilike(f'%{title_search_term}%'))).order_by(Post.due).all()
            return render_template('index.html', posts=posts, today=date.today(), search_term=title_search_term, is_recent=is_recent)

        # 検索条件が未指定の場合は全ての投稿を表示
        else:
            posts = Post.query.order_by(Post.due).all()
            return render_template('index.html', posts=posts, today=date.today(), is_recent=is_recent)
            #return redirect('/')


        return render_template('index.html', posts=posts, today=date.today(), search_term=title_search_term, is_recent=is_recent)
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':
        # POST メソッドでの処理
        username = request.form.get('username')
        password = request.form.get('password')
        # データを取得

        existing_user = User.query.filter_by(username=username).first()

        # ユーザー名が既に存在する場合はエラーメッセージを表示
        if existing_user:
            abort(403, "このメールアドレスは使用済みです。")
            return redirect('/signup')

        
        #ユーザー情報を登録
        user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    # GET メソッドでの処理
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        # POST メソッドでの処理

        username = request.form.get('username')
        password = request.form.get('password')
        #データを取得

        # パスワードとメールアドレスが正しいか確認
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/')
    # GET メソッドでの処理
    return render_template('login.html')

#ログアウト機能
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


#投稿を追加
@app.route('/create', methods=['GET', 'POST'])
#@login_required
def create():

    if request.method == 'POST':
        # POST メソッドでの処理
        title = request.form.get('title')
        place = request.form.get('place')
        time = request.form.get('time')
        money = request.form.get('money')
        detail = request.form.get('detail')
        due = datetime.strptime(request.form.get('due'), '%Y-%m-%d')

        # 新しい投稿を作成してデータベースに追加
        new_post = Post(title=title, place=place, time=time, money=money, detail=detail, due=due, user=current_user)
        db.session.add(new_post)
        db.session.commit()

        # 投稿後のリダイレクト
        return redirect('/')
    # GET メソッドでの処理
    return render_template('create.html')


#問い合わせフォーム
@app.route('/contact', methods=['POST'])
def contact():
    if request.method == 'POST':
        # フォームから送信されたデータを取得
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        new_contact = Contact(name=name, email=email, message=message)
        db.session.add(new_contact)
        db.session.commit()

    # 必要に応じてリダイレクトなどの処理を行う
    return redirect('/')


#投稿の詳細ページへ
@app.route('/detail/<int:id>',methods=['GET', 'POST'])
def read(id):
    post = Post.query.get(id)
    #POSTで詳細の表示
    if request.method == 'POST':
        comment_text = request.form.get('comment_text')
        new_comment = Comment(text=comment_text, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()

    comments = Comment.query.filter_by(post_id=id).order_by(Comment.created_at.desc()).all()

    return render_template('detail.html', post=post, comments=comments)


#投稿の内容を編集
@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    post = Post.query.get(id)
    #エラーメッセージ
    if post.user != current_user:
        abort(403, "投稿したアカウントでしか編集は行えません...ごめんね。")  # Forbidden
        
    if request.method == 'GET':
        return render_template('update.html', post=post)
    else:
        post.title = request.form.get('title')
        post.detail = request.form.get('detail')
        post.due = datetime.strptime(request.form.get('due'), '%Y-%m-%d')
        post.place = request.form.get('place')
        post.time = request.form.get('time')
        post.money = request.form.get('money')

        db.session.commit()
        return redirect('/')
  
    
#投稿を削除
@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get(id)

    if post.user != current_user:
        abort(403, "投稿したアカウントでしか削除は行えません...ごめんね。")  # Forbidden

    db.session.delete(post)
    db.session.commit()
    return redirect('/')

    return render_template('detail.html', post=post)

if __name__ == '__main__':
    app.run()