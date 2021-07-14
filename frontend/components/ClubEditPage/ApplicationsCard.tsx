import { Field } from 'formik'
import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'

import {
  ApplicationQuestionType,
  Club,
  ClubApplicationRequired,
} from '../../types'
import {
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE_SINGULAR,
} from '../../utils/branding'
import { Icon, Modal, Text } from '../common'
import { DateTimeField, SelectField, TextField } from '../FormComponents'
import ModelForm from '../ModelForm'
import BaseCard from './BaseCard'

type Props = {
  club: Club
}
const QUESTION_TYPES = [
  {
    value: ApplicationQuestionType.Text,
    label: 'Text',
  },
  {
    value: ApplicationQuestionType.MultipleChoice,
    label: 'Multiple Choice',
  },
]

const ModalContainer = styled.div`
  text-align: left;
  padding: 20px;
`

const ApplicationModal = (props: {
  clubCode: string
  applicationName: string
  showDetailsButton?: boolean
  onLinkClicked?: () => void
}): ReactElement => {
  const { clubCode, applicationName, showDetailsButton, onLinkClicked } = props

  return (
    <ModalContainer>
      <ModelForm
        baseUrl={`/clubs/${clubCode}/applications/${applicationName}/questions/`}
        defaultObject={{ name: `${applicationName} Question` }}
        fields={
          <>
            <Field name="prompt" as={TextField} required={true} />
            <Field
              name="type"
              as={SelectField}
              choices={QUESTION_TYPES}
              required={true}
            />
          </>
        }
        tableFields={[
          { name: 'prompt', label: 'Prompt' },
          {
            name: 'type',
            label: 'Type',
          },
        ]}
        noun="Application"
      />
    </ModalContainer>
  )
}

export default function ApplicationsCard({ club }: Props): ReactElement {
  const [show, setShow] = useState(false)
  const showModal = () => setShow(true)
  const hideModal = () => setShow(false)
  const [applicationName, setApplicationName] = useState('')

  return (
    <BaseCard title={`${OBJECT_NAME_TITLE_SINGULAR} Applications`}>
      {club.application_required === ClubApplicationRequired.Open && (
        <div className="notification is-warning">
          <Icon name="alert-triangle" /> Your {OBJECT_NAME_SINGULAR} currently
          has it application status set to open membership. Adding{' '}
          {OBJECT_NAME_SINGULAR} applications here will have no effect on what
          the student sees.
        </div>
      )}
      <Text>
        You can use the interface below to add {OBJECT_NAME_SINGULAR}{' '}
        applications.
      </Text>
      <ul className="mb-3">
        {[
          <>
            Display your application links in a centralized repository of{' '}
            {OBJECT_NAME_SINGULAR} applications. While your{' '}
            {OBJECT_NAME_SINGULAR} has an open application, it will be
            prioritized in {OBJECT_NAME_SINGULAR} listings.
          </>,
          <>
            Subscribed students will automatically receive email reminders about
            application deadlines three days before the application is due.
          </>,
          <>
            Automatically update membership and recruiting statuses based on
            when your applications open and close. When your application opens,
            we will mark your {OBJECT_NAME_SINGULAR} as accepting members. When
            it closes, we will mark your {OBJECT_NAME_SINGULAR} as not accepting
            members.
          </>,
        ].map((text, i) => (
          <li key={i}>
            <span className=" ml-3 has-text-success">
              <Icon name="check" />
            </span>{' '}
            {text}
          </li>
        ))}
      </ul>
      <ModelForm
        baseUrl={`/clubs/${club.code}/applications/`}
        defaultObject={{ name: `${club.name} Application` }}
        fields={
          <>
            <Field
              name="name"
              as={TextField}
              helpText="A name for this application, used for identifying it if you have multiple applications per semester."
            />
            <Field
              name="application_start_time"
              as={DateTimeField}
              required={true}
              helpText="The date when your application opens."
            />
            <Field
              name="application_end_time"
              as={DateTimeField}
              required={true}
              helpText="The date when your application closes."
            />
            <Field
              name="result_release_time"
              as={DateTimeField}
              required={true}
              helpText={`The latest date that your ${OBJECT_NAME_SINGULAR} will be releasing admission results.`}
            />
            <Field
              name="external_url"
              as={TextField}
              type="url"
              required={true}
              helpText={`The external URL where students can apply for your ${OBJECT_NAME_SINGULAR}.`}
            />
          </>
        }
        tableFields={[
          { name: 'name', label: 'Name' },
          {
            name: 'id',
            label: 'Edit',
            render: (id) => {
              setApplicationName(id)
              return (
                <>
                  <button
                    className="button is-primary is-small"
                    onClick={showModal}
                  >
                    Questions
                  </button>
                  <a href={`/club/${club.code}/application/${id}`}>
                    <button className="button is-primary is-small ml-3">
                      Preview
                    </button>
                  </a>
                </>
              )
            },
          },
        ]}
        noun="Application"
      />
      {show && (
        <Modal
          show={show}
          closeModal={hideModal}
          width="80%"
          marginBottom={false}
        >
          <ApplicationModal
            clubCode={club.code}
            applicationName={applicationName}
            showDetailsButton={false}
          />
        </Modal>
      )}
    </BaseCard>
  )
}
