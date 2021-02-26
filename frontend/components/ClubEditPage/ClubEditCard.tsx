import { Field, Form, Formik } from 'formik'
import Link from 'next/link'
import { ReactElement, useState } from 'react'

import { BLACK } from '../../constants'
import {
  Club,
  ClubApplicationRequired,
  ClubRecruitingCycle,
  ClubSize,
  Major,
  MembershipRank,
  School,
  StudentType,
  Tag,
  Year,
} from '../../types'
import { doApiRequest, formatResponse, isClubFieldShown } from '../../utils'
import {
  APPROVAL_AUTHORITY,
  FIELD_PARTICIPATION_LABEL,
  FORM_DESCRIPTION_EXAMPLES,
  FORM_LOGO_DESCRIPTION,
  FORM_TAG_DESCRIPTION,
  FORM_TARGET_DESCRIPTION,
  MEMBERSHIP_ROLE_NAMES,
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE_SINGULAR,
  OBJECT_TAB_ADMISSION_LABEL,
  SHOW_RANK_ALGORITHM,
  SITE_ID,
  SITE_NAME,
} from '../../utils/branding'
import { Checkbox, CheckboxLabel, Contact, Text } from '../common'
import {
  CheckboxField,
  FileField,
  FormikAddressField,
  FormStyle,
  RichTextField,
  SelectField,
  TextField,
} from '../FormComponents'
import { doFormikInitialValueFixes } from '../ModelForm'

export const CLUB_APPLICATIONS = [
  {
    value: ClubApplicationRequired.Open,
    label: 'Open Membership',
  },
  {
    value: ClubApplicationRequired.Tryout,
    label: 'Tryout Required',
  },
  {
    value: ClubApplicationRequired.Audition,
    label: 'Audition Required',
  },
  {
    value: ClubApplicationRequired.Application,
    label: 'Application Required',
  },
  {
    value: ClubApplicationRequired.ApplicationAndInterview,
    label: 'Application and Interview Required',
  },
]

export const CLUB_RECRUITMENT_CYCLES = [
  {
    value: ClubRecruitingCycle.Unknown,
    label: 'Unknown',
  },
  {
    value: ClubRecruitingCycle.Fall,
    label: 'Fall Semester',
  },
  {
    value: ClubRecruitingCycle.Spring,
    label: 'Spring Semester',
  },
  {
    value: ClubRecruitingCycle.Both,
    label: 'Both Semesters',
  },
  {
    value: ClubRecruitingCycle.Open,
    label: 'Open',
  },
]

const CLUB_SIZES = [
  {
    value: ClubSize.Small,
    label: '< 20',
  },
  {
    value: ClubSize.Medium,
    label: '21-50',
  },
  {
    value: ClubSize.Large,
    label: '51-100',
  },
  {
    value: ClubSize.VeryLarge,
    label: '> 100',
  },
]

type ClubEditCardProps = {
  schools: Readonly<School[]>
  majors: Readonly<Major[]>
  studentTypes: Readonly<StudentType[]>
  years: Readonly<Year[]>
  tags: Readonly<Tag[]>
  club: Partial<Club>
  isEdit: boolean
  onSubmit?: (data: {
    message: ReactElement | string | null
    club?: Club
    isEdit?: boolean
  }) => Promise<void>
}

const Card = ({
  title,
  children,
}: React.PropsWithChildren<{
  title?: string | ReactElement
}>): ReactElement => {
  return (
    <div className="card mb-5">
      <div className="card-header">
        <div className="card-header-title">{title}</div>
      </div>
      <div className="card-content">{children}</div>
    </div>
  )
}

/**
 * Remove fields in an object that are not part of a whitelist.
 *
 * Accounts for how some fields have _url appended as a suffix and allows these fields through.
 */
const removeNonFieldAttributes = (
  object: { [key: string]: any },
  validFields: Set<string>,
): { [key: string]: any } => {
  return Object.entries(object).reduce((acc, [key, value]) => {
    if (
      validFields.has(key) ||
      (key.endsWith('_url') && validFields.has(key.substr(0, key.length - 4)))
    ) {
      acc[key] = value
    }
    return acc
  }, {})
}

/**
 * A card that can show and edit the basic properties of a Club object.
 *
 * Consists of a group of cards, with each card representing a subset of fields on the Club object grouped by category.
 */
export default function ClubEditCard({
  schools,
  majors,
  studentTypes,
  years,
  tags,
  club,
  isEdit,
  onSubmit = () => Promise.resolve(undefined),
}: ClubEditCardProps): ReactElement {
  const [showTargetFields, setShowTargetFields] = useState<boolean>(
    !!(
      club.target_majors?.length ||
      club.target_schools?.length ||
      club.target_years?.length ||
      club.student_types?.length
    ),
  )

  const submit = (data, { setSubmitting, setStatus }): Promise<void> => {
    const photo = data.image
    if (photo !== null) {
      delete data.image
    }

    const req =
      isEdit && club !== null
        ? doApiRequest(`/clubs/${club.code}/?format=json`, {
            method: 'PATCH',
            body: data,
          })
        : doApiRequest('/clubs/?format=json', {
            method: 'POST',
            body: data,
          })

    return req.then((resp) => {
      if (resp.ok) {
        return resp.json().then((info) => {
          let clubCode: string | null = null
          if (!isEdit) {
            clubCode = info.code
          } else {
            clubCode = club?.code ?? null
          }

          let msg = isEdit
            ? `${OBJECT_NAME_TITLE_SINGULAR} has been successfully saved.`
            : `${OBJECT_NAME_TITLE_SINGULAR} has been successfully created.`

          const finishUpload = async () => {
            if (photo && photo instanceof File) {
              const formData = new FormData()
              formData.append('file', photo)
              const resp = await doApiRequest(
                `/clubs/${clubCode}/upload/?format=json`,
                {
                  method: 'POST',
                  body: formData,
                },
              )
              if (resp.ok) {
                msg += ` ${OBJECT_NAME_TITLE_SINGULAR} image also saved.`
                const { url } = await resp.json()
                info.image_url = url
              } else {
                msg += ` However, failed to upload ${OBJECT_NAME_SINGULAR} image file!`
              }
            }
            await onSubmit({ isEdit: true, club: info, message: msg })
            setStatus({})
            setSubmitting(false)
          }
          return finishUpload()
        })
      } else {
        return resp.json().then(async (err) => {
          await onSubmit({ message: formatResponse(err) })
          setStatus(err)
          setSubmitting(false)
        })
      }
    })
  }

  const fields = [
    {
      name: 'General',
      type: 'group',
      fields: [
        {
          name: 'name',
          type: 'text',
          required: true,
          label: `${OBJECT_NAME_TITLE_SINGULAR} Name`,
          help: isEdit ? (
            <>
              If you would like to change your {OBJECT_NAME_SINGULAR} URL in
              addition to your {OBJECT_NAME_SINGULAR} name, you will need to
              email <Contact />. Changing this field will require reapproval
              from the {APPROVAL_AUTHORITY}.
            </>
          ) : (
            <>
              Your {OBJECT_NAME_SINGULAR} URL will be generated from your{' '}
              {OBJECT_NAME_SINGULAR} name, and cannot be changed upon creation.
              Your {OBJECT_NAME_SINGULAR} name can still be changed afterwards.
              (Ex: {FORM_DESCRIPTION_EXAMPLES})
            </>
          ),
        },
        {
          name: 'subtitle',
          type: 'text',
          placeholder: 'Your Subtitle Here',
          label: `${OBJECT_NAME_TITLE_SINGULAR} Subtitle`,
          help: `This text will be shown next to your ${OBJECT_NAME_SINGULAR} name in list and card views. Enter a one sentence description of your ${OBJECT_NAME_SINGULAR}.`,
        },
        {
          name: 'terms',
          type: 'text',
          label: 'Alt Names',
          help: `Enter alternative names for your ${OBJECT_NAME_SINGULAR} here, separated by commas. For example, this could be an acronym or abbreviation that your ${OBJECT_NAME_SINGULAR} goes by. Your ${OBJECT_NAME_SINGULAR} will show up when these terms are entered into the search bar.`,
        },
        {
          name: 'description',
          required: true,
          help: `Changing this field will require reapproval from the ${APPROVAL_AUTHORITY}.`,
          placeholder: `Type your ${OBJECT_NAME_SINGULAR} description here!`,
          type: 'html',
        },
        {
          name: 'mission',
          required: true,
          help: `Changing this field will require reapproval from the ${APPROVAL_AUTHORITY}.`,
          placeholder: `Enter your ${OBJECT_NAME_SINGULAR} Mission here!`,
          type: 'html',
        },
        {
          name: 'tags',
          type: 'multiselect',
          required: true,
          help: `${FORM_TAG_DESCRIPTION}`,
          placeholder: `Select tags relevant to your ${OBJECT_NAME_SINGULAR}!`,
          choices: tags,
        },
        {
          name: 'image',
          help: `${FORM_LOGO_DESCRIPTION}`,
          accept: 'image/*',
          type: 'image',
          label: `${OBJECT_NAME_TITLE_SINGULAR} Logo`,
        },
        {
          name: 'size',
          type: 'select',
          required: true,
          choices: CLUB_SIZES,
          valueDeserialize: (a) => CLUB_SIZES.find((x) => x.value === a),
          serialize: (a) => a.value,
        },
        {
          name: 'founded',
          type: 'date',
          label: 'Date Founded',
        },
      ].filter(({ name }) => isClubFieldShown(name)),
    },
    {
      name: 'Contact',
      type: 'group',
      description: (
        <Text>
          Contact information entered here will be shown{' '}
          <strong>on your {OBJECT_NAME_SINGULAR} page</strong>.
        </Text>
      ),
      fields: [
        {
          name: 'address',
          label: 'Location',
          required: false,
          type: 'location',
          help:
            'Remember, this will be available to the public. Please only include information you feel comfortable sharing.',
        },
        {
          name: 'email',
          required: true,
          type: 'email',
          help:
            SITE_ID === 'fyh'
              ? `This can be a specific or general email that will serve as the main point of contact for ${SITE_NAME} users. The email associated with the owner of this resource page will be used by ${SITE_NAME} administrators as a point of contact for resource management and renewal.`
              : `Along with your ${OBJECT_NAME_SINGULAR} ${
                  MEMBERSHIP_ROLE_NAMES[MembershipRank.Officer]
                }s, this email will receive important notifications from ${SITE_NAME}. It will also be shown on your ${OBJECT_NAME_SINGULAR} page unless otherwise specified.`,
        },
        {
          name: 'email_public',
          type: 'checkbox',
          label: `Show this contact email to the public. If you do not check this box, your contact email will only be visible to internal ${OBJECT_NAME_SINGULAR} members.`,
        },
        {
          name: 'website',
          type: 'url',
        },
        {
          name: 'facebook',
          type: 'url',
        },
        {
          name: 'twitter',
          type: 'url',
        },
        {
          name: 'instagram',
          type: 'url',
        },
        {
          name: 'linkedin',
          type: 'url',
        },
        {
          name: 'github',
          type: 'url',
        },
        {
          name: 'youtube',
          type: 'url',
        },
        {
          name: 'listserv',
          type: 'text',
        },
      ].filter(({ name }) => isClubFieldShown(name)),
    },
    {
      name: OBJECT_TAB_ADMISSION_LABEL,
      type: 'group',
      description: SHOW_RANK_ALGORITHM ? (
        <Text>
          Some of these fields will be used to adjust {OBJECT_NAME_SINGULAR}{' '}
          ordering on the home page. Click{' '}
          <Link href="/rank">
            <a>here</a>
          </Link>{' '}
          for more details.
        </Text>
      ) : (
        <Text>
          This information will help students learn more about your{' '}
          {OBJECT_NAME_SINGULAR}.
        </Text>
      ),
      fields: [
        {
          name: 'application_required',
          label: `What is the membership process to join your ${OBJECT_NAME_SINGULAR}?`,
          required: true,
          type: 'select',
          choices: CLUB_APPLICATIONS,
          valueDeserialize: (a) => CLUB_APPLICATIONS.find((x) => x.value === a),
          serialize: (a) => a.value,
        },
        {
          name: 'recruiting_cycle',
          label: `When do you recruit your members?`,
          required: true,
          type: 'select',
          choices: CLUB_RECRUITMENT_CYCLES,
          valueDeserialize: (a) =>
            CLUB_RECRUITMENT_CYCLES.find((x) => x.value === a),
          serialize: (a) => a.value,
        },
        {
          name: 'accepting_members',
          label: 'Are you currently accepting applications at this time?',
          type: 'checkbox',
        },
        {
          name: 'available_virtually',
          label: `Is your ${OBJECT_NAME_SINGULAR} available virtually?`,
          type: 'checkbox',
        },
        {
          name: 'appointment_needed',
          label: `Is an appointment necessary to interact with your ${OBJECT_NAME_SINGULAR}?`,
          type: 'checkbox',
        },
        {
          name: 'how_to_get_involved',
          label: FIELD_PARTICIPATION_LABEL,
          type: 'html',
        },
        {
          name: 'signature_events',
          label: 'Signature Events',
          type: 'html',
        },
        {
          type: 'content',
          content: (
            <>
              <Text>{FORM_TARGET_DESCRIPTION}</Text>
              <div className="ml-2 mb-4">
                <CheckboxLabel>
                  <Checkbox
                    checked={showTargetFields}
                    onChange={(e) => setShowTargetFields(e.target.checked)}
                    color={BLACK}
                  />{' '}
                  <span className="ml-1">
                    Yes, my {OBJECT_NAME_SINGULAR} is restricted to certain
                    student groups.
                  </span>
                </CheckboxLabel>
              </div>
            </>
          ),
        },
        {
          name: 'target_years',
          label: SITE_ID === 'fyh' ? 'Degree Type' : 'Target Years',
          type: 'multiselect',
          placeholder:
            SITE_ID === 'fyh'
              ? `Select degree type relevant to your ${OBJECT_NAME_SINGULAR}!`
              : `Select graduation years relevant to your ${OBJECT_NAME_SINGULAR}!`,
          choices: years,
          hidden: !showTargetFields,
        },
        {
          name: 'target_schools',
          type: 'multiselect',
          placeholder: `Select schools relevant to your ${OBJECT_NAME_SINGULAR}!`,
          choices: schools,
          hidden: !showTargetFields,
        },
        {
          name: 'target_majors',
          type: 'multiselect',
          placeholder: `Select majors relevant to your ${OBJECT_NAME_SINGULAR}!`,
          choices: majors,
          hidden: !showTargetFields,
        },
        {
          name: 'student_types',
          type: 'multiselect',
          placeholder: `Select student types relevant to your ${OBJECT_NAME_SINGULAR}!`,
          choices: studentTypes,
          hidden: !showTargetFields,
        },
      ].filter(({ name }) => name == null || isClubFieldShown(name)),
    },
  ]

  const creationDefaults = {
    subtitle: '',
    email_public: true,
    accepting_members: false,
    size: CLUB_SIZES[0].value,
    application_required: CLUB_APPLICATIONS[0].value,
    recruiting_cycle: CLUB_RECRUITMENT_CYCLES[0].value,
  }

  const editingFields = new Set<string>()
  fields.forEach(({ fields }) =>
    fields.forEach((args) => {
      if (args.name != null) {
        editingFields.add(args.name)
      }
    }),
  )

  const initialValues = Object.keys(club).length
    ? doFormikInitialValueFixes(removeNonFieldAttributes(club, editingFields))
    : creationDefaults

  return (
    <Formik initialValues={initialValues} onSubmit={submit} enableReinitialize>
      {({ dirty, isSubmitting }) => (
        <Form>
          <FormStyle isHorizontal>
            {fields.map(({ name, description, fields }, i) => {
              return (
                <Card title={name} key={i}>
                  {description}
                  {(fields as any[]).map(
                    (props: any, i): ReactElement | null => {
                      const { hidden, ...other } = props
                      if (hidden) {
                        return null
                      }
                      if (props.type === 'content') {
                        return <div key={i}>{props.content}</div>
                      }
                      if (other.help) {
                        other.helpText = other.help
                        delete other.help
                      }
                      if (props.type === 'select') {
                        other.isMulti = false
                      } else if (props.type === 'multiselect') {
                        other.isMulti = true
                      }
                      if (props.type === 'image') {
                        other.isImage = true
                        delete other.type
                      }

                      return (
                        <Field
                          key={i}
                          as={
                            {
                              checkbox: CheckboxField,
                              html: RichTextField,
                              multiselect: SelectField,
                              select: SelectField,
                              image: FileField,
                              address: FormikAddressField,
                            }[props.type] ?? TextField
                          }
                          {...other}
                        />
                      )
                    },
                  )}
                </Card>
              )
            })}
            <button
              disabled={!dirty || isSubmitting}
              type="submit"
              className="button is-primary is-large"
            >
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </FormStyle>
        </Form>
      )}
    </Formik>
  )
}
