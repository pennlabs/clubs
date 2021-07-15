import ClubMetadata from 'components/ClubMetadata'
import { Container, Icon, Title } from 'components/common'
import { Field, Form, Formik } from 'formik'
import { NextPageContext } from 'next'
import React, { ReactElement, useState } from 'react'
import renderPage from 'renderPage'
import styled from 'styled-components'
import { ApplicationQuestionType, Club } from 'types'
import { doApiRequest } from 'utils'

import { TextField } from '~/components/FormComponents'

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
  word_limit: number
}

type ApplicationPageProps = {
  club: Club
  application: Application
  questions: ApplicationQuestion[]
  initialValues: any
}

const ErrorSpan = styled.span`
  position: relative;
  top: 0.5em;
  left: 1em;
`

const ApplicationPage = ({
  club,
  application,
  questions,
  initialValues,
}: ApplicationPageProps): ReactElement => {
  const [errors, setErrors] = useState<string | null>(null)

  function computeWordCount(input: string): number {
    return input.split(' ').filter((word) => word !== '').length
  }

  function formatQuestionType(
    props: any,
    question: ApplicationQuestion,
  ): JSX.Element {
    const [wordCount, setWordCount] = useState<number>(
      computeWordCount(initialValues[question.id]),
    )
    switch (question.question_type) {
      case ApplicationQuestionType.FreeResponse:
        return (
          <>
            <Field
              name={question.id}
              label={question.prompt}
              onInput={(event) => {
                setWordCount(computeWordCount(event.target.value))
              }}
              as={TextField}
              type={'textarea'}
              helpText={`Word count: ${wordCount}/${question.word_limit}`}
            />
          </>
        )
      case ApplicationQuestionType.MultipleChoice:
        return (
          <Field name={question.id} label={question.prompt} as={TextField} />
        )
      default:
        return (
          <Field name={question.id} label={question.prompt} as={TextField} />
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
          onSubmit={(values: { [id: number]: string }, actions) => {
            for (const [questionId, text] of Object.entries(values)) {
              const question = questions.find(
                (question: ApplicationQuestion) =>
                  question.id === parseInt(questionId),
              )
              if (
                question !== undefined &&
                computeWordCount(text) > question.word_limit
              ) {
                setErrors('One of your responses exceeds the word limit!')
              }
            }

            if (errors !== null) {
              for (const [questionId, text] of Object.entries(values)) {
                doApiRequest('/users/questions/?format=json', {
                  method: 'POST',
                  body: {
                    questionId,
                    text,
                  },
                })
              }
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
              {errors !== null && (
                <ErrorSpan className="has-text-danger">{errors}</ErrorSpan>
              )}
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
