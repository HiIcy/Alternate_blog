# _*_coding:utf-8 _*_
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField,FileField

from wtforms.validators import DataRequired, Length, Email, Regexp, ValidationError
from flask_pagedown.fields import PageDownField
from app.models import Role, User


class EditProfileForm(FlaskForm):
	name = StringField('Real name', validators=[Length(0, 64)])
	location = StringField('Location', validators=[Length(0, 64)])
	about_me = TextAreaField('About me')
	submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
	email = StringField(u"新邮件地址", validators=[DataRequired(), Length(5, 20), Email()])
	username = StringField('Username', validators=[DataRequired(),
	                                               Length(1, 64),
	                                               Regexp('^[a-zA-Z][a-zA-Z0-9_.]*$', 0, message='Usernames must have only letters, numbers, dots or underscores')])
	confirmed = BooleanField('Confirmed')
	# 强制整数型
	role = SelectField('Role', coerce=int)
	name = StringField('Real name', validators=[Length(0, 64)])
	location = StringField('Location', validators=[Length(0, 64)])
	about_me = TextAreaField('About me')
	submit = SubmitField('Submit')

	def __init__(self, user, *args, **kwargs):
		super(EditProfileAdminForm, self).__init__(*args, **kwargs)
		# 用角色id来代表不同值，强制整数型，一个元组一个部分
		self.role.choices = [(role.id, role.name)
		                     for role in Role.query.order_by(Role.name).all()]
		self.user = user

	# 参数field 直接就是表单该字段！
	def validate_email(self, field):
		# 不是针对的当前用户，是管理员要修改的用户，所以加个条件
		if User.query.filter_by(email=field.data).first() and \
				field.data != self.user.email:
			raise ValidationError('Email already registered.')

	def validate_username(self, field):
		if field.data != self.user.username and \
				User.query.filter_by(username=field.data).first():
			raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
	body = PageDownField("What's on you mind?", validators=[DataRequired()])
	submit = SubmitField("Submit")


class CommentForm(FlaskForm):
	body = StringField("leave your comment")
	submit = SubmitField("Submit")

class AvatarForm(FlaskForm):
	avatar = FileField('头像上传')
	submit = SubmitField("Submit")
