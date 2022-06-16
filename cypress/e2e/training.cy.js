describe('Mission Training', function() {
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

  describe('Short Answer (Self-Graded)', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/question/short-answer', { 
        'author_id': this.instructorUser.id,
        'assessment_id': 4,
        'amount': 1
      })
    })

    /* 
     * Tests a self-graded short answer question, which is correctly answered and rated
     * as easy.
     */
    it('Correct Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
      respondToQuestionCorrectly(this.testCourse.name, 'This is DEFINITELY correct. So simple!', 'Easy', false)
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Congratulations")
    })

    it('IDK Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("I Don't Know").click()

      cy.contains("Incorrect Answer")
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })

    /* 
     * Simulate a challenging short answer question that results in an incorrect
     * answer followed by a retry.
     */
    it('Incorrect Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // Enter an 'incorrect' answer
      cy.get('textarea[name=response]').type("This isn't correct")
      cy.get('input[name=submit]').click()

      // check that they are on the page where they say whether their answer was
      // correct and select "No"
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/short-answer`)
      cy.get('input[name=no]').click()

      // Should be back at the main training page with the same question ready
      // to repeat
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })
  })

  describe('Short Answer (Auto-Graded)', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/question/auto-check', { 
        'author_id': this.instructorUser.id,
        'assessment_id': 4,
        'amount': 1
      })
        .its('body')
        .then(questions => { return questions[0]; })
        .as('currentQuestion')
    })

    /* 
     * Tests a self-graded short answer question, which is correctly answered and rated
     * as easy.
     */
    it('Correct Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
      cy.get('input[name=response]').type(`${this.currentQuestion.answer}`)
      cy.get('input[name=submit]').click()

      // check that they are on the page where they rate their performance
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/auto-check`)

      cy.contains('Easy').click()
      cy.get('input[name=submit]').click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Congratulations")
    })

    // TODO: Test for IDK response to Auto Check question

    /*
     * Tests an incorrect response to the auto-graded question.
     */
    it('Incorrect Answer', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // Note: by design, the random answer will always be a positive number
      // so -1 will always be incorrect
      cy.get('input[name=response]').type("-1")
      cy.get('input[name=submit]').click()

      // check that "Incorrect Answer" appears
      cy.contains("Incorrect Answer")
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })
  })

  describe('Multiple Choice', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/question/multiple-choice', { 
        'author_id': this.instructorUser.id,
        'assessment_id': 4,
        'amount': 1
      })

    })

    /* 
     * Tests a multiple choice question, which is correctly answered and rated
     * as easy.
     */
    it('Correct Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
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
     * Tests an incorrect response to a multiple choice question.
     */
    it('Incorrect Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      cy.contains("Bad answer").click()
      cy.get('input[name=submit]').click()

      // check that "Incorrect Answer" appears
      cy.contains("Incorrect Answer")
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })

    /*
     * Tests a response of "I Don't Know"
     */
    it('IDK Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      cy.contains("I Don't Know").click()
      cy.get('input[name=submit]').click()

      // check that "Incorrect Answer" appears
      cy.contains("Incorrect Answer")
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })
  })


})

