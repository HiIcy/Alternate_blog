# _*_coding:utf-8 _*_
import os
from threading import Thread

from flask import render_template, current_app
from flask_mail import Message
from app import create_app, mail


# 异步
def send_async_email(app, msg):
	# 。Flask - Mail中的send()
	# 函数使用current_app，因此必须激活程序上下文
	with app.app_context():
		mail.send(msg)


def send_email(to, subject, template, **kwargs):
	app = current_app._get_current_object()
	msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
	              sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
	msg.body = render_template(template + '.txt', **kwargs)
	msg.html = render_template(template + '.html', **kwargs)

	thr = Thread(target=send_async_email, args=(app, msg))
	thr.start()
	return thr