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
      cy.location('pathname').should('eq', `/c/${courseName}/mission/4/train/self-grade`)
      cy.get('input[name=yes]').click()

      // check that they are on the page where they rate their performance
      cy.location('pathname').should('eq', `/c/${courseName}/mission/4/train/rating`)

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

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
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
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/self-grade`)
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
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/rating`)

      cy.contains('Easy').click()
      cy.get('input[name=submit]').click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Congratulations")
    })

    /*
     * Tests a response of "I Don't Know"
     */
    it('IDK Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      cy.contains("I Don't Know").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })

    /*
     * Tests an incorrect response to the auto-graded question.
     */
    it('Incorrect Answer', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // Note: by design, the random answer will always be a positive number
      // so -1 will always be incorrect
      cy.get('input[name=response]').type("-1")
      cy.get('input[name=submit]').click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
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
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/rating`)
      cy.contains('Easy').click()
      cy.contains('Submit').click()

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

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
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

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })
  })

  describe('Multiple Selection', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/question/multiple-selection', { 
        'author_id': this.instructorUser.id,
        'assessment_id': 4,
        'amount': 1
      })
    })

    /* 
     * Tests a multiple selection question, which is correctly answered and rated
     * as easy.
     */
    it('Correct Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Good answer 1").click()
      cy.contains("Good answer 2").click()
      cy.get("input[name=submit]").click()

      // check that they are on the page where they rate their performance
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/rating`)

      cy.contains('Easy').click()
      cy.get('input[name=submit]').click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Congratulations")
    })

    /*
     * Tests an incorrect response to a multiple selection question.
     */
    it('Incorrect Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      cy.contains("Good answer 2").click()
      cy.contains("Good answer 1").click()
      cy.contains("Bad answer").click()
      cy.get('input[name=submit]').click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
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

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })
  })

  describe('Code Jumble', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/question/code-jumble', { 
        'author_id': this.instructorUser.id,
        'assessment_id': 4,
        'amount': 1
      })
    })

    function moveCodeBlock(lineContents, destinationId, destinationIndex) {
      const dataTransfer = new DataTransfer()

      cy.contains(lineContents)
        .trigger('dragstart', {dataTransfer})
      cy.get(`${destinationId}>li`).eq(destinationIndex)
        .trigger('drop', {dataTransfer})
      cy.contains(lineContents)
        .trigger('dragend', {dataTransfer})
    }

    /* 
     * Tests a code jumble question, which is correctly answered and rated
     * as easy.
     */
    it('Correct Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // move correct blocks into place
      moveCodeBlock('line 0', '#jumbley', 0);
      moveCodeBlock('line 1', '#jumbley', 1);
      moveCodeBlock('line 2', '#jumbley', 2);

      // move unused blocks into trash
      moveCodeBlock('trash 1', '#jumble-trash', 0);
      moveCodeBlock('trash 2', '#jumble-trash', 0);

      // indent the blocks
      cy.get("#jumbley>li").eq(1).find('.bi-arrow-right').click().click()

      // indent twice, but then remove indent
      cy.get("#jumbley>li").eq(2).find('.bi-arrow-right').click().click()
      cy.get("#jumbley>li").eq(2).find('.bi-arrow-left').click()

      // test that unindent doesn't do anything if there isn't any indentation
      cy.get("#jumbley>li").eq(0).find('.bi-arrow-left').click().click()

      cy.contains("Submit").click()

      // should be on rating page
      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/rating`)
      cy.contains("Easy").click()
      cy.contains("Submit").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Congratulations")
    })

    /*
     * Tests several incorrect attempts:
     * (1) Wrong blocks/order/indentation
     * (2) Correct blocks/order, bad indentation
     * (3) Correct blocks/indentation, bad ordering
     */
    it('Incorrect Attempts', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // Scenario 1 (wrong blocks/order/indentation)
      cy.contains("Submit").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")

      // Scenario 2 (bad indentation)
      // move correct blocks into place
      moveCodeBlock('line 0', '#jumbley', 0);
      moveCodeBlock('line 1', '#jumbley', 1);
      moveCodeBlock('line 2', '#jumbley', 2);

      // move unused blocks into trash
      moveCodeBlock('trash 1', '#jumble-trash', 0);
      moveCodeBlock('trash 2', '#jumble-trash', 0);

      cy.contains("Submit").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")

      // Scenario 3 (bad ordering)
      // move correct blocks into correct places (we'll undo this later)
      moveCodeBlock('line 0', '#jumbley', 0);
      moveCodeBlock('line 1', '#jumbley', 1);
      moveCodeBlock('line 2', '#jumbley', 2);

      // move unused blocks into trash
      moveCodeBlock('trash 1', '#jumble-trash', 0);
      moveCodeBlock('trash 2', '#jumble-trash', 0);

      // indent the blocks
      cy.get("#jumbley>li").eq(1).find('.bi-arrow-right').click().click()
      cy.get("#jumbley>li").eq(2).find('.bi-arrow-right').click()

      // move one block to the wrong spot
      moveCodeBlock('line 0', '#jumbley', 2);

      cy.contains("Submit").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })

    it('IDK Attempt', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("I Don't Know").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train/review`)
      cy.contains("Continue Training").click()

      cy.location('pathname').should('eq', `/c/${this.testCourse.name}/mission/4/train`)
      cy.contains("Repeat Question")
    })

  })

  describe('Completion Page Stats', function() {
    beforeEach(function() {
      cy.request('POST', '/test/seed/assessment', { 
        'assessment_id': 4,
        'num_objectives': 5,
        'questions_per_objective': 6,
      })
        .its('body')
        .as('currentAssessment')
    })

    it('Student Training Stats and Review', function () {
      cy.visit(`/c/${this.testCourse.name}/mission/4/train`)

      // check that there are three learning objectives listed
      cy.get("#objectivesToReview").find('li').should('have.length', 3)
      cy.get("#objectivesToReview").contains("View Questions").click()
    })
  })

})

