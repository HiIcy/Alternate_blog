# _*_ coding:utf-8 _*_

from flask import Blueprint
# 构造完蓝本后，还要去注册蓝本
api = Blueprint('api', __name__)

from .import authentication, posts, comments, decorators, errors, users
