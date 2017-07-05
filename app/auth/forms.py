# _*_ coding:utf-8 _*_

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Length(5, 20), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	remember_me = BooleanField("keep me logged in")
	submit = SubmitField("log in")


class RegistrationForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Length(5, 20), Email()])
	username = StringField('Username', validators=[DataRequired(), Length(1, 64), Regexp('^[a-zA-Z][A-Za-z._]*$',0,
	                                                                                     'Usernames must have only letters,'
	                                                                                    'numbers, dots or underscores')])
	# EqualTo验证两个字段的值很有用，
	password1 = PasswordField('Password', validators=[
		DataRequired(), EqualTo('password2', message='Passwords must match.')])
	password2 = PasswordField('Confirm password', validators=[DataRequired()])
	submit = SubmitField("Register")

	# 表单类中定义了以validate_ 开头且后面跟着字段名的方法，这个方法就和常规的验证函数一起调用
	# 填表单的时候就开始执行，
	def validate_email(self, field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('Email already registered.')

	def validate_username(self, field):
		if User.query.filter_by(username=field.data).first():
			raise ValidationError('Username already in use.')


class ChangePasswordForm(FlaskForm):
	oldpassword = PasswordField("old password", validators=[DataRequired()])
	newpassword1 = PasswordField('newPassword', validators=[
		DataRequired(), EqualTo('newpassword2', message='Passwords must match.')])
	newpassword2 = PasswordField('Confirm password', validators=[DataRequired()])
	submit = SubmitField("Update The Password")


class ResetPasswordRequestForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Length(5, 20), Email()])
	submit = SubmitField("Reset the Password")


class ResetPasswordForm(FlaskForm):
	email = StringField('Email', validators=[DataRequired(), Length(1, 64),
	                                         Email()])
	password1 = PasswordField('Password', validators=[
		DataRequired(), EqualTo('password2', message='Passwords must match.')])
	password2 = PasswordField('Confirm password', validators=[DataRequired()])
	submit = SubmitField("Register")

	def validate_email(self, field):
		if User.query.filter_by(email=field.data).first() is None:
			raise ValidationError("Unknown email address")


class ChangeEmailForm(FlaskForm):
	email = StringField(u"新邮件地址", validators=[DataRequired(), Length(5, 20), Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Update Email Address')

	def validate_email(self, field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('Email already registered.')