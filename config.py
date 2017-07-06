# _*_coding:utf-8 _*_
"""
_*_: 不同环境的不同数据库
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
	SQLALCHEMY_RECORD_QUERIES = True
	FLASKY_DB_QUERY_TIMEOUT = 0.5
	FLASK_COVERAGE = None
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
	FLASKY_POSTS_PER_PAGE = 7
	FLASKY_FOLLOWERS_PER_PAGE = 6
	SQLALCHEMY_COMMIT_ON_TEARDOWN = True
	FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
	FLASKY_MAIL_SENDER = os.environ.get('MAIL_USERNAME')
	FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
	MAIL_PORT = 465
	MAIL_USE_SSL = True
	MAIL_USE_TLS = True
	MAIL_SERVER = 'smtp.qq.com'
	MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
	# 授权码
	MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

	@staticmethod
	def init_app(app):
		pass


class DevelopmentConfig(Config):
	DEBUG = True

	# MAIL_PASSWORD = 'yeaynuflvjtpbahj'
	SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
	                          'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
	WTF_CSRF_ENABLED = False
	TESTING = True
	SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
	                          'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')


class ProductionConfig(Config):
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
	                          'sqlite:///' + os.path.join(basedir, 'data.sqlite')

	# 程序出错时发送电子邮件
	@classmethod
	def init_app(cls, app):
		Config.init_app(app)
		# 把错误通过电子邮件发送给管理员
		import logging
		from logging.handlers import SMTPHandler
		credentials = None
		secure = None
		if getattr(cls, 'MAIL_USERNAME', None) is not None:
			credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
			if getattr(cls, 'MAIL_USE_TLS', None):
				secure = ()
			mail_handler = SMTPHandler(
				mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
				fromaddr=cls.FLASKY_MAIL_SENDER,
				toaddrs=[cls.FLASKY_ADMIN],
				subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + 'Applilcation Error',
				credentials=credentials,
				secure=secure)
			mail_handler.setLevel(logging.ERROR)
			app.logger.addHandler(mail_handler)

# config_name
config = {
	'development': DevelopmentConfig,
	'testing': TestingConfig,
	'production': ProductionConfig,
	'default': DevelopmentConfig
}
