# _*_coding:utf-8 _*_
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_pagedown import PageDown
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager



login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = 'auth.login'
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()


# 工厂函数返回创建的程序实例
def create_app(config_name):
	app = Flask(__name__)
	app.config.from_object(config[config_name])
	config[config_name].init_app(app)
	# 初始化扩展
	bootstrap.init_app(app)
	mail.init_app(app)
	moment.init_app(app)
	login_manager.init_app(app)
	pagedown.init_app(app)
	db.init_app(app)

	# 附加路由和自定义的错误页面

	# 蓝本要在工厂函数里附加到程序中，注册蓝本
	from .main import main as main_blueprint
	from .auth import auth as auth_blueprint
	from .api_1_0 import api as api_1_0_blueprint

	app.register_blueprint(main_blueprint)
	# url_prefix 默认的路由前缀
	app.register_blueprint(auth_blueprint, url_prefix='/auth')
	app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

	return app
