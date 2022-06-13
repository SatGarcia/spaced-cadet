import unittest
from app import create_app, db
from app.db_models import Course, Assessment
from datetime import date, timedelta, datetime

class CourseModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('config.TestConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # create a test course that is a week long to give room to test assessments that will be added to this course
        self.c = Course(name="test-course1", title="Test Course 1", description="",
                    start_date=(date.today()-timedelta(days=3)),
                    end_date=(date.today()+timedelta(days=3)))
        
        db.session.add(self.c)
        db.session.commit()

        self.a1 = Assessment(title="Test assessment1", time = datetime.now()-timedelta(days=2))  # assessment occurs during course, before current date
        self.a2 = Assessment(title="Test assessment2", time = datetime.now()-timedelta(hours=1)) # assessment occurs during course, today (an hour before this moment)
        self.a3 = Assessment(title="Test assessment3", time = datetime.now())                    # assessment occurs during course, today (right at this moment)
        self.a4 = Assessment(title="Test assessment4", time = datetime.now()+timedelta(hours=1)) # assessment occurs during course, today (an hour after this moment)
        self.a5 = Assessment(title="Test assessment5", time = datetime.now()+timedelta(days=2))  # assessment occurs during course, after current date


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


    def test_upcoming_assessments(self):
        # test: if no assessments are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.upcoming_assessments(), []) 

        # add assessments within the course all with differing times. a4 and a5 should be upcoming because they haven't occurred yet
        self.c.assessments.append(self.a5)
        self.c.assessments.append(self.a4)
        self.c.assessments.append(self.a3)
        self.c.assessments.append(self.a2)
        self.c.assessments.append(self.a1)

        self.assertCountEqual(self.c.upcoming_assessments(), [self.a4,self.a5])


    def test_past_assessments(self):
        # test: if no assessments are added to the course yet, then none should be upcoming
        self.assertCountEqual(self.c.past_assessments(), []) 

        # add assessments within the course all with differing times. a1,a2,a3 should be past because they have already occurred 
        self.c.assessments.append(self.a5)
        self.c.assessments.append(self.a4)
        self.c.assessments.append(self.a3)
        self.c.assessments.append(self.a2)
        self.c.assessments.append(self.a1)

        self.assertCountEqual(self.c.past_assessments(), [self.a1, self.a2, self.a3])
        