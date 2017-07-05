# _*_coding:utf-8 _*_

from flask import render_template, request, jsonify
from . import main


@main.app_errorhandler(404)
def page_not_found(e):
	# 根据客户端请求格式，可接收类型；内容协商处理
	if request.accept_mimetypes.accept_json and \
		not request.accept_mimetypes.accept_html:
		response = jsonify({'error': 'not found'})
		response.status_code = 404
	return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
	if request.accept_mimetypes.accept_json and \
		not request.accept_mimetypes.accept_html:
		response = jsonify({'error': 'internal server error'})
		response.status_code = 500
	return render_template('500.html'), 500