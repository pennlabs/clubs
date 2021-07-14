import ClubMetadata from 'components/ClubMetadata'
import { Container, Icon, Title } from 'components/common'
import { Field, Form, Formik } from 'formik'
import { NextPageContext } from 'next'
import React, { ReactElement } from 'react'
import renderPage from 'renderPage'
import { ApplicationQuestionType, Club } from 'types'
import { doApiRequest } from 'utils'

import { RichTextField } from '~/components/FormComponents'

type Application = {
  name: string
  application_start_time: string
  application_end_time: string
  result_release_time: string
  external_url: string | null
}

type ApplicationQuestion = {
  id: number
  question_type: ApplicationQuestionType
  prompt: string
}

type ApplicationPageProps = {
  club: Club
  application: Application
  questions: ApplicationQuestion[]
  initialValues: any
}

const ApplicationPage = ({
  club,
  application,
  questions,
  initialValues,
}: ApplicationPageProps): ReactElement => {
  function formatQuestionType(
    props: any,
    question: ApplicationQuestion,
  ): JSX.Element {
    switch (question.question_type) {
      case ApplicationQuestionType.Text:
        return (
          <Field
            name={question.id}
            label={question.prompt}
            as={RichTextField}
          />
        )
      case ApplicationQuestionType.MultipleChoice:
        return (
          <Field
            name={question.id}
            label={question.prompt}
            as={RichTextField}
          />
        )
      default:
        return (
          <Field
            name={question.id}
            label={question.prompt}
            as={RichTextField}
          />
        )
    }
  }

  return (
    <>
      <ClubMetadata club={club} />
      <Container paddingTop>
        <div className="is-clearfix">
          <Title className="is-pulled-left">{application.name}</Title>
        </div>
        <hr />
        <Formik
          initialValues={initialValues}
          onSubmit={(values, actions) => {
            for (const [questionId, text] of Object.entries(values)) {
              doApiRequest('/users/questions/?format=json', {
                method: 'POST',
                body: {
                  questionId,
                  text,
                },
              })
            }
          }}
        >
          {(props) => (
            <Form onSubmit={props.handleSubmit}>
              {questions.map((question: ApplicationQuestion) => {
                const input = formatQuestionType(props, question)
                return (
                  <div>
                    {input}
                    <br></br>
                  </div>
                )
              })}
              <button type="submit" className="button is-primary">
                <Icon name="edit" alt="save" /> Submit
              </button>
              <br></br>
              <br></br>
              <small>
                Feel free to submit multiple times, only your most recent
                submissions will be shared with the club application reviewers.
              </small>
            </Form>
          )}
        </Formik>
      </Container>
    </>
  )
}

ApplicationPage.getInitialProps = async (
  ctx: NextPageContext,
): Promise<ApplicationPageProps> => {
  const { query, req } = ctx
  const data = {
    headers: req ? { cookie: req.headers.cookie } : undefined,
  }
  const [club, application, questions] = await Promise.all(
    [
      `/clubs/${query.club}/?format=json`,
      `/clubs/${query.club}/applications/${query.application}/?format=json`,
      `/clubs/${query.club}/applications/${query.application}/questions/?format=json`,
    ].map(async (url) => (await doApiRequest(url, data)).json()),
  )

  const initialValues = await questions
    .map((question) => {
      return [
        question.id,
        `/users/questions?format=json&prompt=${question.prompt}`,
      ]
    })
    .reduce(async (acc, params) => {
      const [id, url] = params
      const payload = await (await doApiRequest(url, data)).json()
      acc[id] = payload.text
      return acc
    }, {})

  return { club, application, questions, initialValues }
}

export default renderPage(ApplicationPage)
