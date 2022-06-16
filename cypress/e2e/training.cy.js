describe('Mission Training', () => {
  beforeEach(() => {
    // reset and seed the database prior to every test
    cy.request('/test/reset_db')

    // create an instructor
    cy.request('POST', '/test/seed/user', { 
      instructor: true,
      email: 'instructor@cadet.com',
      password: 'testing',
      'first-name': 'Foo',
      'last-name': 'Instructor' })
      .its('body')
      .as('instructorUser')

    cy.request('POST', '/test/seed/course', {
      name: 'test-course',
      'instructor_email': 'instructor@cadet.com',
      'num_students': 5,
      'num_past_assessments': 2,
      'num_upcoming_assessments': 3})
      .its('body')
      .as('testCourse')
      .then(course => {
        return course.users.filter(u => u.email !== 'instructor@cadet.com')
      })
      .should('have.length', 5)
      .then(students => {
	    cy.login(students[0].email, 'testing')
      })
  })

  function respondToQuestionCorrectly(courseName, answer, difficulty, isRepeat) {
      cy.location('pathname').should('eq', `/c/${courseName}/mission/4/train`)
      if (isRepeat === true) {
        cy.contains("Repeat Question")
      }
      cy.get('textarea[name=response]').type(answer)
      cy.get('input[name=submit]').click()

      // confirm that they got it correct
      cy.location('pathname').should('eq', `/c/${courseName}/mission/4/train/short-answer`)
      cy.get('input[name=yes]').click()

      // check that they are on the page where they rate their performance
      cy.location('pathname').should('eq', `/c/${courseName}/mission/4/train/review`)

      cy.contains(difficulty).click()
      cy.get('input[name=submit]').click()
  }

  /* 
   * Tests a self-graded short answer question, which is correctly answered and rated
   * as easy.
   */
  it('Easy Short Answer Question', function () {
    cy.request('POST', '/test/seed/question/short-answer', { 
      'author_id': this.instructorUser.id,
      'assessment_id': 4,
      'amount': 1
    })

    cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
    respondToQuestionCorrectly(this.testCourse.name, 'This is DEFINITELY correct. So simple!', 'Easy', false)
    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
    cy.contains("Congratulations")
  })

  /* 
   * Tests a multiple choice question, which is correctly answered and rated
   * as easy.
   */
  it('Easy Multiple Choice Question', function () {
    cy.request('POST', '/test/seed/question/multiple-choice', { 
      'author_id': this.instructorUser.id,
      'assessment_id': 4,
      'amount': 1
    })

    cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
    cy.contains("MULTIPLE CHOICE")
    cy.contains("Good answer").click()
    cy.get("input[name=submit]").click()

    // check that they are on the page where they rate their performance
    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/multiple-choice`)

    cy.contains('Easy').click()
    cy.get('input[name=submit]').click()

    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
    cy.contains("Congratulations")
  })

  /* 
   * Simulate a challenging short answer question that results in an incorrect
   * answer followed by a retry.
   */
  it('Challenging Short Answer Question', function () {
    // create a short answer question
    cy.request('POST', '/test/seed/question/short-answer', { 
      'author_id': this.instructorUser.id,
      'assessment_id': 4,
      'amount': 1
    })

    cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

    // Enter an 'incorrect' answer
    cy.get('textarea[name=response]').type("This isn't correct")
    cy.get('input[name=submit]').click()

    // check that they are on the page where they say whether their answer was
    // correct and select "No"
    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/short-answer`)
    cy.get('input[name=no]').click()

    const responses = [{difficulty: 'Hard', answer: 'This is correct, I think'},
      {difficulty: 'Medium', answer: 'I am fairly confident that this is correct'}]

    responses.forEach(response => {
      // should be back on training page
      respondToQuestionCorrectly(this.testCourse.name, response.answer, response.difficulty, true)
    })

    cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
    cy.contains("Congratulations")
  })

})

