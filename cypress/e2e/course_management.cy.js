describe('Instructor Course Management', function() {
  beforeEach(() => {
    // reset and seed the database prior to every test
    cy.request('/test/reset_db')

    // seed a user in the DB that we can control from our tests
    cy.request('POST', '/test/seed/user', { 
      instructor: true,
      email: 'test@cadet.com',
      password: 'testing',
      'first-name': 'Foo',
      'last-name': 'Bar' })
      .its('body')
      .as('currentUser')

    cy.login('test@cadet.com', 'testing')
  })

  describe('Course Creation / Setup', function() {
    beforeEach(function() {
      // add some random topics (outside of any textbook)
      cy.request('POST', '/test/seed/topics', { 'amount': 5 })
        .its('body')
        .as('extraTopics')

      // create a random textbook
      cy.request('POST', '/test/seed/textbook', { 
        'num_sections': 5,
        'author_id': this.currentUser.id})
        .its('body')
        .as('textbook1')
    })

    it('Create New Course', function () {
      cy.visit('/')
      cy.contains("Courses").click()
      cy.contains("Create New Course").click()

      cy.location('pathname').should('eq', '/new-course')
      cy.get('input[name=name]').type("test-course1")
      cy.get('input[name=title]').type("Intro to Narwhals")
      cy.get('textarea[name=description]').type("A very interesting course")
      cy.get('input[name=start_date]').type('2021-01-03')
      cy.get('input[name=end_date]').type('2095-07-13')
      cy.contains("Create Course").click()

      // TODO: check URL to make sure we are at setup textbooks
      cy.get('input[id=textbookSearchBar]').type(`${this.textbook1.title}{enter}`)
      cy.contains('button', 'Add').click()
      cy.contains("Continue...").click()
      cy.contains("Next Step").click()

      // TODO: check url to make sure we are at setup topics
      cy.get('[data-cy=topicList]').as('sectionTopics')

      // Add all topics from first section and one from the third section
      cy.get('@sectionTopics').first().contains("Add All").click()
      cy.get('[data-cy=topicsPage]').children().should('have.length', 3)

      cy.contains(this.textbook1.sections[2].topics[1].text).click()
      cy.get('[data-cy=topicsPage]').children().should('have.length', 4)

      // remove one of the topics
      cy.get('[data-cy=topicsPage]').children().eq(1).contains("Remove").click()

      cy.contains("Search / Create").click()

      // search for non-existent topic and add it through here
      cy.get('#topicSearchBar').type("aaabbb{enter}")
      cy.contains("Create and Add Topic").click()
      cy.get("#courseTopics").should('contain', 'aaabbb')

      cy.get('#topicSearchBar').type(`{selectAll}{backspace}${this.extraTopics[0].text}{enter}`)
      cy.get('[data-cy=result0]').should('contain', this.extraTopics[0].text).find('button').click()

      cy.get('#courseTopics').should('contain', this.extraTopics[0].text)
      cy.contains("Continue...").click()
      cy.contains("Exit Course Setup").click()

      cy.location('pathname').should('eq', `/c/test-course1`)
    })
  })

  describe('Edit Course', function() {
    beforeEach(() => {
      cy.request('POST', '/test/seed/course', { 
        name: 'test-course',
        'instructor_email': 'test@cadet.com',
        'num_students': 5,
        'num_past_assessments': 2,
        'num_upcoming_assessments': 3})
        .its('body')
        .as('testCourse')
    })

    /*
    it('Course Overview Page', function () {
      cy.visit(`/c/${this.testCourse.name}`)

      cy.get('h3').should('contain', this.testCourse.title)

      cy.get('[id=instructorMenu]').contains('Manage Assessments')
      cy.get('[id=instructorMenu]').should('contain', 'Manage Roster')
      cy.get('[id=instructorMenu]').should('contain', 'Edit Settings')
      cy.get('[id=instructorMenu]').should('contain', 'Course Setup')
    })
    */

    it('Edit Course Settings Page', function () {
      cy.visit(`/c/${this.testCourse.name}`)

      cy.get('[id=instructorMenu]').contains('Edit Settings').click()

      cy.contains("Edit Course Settings")

      cy.get('input[name=title]').clear().type('Zippy Course Title')
      cy.get('textarea[name=description]').clear().type('A shiny new course description')
      cy.get('input[name=start_date]').type('2021-01-15')
      cy.get('input[name=submit]').click()
      cy.url().should('contain', '/c/test-course')
      cy.get('h3').should('contain', 'Zippy Course Title')
      cy.contains('A shiny new course description')
    })

    it('Manage Roster', function () {
      cy.visit(`/c/${this.testCourse.name}`)

      cy.get('[id=instructorMenu]').contains('Manage Roster').click()

      cy.contains(`Manage Roster (${this.testCourse.name})`)

      // Check that all the students appear
      for (const user of this.testCourse.users) {
        cy.get('tr').contains(user.email)
      }

      const user_to_delete = this.testCourse.users[2]
      cy.get('tr').contains(user_to_delete.email).parent().contains('Remove').click()
      cy.get('table').contains(user_to_delete.email).should('not.exist')

      cy.get('input[type=file]').selectFile('cypress/fixtures/text_files/roster1.csv')
      cy.get('input[type=submit]').contains('Upload Roster').click()
      cy.get('tbody').contains('bradley@mockingbird.com')
      cy.get('tbody').contains('gravy@thanksgiving.org')

      // upload another roster file with column names that don't auto populate
      // correctly, using the add/drop option to remove all students not in the
      // file
      cy.get('input[type=file]').selectFile('cypress/fixtures/text_files/roster2.csv')
      cy.get('select[name=email_index]').select('Correo')
      cy.get('select[name=last_name_index]').select('Surname')
      cy.get('select[name=first_name_index]').select('Primary Name')
      cy.get('input[name=add_drop]').check()
      cy.get('input[type=submit]').contains('Upload Roster').click()

      // check flash messages
      cy.contains("Removed 5 students")
      cy.contains("Added 2 new students")
      cy.contains("Skipped 1 who were")

      // check contents of table
      cy.get('tbody').contains('bradley@mockingbird.com')
      cy.get('tbody').contains("chocolate@swiss.ch")
      cy.get('tbody').contains("Michael")
      cy.get('tbody').contains("Toblerone")
      cy.get('tbody').contains("gravey@thanksgiving.org").should('not.exist')

    })
  })
})

