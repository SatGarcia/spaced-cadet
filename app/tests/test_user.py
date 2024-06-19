import unittest
from app import create_app, db
from app.db_models import User, Course, ShortAnswerQuestion, TextAttempt
from datetime import date, datetime, timedelta
from sqlalchemy_utils import ScalarListType #need this to make the FITB question answers field a list.

class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.u = User(email="test@test.com", first_name="Test", last_name="User")
        self.u.set_password('test')
        db.session.add(self.u)
        db.session.commit()

        #start: yesterday end: tomorrow
        self.c1 = Course(name="test-course1", title="Test Course 1", description="",
                    start_date=(date.today()-timedelta(days=1)),
                    end_date=(date.today()+timedelta(days=1)))

        #start: today end: today
        self.c2 = Course(name="test-course2", title="Test Course 2", description="",
                    start_date=date.today(), end_date=date.today())

        #start: tomorrow end: 2 days
        self.c3 = Course(name="test-course3", title="Test Course 3", description="",
                    start_date=(date.today()+timedelta(days=1)),
                                end_date=(date.today()+timedelta(days=2)))

        #start: yesterday end: yesterday
        self.c4 = Course(name="test-course4", title="Test Course 4", description="",
                    start_date=(date.today()-timedelta(days=1)),
                                end_date=(date.today()-timedelta(days=1)))

        self.c5 = Course(name="test-course5", title="Test Course 5", description="",
                    start_date=(date.today()-timedelta(days=1)),
                                end_date=(date.today()-timedelta(days=1)))

        # to make sure that a new course isn't appended
        db.session.add(self.c5)
        db.session.commit()


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

        self.assertEqual(self.u.get_current_courses(), [])

        # add the newer course in first (just to make sure ordering is correct
        # later)
        self.u.courses.append(self.c3)
        self.u.courses.append(self.c2)
        self.u.courses.append(self.c1)
        self.u.courses.append(self.c4)

        db.session.commit() #ADD TO OTHERS
        current_courses = self.u.get_current_courses()

        # check that contents are correct (i.e. disregarding order)
        self.assertCountEqual(current_courses, [self.c1, self.c2])

        # check that results are sorted from oldest start_date to newest
        self.assertEqual(current_courses, [self.c1, self.c2])

    def test_get_active_courses(self):

        self.assertEqual(self.u.get_active_courses(), [])

        # add the newer course in first (just to make sure ordering is correct
        # later)
        self.u.courses.append(self.c3)
        self.u.courses.append(self.c2)
        self.u.courses.append(self.c1)
        self.u.courses.append(self.c4)

        current_courses = self.u.get_active_courses()

        # check that contents are correct (i.e. disregarding order)
        self.assertCountEqual(current_courses, [self.c1, self.c2, self.c3])

        # check that results are sorted from oldest start_date to newest
        self.assertEqual(current_courses, [self.c1, self.c2, self.c3])

    def test_get_past_courses(self):
        
        self.assertEqual(self.u.get_past_courses(), [])

        # add the newer course in first (just to make sure ordering is correct
        # later)
        self.u.courses.append(self.c3)
        self.u.courses.append(self.c2)
        self.u.courses.append(self.c1)
        self.u.courses.append(self.c4)

        current_courses = self.u.get_past_courses()

        # check that contents are correct (i.e. disregarding order)
        self.assertCountEqual(current_courses, [self.c4])

        # check that results are sorted from oldest start_date to newest
        self.assertEqual(current_courses, [self.c4])

    def test_latest_next_attempts(self):

        q1 = ShortAnswerQuestion(prompt="Question 1", answer="Answer 1")
        q2 = ShortAnswerQuestion(prompt="Question 2", answer="Answer 2")
        q3 = ShortAnswerQuestion(prompt="Question 3", answer="Answer 3")
        q4 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 4")
        q5 = ShortAnswerQuestion(prompt="Question 4", answer="Answer 5")

        db.session.add(q5)
        db.session.commit()

        u1 = User(email="test1@test.com", first_name="Test1", last_name="User")
        u1.set_password("test")
        u2 = User(email="test2@test.com", first_name="Test2", last_name="User")
        u2.set_password("test")
        db.session.add_all([u1, u2])
        db.session.commit()

        self.assertCountEqual(u1.latest_next_attempts().all(), [])

        q1_attempt = TextAttempt(response="Meow", user=u1, question=q1,
                                 next_attempt=date.today())   
        q2_attempt = TextAttempt(response="Meow", user=u1, question=q2,
                                 next_attempt=date.today()+timedelta(days=1))
        q3_attempt = TextAttempt(response="Meow", user=u1, question=q3,
                                 next_attempt=date.today()-timedelta(days=1))

        
        # single attempt for u2, with next attempt of tomorrow to make sure
        # method differentiates between users
        q4_attempt = TextAttempt(response="Meow", user=u2, question=q4,
                                 next_attempt=datetime.today()+timedelta(days=1))
        db.session.add_all([q1_attempt, q2_attempt, q3_attempt, q4_attempt])

        self.assertCountEqual(u1.latest_next_attempts().all(), [(q1_attempt.question_id, date.today(), date.today()), 
                                                                (q2_attempt.question_id, date.today()+timedelta(days=1), date.today()+timedelta(days=1)), 
                                                                (q3_attempt.question_id, date.today()-timedelta(days=1), date.today()-timedelta(days=1))])

        # test that we successfully update a latest attempt by u1 reattempting q1
        q1_attempt2 = TextAttempt(response="Meow", user=u1, question=q1,
                                 next_attempt=date.today()+timedelta(days=1))
        self.assertCountEqual(u1.latest_next_attempts().all(), [(q1_attempt2.question_id, date.today()+timedelta(days=1), date.today()+timedelta(days=1)), 
                                                                (q2_attempt.question_id, date.today()+timedelta(days=1), date.today()+timedelta(days=1)), 
                                                                (q3_attempt.question_id, date.today()-timedelta(days=1), date.today()-timedelta(days=1))])

        
        
                
if __name__ == '__main__':
    unittest.main(verbosity=2)
