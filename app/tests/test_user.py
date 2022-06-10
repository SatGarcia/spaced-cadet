import unittest
from app import create_app, db
from app.db_models import User, Course
from datetime import date, timedelta

class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(email="test@test.com", first_name="Test", last_name="User")
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_get_current_courses(self):
        u = User(email="test@test.com", first_name="Test", last_name="User")
        u.set_password('test')
        db.session.add(u)
        db.session.commit()

        self.assertEqual(u.get_current_courses(), [])
        c1 = Course(name="test-course1", title="Test Course 1", description="",
                    start_date=(date.today()-timedelta(days=1)),
                    end_date=(date.today()+timedelta(days=1)))

        c2 = Course(name="test-course2", title="Test Course 2", description="",
                    start_date=date.today(), end_date=date.today())

        c3 = Course(name="test-course3", title="Test Course 3", description="",
                    start_date=(date.today()+timedelta(days=1)),
                                end_date=(date.today()+timedelta(days=2)))

        # add the newer course in first (just to make sure ordering is correct
        # later)
        u.courses.append(c2)
        u.courses.append(c1)

        current_courses = u.get_current_courses()

        # check that contents are correct (i.e. disregarding order)
        self.assertCountEqual(current_courses, [c1, c2])

        # check that results are sorted from oldest start_date to newest
        self.assertEqual(current_courses, [c1, c2])

    def test_get_active_courses(self):
        u = User(email="test@test.com", first_name="Test", last_name="User")
        u.set_password('test')
        db.session.add(u)
        db.session.commit()

        self.assertEqual(u.get_active_courses(), [])

        #start: yesterday end: tomorrow
        c1 = Course(name="test-course1", title="Test Course 1", description="",
                    start_date=(date.today()-timedelta(days=1)),
                    end_date=(date.today()+timedelta(days=1)))

        #start: today end: today
        c2 = Course(name="test-course2", title="Test Course 2", description="",
                    start_date=date.today(), end_date=date.today())

        #start: tomorrow end: 2 days
        c3 = Course(name="test-course3", title="Test Course 3", description="",
                    start_date=(date.today()+timedelta(days=1)),
                                end_date=(date.today()+timedelta(days=2)))

        #start: yesterday end: yesterday
        c4 = Course(name="test-course3", title="Test Course 3", description="",
                    start_date=(date.today()-timedelta(days=1)),
                                end_date=(date.today()-timedelta(days=1)))

        # add the newer course in first (just to make sure ordering is correct
        # later)
        u.courses.append(c3)
        u.courses.append(c2)
        u.courses.append(c1)
        u.courses.append(c4)

        current_courses = u.get_current_courses()

        # check that contents are correct (i.e. disregarding order)
        self.assertCountEqual(current_courses, [c1, c2])

        # check that results are sorted from oldest start_date to newest
        self.assertEqual(current_courses, [c1, c2])

    @unittest.skip("Test not implemented")
    def test_latest_next_attempts(self):
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)
