# _*_ coding:utf-8 _*_
import re
import threading
import unittest

from selenium import webdriver

from app import create_app, db
from app.models import Role, User, Post


class SeleniumTestCase(unittest.TestCase):
	client = None

	@classmethod
	def setUpClass(cls):
		try:
			cls.client = webdriver.Chrome()
		except:
			pass
		if cls.client:
			cls.app = create_app('testing')
			cls.app_context = cls.app.app_context()
			cls.app_context.push()

			# 禁止日志，保持输出简洁
			import logging
			logger = logging.getLogger('werkzeug')
			logger.setLevel("ERROR")

			db.create_all()
			Role.insert_roles()
			User.generate_fake(10)
			Post.generate_fake(10)

			# 添加管理员
			admin_role = Role.query.filter_by(permissions=0xff).first()
			admin = User(email='john@example.com',
			             username='john', password='cat',
			             role=admin_role, confirmed=True)
			db.session.add(admin)
			db.session.commit()

			threading.Thread(target=cls.app.run).start()

	@classmethod
	def tearDownClass(cls):
		if cls.client:
			cls.client.get('http://localhost:5000/shutdown')
			cls.client.close()
			db.drop_all()
			db.session.remove()
			cls.app_context.pop()

	def setUp(self):
		if not self.client:
			self.skipTest('Web browser not available')

	def tearDown(self):
		pass

	def test_admin_home_page(self):
		# navigate to home page
		self.client.get('http://localhost:5000/')
		self.assertTrue(re.search('Hello,\s+Stranger!',
		                          self.client.page_source))

		# navigate to login page
		self.client.find_element_by_link_text('Log In').click()
		self.assertTrue('<h1>Login</h1>' in self.client.page_source)

		# login
		self.client.find_element_by_name('email'). \
			send_keys('896913183@qq.com')
		self.client.find_element_by_name('password').send_keys('555666')
		self.client.find_element_by_name('submit').click()
		self.assertTrue(re.search('Hello,\s+meng!', self.client.page_source))

		# navigate to the user's profile page
		self.client.find_element_by_link_text('Profile').click()
		self.assertTrue('<h1>john</h1>' in self.client.page_source)