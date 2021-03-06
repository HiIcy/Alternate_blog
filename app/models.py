# _*_coding:utf-8 _*_
import hashlib
from datetime import datetime
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
from app import db
# 用户密码验证 hash
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from markdown import markdown
import bleach
from app.exceptions import ValidationError
from PIL import Image


# 用户的权限常量
class Permission:
	FOLLOW = 0x01
	COMMENT = 0x02
	WRITE_ARTICLES = 0x04
	MODERATE_COMMENTS = 0x08
	ADMINISTER = 0x80


# 高级多对多关系中
# 提升关联表 关注关联表的实现
class Follow(db.Model):
	__tablename__ = 'follows'
	follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
	followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# 用户角色
class Role(db.Model):
	__tablename__ = 'roles'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	default = db.Column(db.Boolean, default=False, index=True)
	# 值 表示位标志
	permissions = db.Column(db.Integer)
	# 关系的链接 backref-反向查询:user.role
	users = db.relationship('User', backref='role', lazy='dynamic')

	# 类方法
	@staticmethod
	def insert_roles():
		roles = {
			'User': (Permission.FOLLOW |
			         Permission.COMMENT |
			         Permission.WRITE_ARTICLES, True),
			'Moderator': (Permission.FOLLOW |
			              Permission.COMMENT |
			              Permission.WRITE_ARTICLES |
			              Permission.MODERATE_COMMENTS, False),
			'Administrator': (0xff, False)
		}
		for r in roles:
			role = Role.query.filter_by(name=r).first()
			if role is None:
				role = Role(name=r)
			role.permissions = roles[r][0]
			role.default = roles[r][1]
			db.session.add(role)
		db.session.commit()

	def __repr__(self):
		return '<Role %r>' % self.name


class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64))
	location = db.Column(db.String(64))
	# 头像也用String 这点django好
	avatar = db.Column(db.String(64), default=None)
	about_me = db.Column(db.Text())
	# 字段接收函数对象，到时自动触发函数，所以无括号
	member_since = db.Column(db.DateTime(), default=datetime.utcnow)
	last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
	email = db.Column(db.String(64), unique=True, index=True)
	username = db.Column(db.String(64), unique=True, index=True)
	# 密码散列
	password_hash = db.Column(db.String(128))
	confirmed = db.Column(db.Boolean, default=False)
	avatar_hash = db.Column(db.String(32))
	role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
	# 正向查询 posts
	posts = db.relationship('Post', backref='author', lazy='dynamic')
	# 防止外键冲突； 回引模型，立即加载；；删除记录后正确的行为应该是把指向该记录的实体也删除，因为这样能有效销毁联接
	followed = db.relationship('Follow', foreign_keys=[Follow.follower_id],
	                           backref=db.backref('follower', lazy='joined'),
	                           lazy='dynamic',
	                           cascade='all, delete-orphan')
	followers = db.relationship('Follow', foreign_keys=[Follow.followed_id],
	                            backref=db.backref('followed', lazy='joined'),
	                            lazy='dynamic',
	                            cascade='all, delete-orphan')
	comments = db.relationship('Comment', backref='author', lazy='dynamic')

	# 赋予角色
	def __init__(self, **kwargs):
		super(User, self).__init__(**kwargs)
		if self.role is None:
			if self.email == current_app.config['FLASKY_ADMIN']:
				# 利用整数来置定权限
				self.role = Role.query.filter_by(permissions=0xff).first()
			if self.role is None:
				self.role = Role.query.filter_by(default=True).first()
		if self.email is not None and self.avatar_hash is None:
			# 邮箱的md5散列值，暂存，以做头像需要
			self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
		self.follow(self)

	# 写api时用，
	def to_json(self):
		json_user = {
			'url': url_for('api.get_post', id=self.id, _external=True),
			'username': self.username,
			'member_since': self.member_since,
			'last_seen': self.last_seen,
			'posts': url_for('api.get_user_posts', id=self.id, _external=True),
			'followed_posts': url_for('api.get_user_followed_posts',
			                          id=self.id, _external=True),
			'post_count': self.posts.count()
		}
		return json_user

	# property装饰器，拥有get,set力量，转化函数为属性，
	@property
	def followed_posts(self):
		return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
				.filter(Follow.follower_id == self.id)

	def follow(self, user):
		if not self.is_following(user):
			f = Follow(follower=self, followed=user)
			db.session.add(f)

	def unfollow(self, user):
		f = self.followed.filter_by(followed_id=user.id).first()
		if f:
			db.session.delete(f)

	def is_following(self, user):
		return self.followed.filter_by(followed_id=user.id).first() is not None

	def is_followed_by(self, user):
		return self.followers.filter_by(follower_id=user.id).first() is not None

	# 角色验证 检查用户是否有指定的权限
	def can(self, permissions):
		# return 高级使用之一，
		# 位与操作
		return self.role is not None and \
		       (self.role.permissions & permissions) == permissions

	def is_administrator(self):
		return self.can(Permission.ADMINISTER)

	def generate_confirmation_token(self, expiration=3600):
		# 生成一个JSON Web 签名对象
		s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
		# 对指定数据 加密签名
		return s.dumps({'confirm': self.id})

	# 单元测试 later
	def confirm(self, token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return False
		if data.get('confirm') != self.id:
			return False
		self.confirmed = True
		db.session.add(self)
		return True

	# 邮箱重置密令
	def generate_reset_token(self, expiration=3600):
		s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
		return s.dumps({'reset': self.id})

	def reset_password(self, token, new_password):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return False
		if data.get('reset') != self.id:
			return False
		# 调用属性函数去赋值，直接传密码即可
		self.password = new_password
		db.session.add(self)
		return True

	def generate_email_change_token(self, new_email, expiration=3600):
		s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
		# 把id和新邮件都作为token来传递
		return s.dumps({'change_email': self.id, 'new_email': new_email})

	def change_email(self, token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return False
		if data.get('change_email') != self.id:
			return False
		new_email = data.get('new_email')
		if new_email is None:
			return False
		if self.query.filter_by(email=new_email).first() is not None:
			return False
		self.email = new_email
		# 对需要修改的新邮箱的md5散列值，暂存，以做头像需要
		self.avatar_hash = hashlib.md5(
			self.email.encode('utf-8')).hexdigest()
		db.session.add(self)
		return True

	# rating:是图片的安全等级，即暴露，色情等，size图片大小，default默认图片idention默认关键字符串，网站定义
	def gravatar(self, default='identicon', size=100, rating='g'):
		# https 安全级网站
		if request.is_secure:
			url = 'https://secure.gravatar.com/avatar'
		else:
			url = 'http://www.gravatar.com/avatar'
		md5_hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
		return '{url}/{hash}?s={size}&d={default}&r={rating}'.format \
			(url=url, hash=md5_hash, size=size, default=default, rating=rating)

	# api的认证密令，认证令牌
	def generate_auth_token(self, expiration):
		s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
		return s.dumps({'id': self.id})

	@staticmethod
	def verify_auth_token(token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return None
		return User.query.get(data['id'])


	@staticmethod  # 生成虚拟用户和博客文章
	def generate_fake(count=100):
		from sqlalchemy.exc import IntegrityError
		from random import seed
		import forgery_py
		# 随机数种子，使得每次一样
		seed()
		for i in range(count):
			u = User(email=forgery_py.internet.email_address(),
			         username=forgery_py.internet.user_name(True),
			         password=forgery_py.lorem_ipsum.word(),
			         confirmed=True,
			         name=forgery_py.name.full_name(),
			         location=forgery_py.address.city(),
			         about_me=forgery_py.lorem_ipsum.sentence(),
			         member_since=forgery_py.date.date(True))
			db.session.add(u)
			try:
				db.session.commit()
			except IntegrityError:
				db.session.rollback()

	# 模型中创建函数更新数据库这一技术经常用来更新已部署的程序
	@staticmethod
	def add_self_follow():
		for user in User.query.all():
			if not user.is_following(user):
				user.follow(user)
				db.session.add(user)
				db.session.commit()

	@property
	def password(self):
		raise AttributeError('password is not a readable attribute')

	@password.setter
	def password(self, password):
		self.password_hash = generate_password_hash(password)

	def verify_password(self, password):
		# 返回True， False
		return check_password_hash(self.password_hash, password)

	def ping(self):
		self.last_seen = datetime.utcnow()
		db.session.add(self)

	def __repr__(self):
		return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
	def can(self, permissions):
		return False

	def is_administrator(self):
		return False


# 未登录时 current-user的值
login_manager.anonymous_user = AnonymousUser


# flask-login 要求实现一个回调函数
@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))


# 文章模型
class Post(db.Model):
	__tablename__ = 'posts'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
	author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	body_html = db.Column(db.Text)
	comments = db.relationship('Comment', backref='post', lazy='dynamic')

	def to_json(self):
		json_post = {
			'url': url_for('api.get_post', id=self.id, _external=True),
			'body': self.body,
			'body_html': self.body_html,
			'timestamp': self.timestamp,
			'author': url_for('api.get_user', id=self.id, _external=True),
			'comments': url_for('api.get_post_comments', id=self.id, _external=True),
			'comment_count': self.comments.count(),
		}
		return json_post

	@staticmethod
	def from_json(json_post):
		body = json_post.get('body')
		if body is None or body == '':
			raise ValidationError('post does not have a body')
		return Post(body=body)

	@staticmethod
	def generate_fake(count=100):
		from random import seed, randint
		import forgery_py
		seed()
		user_count = User.query.count()
		for i in range(count):
			# 随机生成文章时要为每篇文章随机指定一个用户
			# offset() 查询过滤器。这个过滤器会跳过参数中指定的记录数量。通过设定一个随机的偏移值
			u = User.query.offset(randint(0, user_count - 1)).first()
			p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
			         timestamp=forgery_py.date.date(True),
			         author=u)
			db.session.add(p)
			db.session.commit()

	# 减少重复性劳动，需要用到数据库字段缓存时，可以考虑在models里解决
	@staticmethod
	def on_changed_body(target, value, oldvalue, initiator):
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
		                'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
		                'h1', 'h2', 'h3', 'h4', 'h5', 'p']
		target.body_html = bleach.linkify(bleach.clean(
			markdown(value, output_format='html'),
			tags=allowed_tags, strip=True))


# 转化markdown为html , 清理没标注的标签， 自动转化url为合适的<a>链接

# on_changed_body 函数注册在body 字段上，是SQLAlchemy“set”事件的监听程序，
# 这意味着只要这个类实例的body 字段设了新值，函数就会自动被调用
db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
	__tablename__ = 'comments'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.Text)
	body_html = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)
	disabled = db.Column(db.Boolean)
	author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
	post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

	@staticmethod
	def on_changed_body(target, value, oldvalue, initiator):
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
		                'strong']
		target.body_html = bleach.linkify(bleach.clean(
			markdown(value, output_format='html'),
			tags=allowed_tags, strip=True))

	def to_json(self):
		json_comment = {
			'url': url_for('api.get_comments', id=self.id, _external=True),
			'post': url_for('api.get_post', id=self.post_id, _external=True),
			'body': self.body,
			'body_html': self.body_html,
			'timestamp': self.timestamp,
			'author': url_for('api.get_user', id=self.author_id, _external=True)
		}
		return json_comment

	@staticmethod
	def from_json(json_comment):
		body = json_comment.get('body')
		if body is None or body == '':
			raise ValidationError('comment does not have a body')
		return Comment(body=body)
db.event.listen(Comment.body, 'set', Comment.on_changed_body)
