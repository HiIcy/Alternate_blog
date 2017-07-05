# _*_ coding:utf-8 _*_

from flask import Blueprint

auth = Blueprint('auth', __name__)

# 蓝本控制路由 引入
from . import views
