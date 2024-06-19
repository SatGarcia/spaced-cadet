import unittest
import warnings
from urllib.parse import urlparse
from flask import url_for

from app import create_app, db
from app.db_models import User, Course, ShortAnswerQuestion, TextAttempt
from datetime import date, datetime, timedelta

class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore', category=DeprecationWarning)

        self.app = create_app('config.TestConfig')
        self.app.config['SERVER_NAME'] = 'localhost.localdomain:5000'
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # create two example users
        u1 = User(email="user1@example.com", first_name="User", last_name="Uno")
        u1.set_password('testing1')
        u2 = User(email="user2@example.com", first_name="User", last_name="Uno")
        u2.set_password('testing2')

        db.session.add_all([u1, u2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_successful_login(self):
        response = self.client.post(url_for('auth.login'), data={
            "email": "user1@example.com",
            "password": "testing1"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path,
                         url_for('user_views.root', _external=False))

    def test_successful_login_redirect(self):
        """ Tests that login redirects to wherever next argument says. """
        response = self.client.post(url_for('auth.login', next='/foobar'), data={
            "email": "user1@example.com",
            "password": "testing1"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, '/foobar')

    def test_wrong_email(self):
        response = self.client.post('/auth/login', data={
            "email": "user@example.com",
            "password": "testing1"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not sign in", response.data)

    def test_wrong_password(self):
        response = self.client.post('/auth/login', data={
            "email": "user1@example.com",
            "password": "badpassword"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not sign in", response.data)

if __name__ == '__main__':
    unittest.main(verbosity=2)
