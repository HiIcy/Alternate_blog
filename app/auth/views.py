# _*_ coding:utf-8 _*_

from flask import render_template, request, redirect, url_for, flash, abort
from ..email import send_email
from app import db
from . import auth
from flask_login import login_user, logout_user, login_required, current_user
from .forms import LoginForm, RegistrationForm, ChangePasswordForm
from .forms import ResetPasswordRequestForm, ResetPasswordForm
from .forms import ChangeEmailForm
from ..models import User


# before_request 钩子只能应用到属于蓝本的请求上。若想在
# 蓝本中使用针对程序全局请求的钩子，必须使用before_app_request 修饰器
@auth.before_app_request
def before_request():  # 重写改方法
	if current_user.is_authenticated:
		current_user.ping()
		if not current_user.confirmed \
			and request.endpoint[:5] != 'auth.' \
			and request.endpoint != 'static':
			return redirect(url_for('auth.unconfirmed'))
# endpoint url对应其实找的是端点，是可以改的,只是默认就是对应的视图函数而已


@auth.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		# 数据库语句的orm, 对比django
		user = User.query.filter_by(email=form.email.data).first()
		# 用户密码验证
		if user is not None and user.verify_password(form.password.data):
			login_user(user, form.remember_me.data)
			return redirect(request.args.get('next') or url_for('main.index'))
		flash('Invalid username or password.')
	return render_template('auth/login.html', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def register():
	form = RegistrationForm()
	# 验证表单合理合法性，必选
	if form.validate_on_submit():
		user = User(email=form.email.data,
		            username=form.username.data,
		            password=form.password1.data)
		db.session.add(user)
		db.session.commit()
		# 生成密码哈希
		token = user.generate_confirmation_token()
		# 发送邮件去确认
		send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
		flash('A confirmation email has been sent to you by email.')
		# post/重定向/get 模式，
		return redirect(url_for('main.index'))
	return render_template('auth/register.html', form=form)


# 不需要界面，纯后台处理验证
# 动态url
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
	# 检查是否确认过，避免过多操作，
	if current_user.confirmed:
		return redirect(url_for('main.index'))
	# 令牌确认完全在User 模型中完成，所以视图函数只需调用confirm() 方法
	if current_user.confirm(token):
		flash('You have confirmed your account. Thanks!')
	else:
		flash('The confirmation link is invalid or has expired.')
	return redirect(url_for('main.index'))


@auth.route('/unconfirmed', endpoint='unconfirmed')
def unconfirmed():
	if current_user.is_anonymous or current_user.confirmed:
		return redirect(url_for('main.index'))
	return render_template('auth/unconfirmed.html')


@auth.route('/confirm')
@login_required  # 确保程序知道current_user
def resend_confirmation():
	token = current_user.generate_confirmation_token()
	# 发送邮件去确认
	send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
	flash('A confirmation email has been sent to you by email.')
	# post/重定向/get 模式，
	return redirect(url_for('main.index'))


# 重设密码
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
	form = ChangePasswordForm()
	if form.validate_on_submit():
		if current_user.verify_password(form.oldpassword.data):
			current_user.password = form.newpassword1.data
			db.session.add(current_user)
			# 急时修改提交，免得迟缓
			db.session.commit()
			flash(U"密码修改成功，请重新登陆，thanks")
			# 重新登陆先退出
			logout_user()
			return redirect(url_for('auth.login'))
		flash(U"原密码不对，请重新输入")
	return render_template('auth/change_password.html', form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def reset_password_request():
	# 用户已登录，就不算忘记密码
	if not current_user.is_anonymous:
		return redirect(url_for('main.index'))

	form = ResetPasswordRequestForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		# 有这么个用户存在，就发送邮件
		if user:
			# 新令牌
			token = user.generate_reset_token()
			send_email(user.email, 'Reset Your Password',
			           'auth/email/reset_password', user=user,
			           token=token, next=request.args.get('next'))
			flash('An email with instructions to reset your password has been sent to you.')
			return redirect(url_for('auth.login'))
	return render_template('auth/reset_password.html', form=form)


# 重置密码链接
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
	if not current_user.is_anonymous:
		return redirect(url_for('main.index'))

	form = ResetPasswordForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user is None:
			return redirect(url_for('main.index'))

		if user.reset_password(token, form.password1.data):
			flash('Your password has been updated.')
			return redirect(url_for('auth.login'))
		else:
			return redirect(url_for('main.index'))
	return render_template('auth/reset_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
	form = ChangeEmailForm()
	if form.validate_on_submit():
		if current_user.verify_password(form.password.data):
			new_email = form.email.data
			token = current_user.generate_email_change_token(new_email)
			send_email(new_email, 'Confirm your email address',
			           'auth/email/change_email',
			           user=current_user, token=token)
			flash('An email with instructions to confirm your new email '
			      'address has been sent to you.')
			return redirect(url_for('main.index'))
		else:
			flash('Invalid email or password.')
	return render_template("auth/change_email.html", form=form)


@auth.route('/change/<token>')
@login_required
def change_email(token):
	if current_user.change_email(token):
		flash('Your email address has been updated.')
	else:
		flash('Invalid request.')
	return redirect(url_for('main.index'))


@auth.route('/logout')
@login_required
def logout():
	# flask-login中的函数
	logout_user()
	flash('You have been logged out.')
	return redirect(url_for('main.index'))


