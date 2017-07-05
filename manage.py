# _*_coding:utf-8 _*_
# !/usr/bin/env python
import os

from flask import current_app

from app import create_app, db
from app.models import User, Role, Permission, Post, Follow, Comment
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

COV = None
if os.environ.get('FLASK_COVERAGE'):
	import coverage
	COV = coverage.coverage(branch=True, include='app/*')
	COV.start()
# 获取一个程序实例，并已附加了大量配置，
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
	# 这里加入只是在shell命令里可用
	return dict(app=app, db=db, User=User, Role=Role,
	            Permission=Permission, Post=Post, Follow=Follow,
	            Comment=Comment)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


# 验证代码测试的覆盖率
@manager.command
def test(coverage=False):
	"""Run the unit tests."""
	if coverage and not os.environ.get('FLASK_COVERAGE'):
		import sys
		os.environ['FLASK_COVERAGE'] = '1'
		os.execvp(sys.executable, [sys.executable] + sys.argv)
	import unittest
	tests = unittest.TestLoader().discover('tests')
	unittest.TextTestRunner(verbosity=2).run(tests)
	if COV:
		COV.stop()
		COV.save()
		print('Coverage Summary:')
		COV.report()
		basedir = os.path.abspath(os.path.dirname(__file__))
		covdir = os.path.join(basedir, 'tmp/coverage')
		COV.html_report(directory=covdir)
		print('HTML version: file://%s/index.html' % covdir)
		COV.erase()


@manager.command
def profile(length=25, profile_dir=None):  #在请求分析器的监视下运行程序
	from werkzeug.contrib.profiler import ProfilerMiddleware
	app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
	                                  profile_dir=profile_dir)
	app.run


@manager.command
def deploy():
	from flask_migrate import upgrade
	from app.models import Role, User

	# 迁移数据库到最新修订版本
	upgrade()

	Role.insert_roles()
	User.add_self_follow()
# 因此每次安装或升级程序时只需运行deploy 命令就能完成所有操作。


if __name__ == '__main__':
	manager.run()
