# _*_coding:utf-8 _*_

from flask import Blueprint

from app.models import Permission

main = Blueprint('main', __name__)


# 上下文处理器能让变量在所有模板中全局可访问。
# 把Permission 类加入模板上下文
@main.app_context_processor
def inject_permissions():
	return dict(Permission=Permission)

from . import views, errors
# 程序的路由保存在包里的app/main/views.py 模块中，而错误处理程序保存在app/main/
# errors.py 模块中。导入这两个模块就能把路由和错误处理程序与蓝本关联起来