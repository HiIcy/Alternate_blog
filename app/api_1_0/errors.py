# _*_ coding:utf-8 _*_
from flask import jsonify

from app.api_1_0 import api
from app.exceptions import ValidationError


def forbidden(message):
	response = jsonify({'error':"forbidden", 'message': message})
	response.status = 403
	return response


def unauthorized(message):
	# jsonify会把这个字典转化为json格式 响应对象 send to 浏览器
	response = jsonify({'error': 'unauthorized', 'message': message})
	response.status = 401
	return response


def method_not_allowed(message):
	response = jsonify({'error': 'method_not_allowed', 'message': message})
	response.status = 405
	return response


def bad_request(message):
	response = jsonify({'error': 'bad_request', 'message': message})
	response.status = 400
	return response


@api.errorhandler(ValidationError)
def validation_error(e):
	return bad_request(e.args[0])