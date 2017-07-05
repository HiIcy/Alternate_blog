# _*_ coding:utf-8 _*_

"""
这种用户认证方法只在API 蓝本中使用，所以Flask-HTTPAuth 扩展只在蓝本包中初
始化，而不像其他扩展那样要在程序包中初始化
"""
from app.api_1_0 import api
from .errors import forbidden, unauthorized
from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
# 创建一个HTTPBasicAuth对象
from app.models import AnonymousUser, User

auth = HTTPBasicAuth()


# flask 全局对象 g
# 验证回调函数
@auth.verify_password
def verify_password(email_or_token, password):
	if email_or_token == '':
		# g保存的是 当前 请求的全局变量，不同的请求会有不同的全局变量，通过不同的thread id区别
		g.current_user = AnonymousUser()
		return True
	if password == '':
		g.current_user = User.verify_auth_token(email_or_token)
		g.token_used = True
		return g.current_user is not None
	user = User.query.filter_by(email=email_or_token).first()
	if not user:
		return False
	g.current_user = user
	g.token_used = False
	return user.verify_password(password)


@api.route('/token')
def get_token():
	# 避免客户端使用旧令牌申请新令牌
	if g.current_user.is_anonymous or g.token_used:
		return unauthorized('Invalid credentials')
	return jsonify({'token': g.current_user.generate_auth_token(expiration=3600),
	                'expiration': 3600})


@auth.error_handler
def auth_error():
	return unauthorized('Invaild credentials')


# api中的before_request
@api.before_request
@auth.login_required
def befor_request():
	if not g.current_user.is_anonymous and \
		not g.current_user.confirmed:
		return forbidden("Unconfirmed account")