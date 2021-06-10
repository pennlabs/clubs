import ClubMetadata from 'components/ClubMetadata'
import { Container, Subtitle, Title } from 'components/common'
import { Formik } from 'formik'
import { NextPageContext } from 'next'
import React, { ReactElement } from 'react'
import renderPage from 'renderPage'
import { ApplicationQuestionType, Club } from 'types'
import { doApiRequest } from 'utils'

type Application = {
  name: string
  application_start_time: string
  application_end_time: string
  result_release_time: string
  external_url: string | null
}

type ApplicationQuestion = {
  question_type: ApplicationQuestionType
  prompt: string
}

type ApplicationPageProps = {
  club: Club
  application: Application
  questions: ApplicationQuestion[]
}

const ApplicationPage = ({
  club,
  application,
  questions,
}: ApplicationPageProps): ReactElement => {
  function formatQuestionType(
    props: any,
    questionType: ApplicationQuestionType,
  ): JSX.Element {
    switch (questionType) {
      case ApplicationQuestionType.Text:
        return <input type="text"></input>
      case ApplicationQuestionType.MultipleChoice:
        return <input type="text"></input>
      default:
        return (
          <input
            type="text"
            onChange={props.handleChange}
            onBlur={props.handleBlur}
            name="name"
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
          initialValues={{ name: 'jared' }}
          onSubmit={(values, actions) => {
            setTimeout(() => {
              alert(JSON.stringify(values, null, 2))
              actions.setSubmitting(false)
            }, 1000)
          }}
        >
          {(props) => (
            <form onSubmit={props.handleSubmit}>
              {questions.map((question: ApplicationQuestion) => {
                const input = formatQuestionType(props, question.question_type)
                return (
                  <div>
                    <br></br>
                    <Subtitle>{question.prompt}</Subtitle>
                    {input}
                  </div>
                )
              })}
              <button type="submit">Submit</button>
            </form>
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
  return { club, application, questions }
}

export default renderPage(ApplicationPage)
