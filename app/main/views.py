# coding=utf-8
import os
from datetime import datetime
from flask import render_template, session, redirect, url_for, abort, flash, request, current_app, make_response
from flask_login import current_user, login_required
from app.decorators import admin_required, permission_required
from app.main.forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, AvatarForm
from . import main
from .. import db
from PIL import Image
from ..models import User, Role, Permission, Post, Comment
from flask_sqlalchemy import get_debug_queries

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


@main.route('/', methods=['GET', 'POST'])
def index():
	form = PostForm()
	if current_user.can(Permission.WRITE_ARTICLES) and \
			form.validate_on_submit():
		# _get_current_object获得一个数据库真正用户对象
		# current_user轻度包装
		# 和所有上下文变量一样，是通过线程内的代理对象实现。这个对象的表现类似用户对象
		post = Post(body=form.body.data,
					author=current_user._get_current_object())
		db.session.add(post)
	# 从请求的查询字符串（request.args）中获取
	# 默认第一页，参数type=int 保证参数无法转换成整数时，返回默认值
	page = request.args.get('page', 1, type=int)
	show_followed = False
	if current_user.is_authenticated:
		show_followed = bool(request.cookies.get('show_followed', ''))
	if show_followed:
		query = current_user.followed_posts
	else:
		query = Post.query
	# 按时间戳降序排列 数据库中所有博客文章
	pagination = query.order_by(Post.timestamp.desc()).paginate(
		# 存在实例化的app后就可以通过.config[]去获取config文件的东西
		page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
		error_out=False)
	posts = pagination.items
	return render_template('index.html', form=form, posts=posts,
						   pagination=pagination, show_followed=show_followed)


@main.route('/user/<username>')
def user(username):
	user = User.query.filter_by(username=username).first()

	# 要考虑存不存在的情况
	if user is None:
		abort(404)
	page = request.args.get('page', 1, type=int)
	pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
		page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
		error_out=False)
	posts = pagination.items
	return render_template('user.html', user=user, posts=posts,
						   pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm()
	if form.validate_on_submit():
		current_user.name = form.name.data
		current_user.location = form.location.data
		current_user.about_me = form.about_me.data
		db.session.add(current_user)
		flash('Your profile has been updated.')
		# 是函数参数 username
		return redirect(url_for('.user', username=current_user.username))
	form.name.data = current_user.name
	form.location.data = current_user.location
	form.about_me.data = current_user.about_me
	return render_template('edit_profile.html', form=form)


# 指定类型<type: >
@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
	# 这里不一定成功获取对象，所以用get_or_404
	user = User.query.get_or_404(id)
	form = EditProfileAdminForm(user=user)
	if form.validate_on_submit():
		user.email = form.email.data
		user.username = form.username.data
		user.confirmed = form.confirmed.data
		user.role = Role.query.get(form.role.data)
		user.name = form.name.data
		user.location = form.location.data
		user.about_me = form.about_me.data
		db.session.add(user)
		flash('The profile has been updated.')
		return redirect(url_for('main.user', username=user.username))
	form.email.data = user.email
	form.username.data = user.username
	form.confirmed.data = user.confirmed
	form.role.data = user.role_id
	form.name.data = user.name
	form.location.data = user.location
	form.about_me.data = user.about_me
	return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
	post = Post.query.get_or_404(id)
	form = CommentForm()
	if form.validate_on_submit():
		comment = Comment(body=form.body.data, post=post,
						  # current_user 上下文代理对象
						  author=current_user._get_current_object())
		db.session.add(comment)
		flash("Your comment has been published ")
		return redirect(url_for(".post", id=post.id, page=-1))
	page = request.args.get('page', 1, type=int)
	if page == -1:
		page = (post.comments.count() - 1) / \
			current_app.config['FLASKY_FOLLOWERS_PER_PAGE'] + 1
	pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
		page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
		error_out=True)
	comments = pagination.items
	# 传入列表，因为只有这样，index.html和user.html引用的_posts.html
	# 模板才能在这个页面中使用
	return render_template('post.html', posts=[post], form=form,
						   comments=comments, pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id)
	if current_user != post.author and \
			not current_user.can(Permission.ADMINISTER):
		abort(403)
	form = PostForm()
	if form.validate_on_submit():
		# 这里调用了那个markdown to html的方法
		post.body = form.body.data
		db.session.add(post)
		flash('The post has been updated')
		return redirect(url_for('.post', id=post.id))
	form.body = post.body
	return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(user):
		flash('You are already following this user.')
		return redirect(url_for('.user', username=username))
	current_user.follow(user)
	flash('You are now following %s.' % username)
	return redirect(url_for('.user', username=username))


# 不需要要模板，只要后台实现效果
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(user):
		current_user.unfollow(user)
		flash('You have already unfollowed this user.')
		return redirect(url_for('.user', username=username))
	return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followers.paginate(page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
										 error_out=True)
	# 提取所有跟随者，
	follows = [{'user': item.follower, 'timestamp': item.timestamp}
			   for item in pagination.items]
	return render_template('followers.html', user=user, title="Followers of, ",
						   endpoint='.followers', pagination=pagination, follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('Invalid user.')
		return redirect(url_for('.index'))
	# 1：分页技术，先获取页数
	page = request.args.get('page', 1, type=int)
	# 2：对目标数据构造分页器对象，
	pagination = user.followed.paginate(page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
										error_out=True)
	follows = [{'user': item.followed, 'timestamp': item.timestamp}
			   for item in pagination.items]
	# 3：传过去，借用其方法实现效果
	return render_template('followers.html', user=user, title="Followed by, ",
						   endpoint='.followed_by', pagination=pagination, follows=follows)


@main.route('/all')
@login_required
def show_all():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '', max_age=30 * 24 * 60 * 60)
	return resp


# cookie 只能在响应对象中设置
@main.route('/followed')
@login_required
def show_followed():
	resp = make_response(redirect(url_for('.index')))
	resp.set_cookie('show_followed', '1', max_age=30 * 24 * 60 * 60)
	return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
	page = request.args.get('page', 1, type=int)
	pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
		page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
		error_out=True)
	comments = pagination.items
	return render_template('moderate.html', comments=comments,
						   pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = False
	db.session.add(comment)
	return redirect(url_for('.moderate',
							page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = True
	db.session.add(comment)
	return redirect(url_for('.moderate',
							page=request.args.get('page', 1, type=int)))


@main.route('/shutdown')
def server_shutdown():
	if not current_app.testing:
		abort(404)
	shutdown = request.environ.get('werkzeug.server.shutdown')
	if not shutdown:
		abort(500)
	shutdown()
	return 'Shutting down...'


@main.route('/user/<int:id>/write-article', methods=['GET', 'POST'])
@permission_required(Permission.WRITE_ARTICLES)
@login_required
def write_article(id):
	# flask 多用query来查询，，
	user = User.query.get_or_404(id)
	form = PostForm()
	if current_user != user:
		abort(403)
	if form.validate_on_submit() and current_user.can(Permission.WRITE_ARTICLES):
		post = Post(body=form.body.data, author=user)
		db.session.add(post)
		return redirect(url_for('.index'))
	return render_template('edit_post.html', form=form)

# 上传头像
@main.route('/user/<int:id>/upload_avatar', methods=['GET', 'POST'])
@login_required
def upload_avatar(id):
	user = User.query.get_or_404(id)
	flash('wahg')
	if user is None:
		flash('none')
		abort(403)
	if current_user != user:
		flash("kong")
		abort(403)
	form = AvatarForm()
	if request.method == 'POST':
		# flash('heel')
		# 获取上传的文件
		# avatar = request.files['avatar']
		avatar = form.avatar.data
		size = (40,40)
		im = Image.open(avatar)
		im.thumbnail(size) # 修改图片大小
		UPLOAD_FOLDER = current_app.config['UPLOAD_PHOTO_FOLDER']
		if not allowed_file(avatar.filename):
			flash('文件类型错误')
			return redirect(url_for('.user', user=user.username))
		# secure_filename(filename) 对文件命名保护
		# 保存上传文件到某个位置
		im.save('{}\{}_{}'.format(
			UPLOAD_FOLDER, current_user.username, avatar.filename))
		current_user.avatar ='/static/avatar/{}_{}'.format(current_user.username, avatar.filename)

		# current_user.avatar = '/static/avatar/{}_{}'.format(
		# 	current_user.username, avatar.filename)
		db.session.add(current_user)
		flash(u'修改成功')
		return redirect(url_for('.user', username=current_user.username))

	return render_template('upload_avatar.html', user=user)
# 限定文件上传类型
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# 在视图函数处理完请求之后执行。Flask 把响应对象传给after_app_
# request 处理程序，以防需要修改响应
# @main.after_app_request
# def after_request(response):  # 报告缓慢的数据库查询
# 	# get_debug_queries 返回一个记录列表
# 	for query in get_debug_queries():
# 		if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
# 			current_app.logger.warning(
# 				'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' %
# 				(query.statement, query.parameters, query.duration, query.context))
# 	return response
