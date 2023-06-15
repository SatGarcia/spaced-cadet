#!/bin/bash

SERVER_NAME=http://localhost:5000
USER_EMAIL=teacher@email.com
USER_PASSWORD=password123!

echo "Change the password for $USER_EMAIL to $USER_PASSWORD through the web interface and then press any key to continue..."
read junk

# clear out old session file and recreate it by logging in and then grabbing
# the CSRF token from the response to be inserted as a special header
# (X-CSRF-TOKEN) on every request.
http -h --session=./session.json POST $SERVER_NAME/api/login email=$USER_EMAIL password=$USER_PASSWORD

python3 setup-cookies.py session.json

# create a couple of fake courses
http --session=./session.json POST $SERVER_NAME/api/courses name=comp101-sp20 \
	title="Introduction to Stuff" \
	description="A nice, fake course." \
	start-date="2020-01-01" \
	end-date="2050-12-31"

http --session=./session.json POST $SERVER_NAME/api/courses name=comp102-sp21 \
	title="Advanced Stuff" \
	description="A mean, unreal course." \
	start-date="2021-01-01" \
	end-date="2040-12-31"

# create a new instructor and student
http --session=./session.json POST $SERVER_NAME/api/users email=comp102prof@email.com password=foobar last-name=Pants first-name=Smarty instructor=True
http --session=./session.json POST $SERVER_NAME/api/users email=student@email.com password=foobar last-name=Student first-name=Brianna

# add OG instructor (teacher@gmail.com) to first course
http --session=./session.json POST $SERVER_NAME/api/course/1/students ids:=[1]

# add OG instructor, other instructor, and student to second course
http --session=./session.json POST $SERVER_NAME/api/course/2/students ids:=[1,2,3]

# create a textbook
http --session=./session.json POST $SERVER_NAME/api/textbooks title="Basic Stuff for Students" authors="Kuhl et al" url="https://fakebook.sucks/"

# add the textbook to the first course (comp101)
http --session=./session.json POST $SERVER_NAME/api/course/1/textbooks ids:=[1]

# add a new textbook section
http --session=./session.json POST $SERVER_NAME/api/textbook/1/sections title="Hula Hooping" number="1.1"

# create topics (global, not class specific)
http --session=./session.json POST $SERVER_NAME/api/topics text="hula hoops"
http --session=./session.json POST $SERVER_NAME/api/topics text="exercise"

# add both topics to the textbook section
http --session=./session.json POST $SERVER_NAME/api/source/1/topics ids:=[1,2]

# list students and textbooks for
http --session=./session.json GET $SERVER_NAME/api/course/1/students
http --session=./session.json GET $SERVER_NAME/api/course/1/textbooks
