// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --

// Log in without using the UI
Cypress.Commands.add('login', (email, password) => {
    cy.request({
      url: '/auth/login',
      method: 'POST',
      form: true,
      body: {
        email: email,
        password: password
      },
	  followRedirect: false,
    }).then((resp) => {
	  // make sure we got a 302 redirect to the homepage
	  expect(resp.status).to.eq(302)
	  expect(resp.redirectedToUrl).to.eq(Cypress.config().baseUrl + '/')
    })

    // our auth cookie should be present
    cy.getCookie('access_token_cookie').should('exist')
})


//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })
