import Link from 'next/link'
import { useRouter } from 'next/router'
import React, { ReactElement, useEffect, useState } from 'react'
import { toast, TypeOptions } from 'react-toastify'

import ApplicationsPage from '../components/ClubEditPage/ApplicationsPage'
import ClubEditCard from '../components/ClubEditPage/ClubEditCard'
import ClubManagementCard from '../components/ClubEditPage/ClubManagementCard'
import EventsCard from '../components/ClubEditPage/EventsCard'
import FilesCard from '../components/ClubEditPage/FilesCard'
import InviteCard from '../components/ClubEditPage/InviteCard'
import MemberExperiencesCard from '../components/ClubEditPage/MemberExperiencesCard'
import MembersCard from '../components/ClubEditPage/MembersCard'
import QRCodeCard from '../components/ClubEditPage/QRCodeCard'
import {
  CLUB_EDIT_ROUTE,
  CLUB_RENEW_ROUTE,
  CLUB_ROUTE,
  DIRECTORY_ROUTE,
  HOME_ROUTE,
} from '../constants/routes'
import {
  Club,
  Major,
  School,
  StudentType,
  Tag,
  VisitType,
  Year,
} from '../types'
import { apiCheckPermission, doApiRequest } from '../utils'
import {
  APPROVAL_AUTHORITY,
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE,
  OBJECT_NAME_TITLE_SINGULAR,
  OBJECT_TAB_MEMBERSHIP_LABEL,
  OBJECT_TAB_RECRUITMENT_LABEL,
  SHOW_APPLICATIONS,
  SHOW_MEMBERSHIP_REQUEST,
  SHOW_ORG_MANAGEMENT,
  SITE_NAME,
} from '../utils/branding'
import AdvisorCard from './ClubEditPage/AdvisorCard'
import AnalyticsCard from './ClubEditPage/AnalyticsCard'
import ApplicationsCard from './ClubEditPage/ApplicationsCard'
import ClubFairCard from './ClubEditPage/ClubFairCard'
import DeleteClubCard from './ClubEditPage/DeleteClubCard'
import EnableSubscriptionCard from './ClubEditPage/EnableSubscriptionCard'
import EventsImportCard from './ClubEditPage/EventsImportCard'
import PotentialMemberCard from './ClubEditPage/PotentialMemberCard'
import QuestionsCard from './ClubEditPage/QuestionsCard'
import RenewCard from './ClubEditPage/RenewCard'
import ClubMetadata from './ClubMetadata'
import {
  Contact,
  Container,
  Icon,
  InactiveTag,
  InfoPageTitle,
  Loading,
  Metadata,
} from './common'
import AuthPrompt from './common/AuthPrompt'
import { BrowserTabView } from './TabView'

type ClubFormProps = {
  clubId: string | undefined
  authenticated: boolean | null
  schools: School[]
  majors: Major[]
  years: Year[]
  tags: Tag[]
  studentTypes: StudentType[]
  tab?: string | null
}

const ClubForm = ({
  authenticated,
  schools,
  years,
  majors,
  tags,
  studentTypes,
  clubId,
  tab,
}: ClubFormProps): ReactElement => {
  const [club, setClub] = useState<Club | null>(null)
  const [isEdit, setIsEdit] = useState<boolean>(typeof clubId !== 'undefined')

  const router = useRouter()

  const notify = (
    msg: string | ReactElement,
    type: TypeOptions = 'info',
  ): void => {
    toast[type](msg)
  }

  const submit = async ({
    message,
    club,
    isEdit: isEditNew,
  }: {
    message: ReactElement | string | null
    club?: Club
    isEdit?: boolean
  }): Promise<void> => {
    if (typeof club !== 'undefined' && typeof isEditNew !== 'undefined') {
      if (!isEdit && isEditNew) {
        // if the club is not active, redirect to the renewal page instead of the edit page
        if (!club.active) {
          router.push(CLUB_RENEW_ROUTE(), CLUB_RENEW_ROUTE(club.code))
          notify(`${message} Redirecting you to the renewal page...`, 'success')
          return Promise.resolve(undefined)
        } else {
          router.push(CLUB_EDIT_ROUTE(), CLUB_EDIT_ROUTE(club.code), {
            shallow: true,
          })
        }
      }
      setClub(club)
      if (isEdit !== isEditNew) {
        setIsEdit(isEditNew)
      }
    }
    if (message) {
      notify(
        club != null ? (
          message
        ) : (
          <>
            <div>
              You must fix the following errors before saving your{' '}
              {OBJECT_NAME_SINGULAR}:
            </div>
            {message}
          </>
        ),
        club != null ? 'success' : 'error',
      )
    }
  }

  const reloadClub = (): void => {
    if (isEdit) {
      const actualClubId = club !== null && club.code ? club.code : clubId
      doApiRequest(`/clubs/${actualClubId}/?format=json`)
        .then((resp) => resp.json())
        .then((data) => setClub(data))
    }
  }

  useEffect(reloadClub, [])

  useEffect(() => {
    if (club != null) {
      doApiRequest('/clubvisits/?format=json', {
        method: 'POST',
        body: {
          club: club.code,
          visit_type: VisitType.ManagePage,
        },
      })
    }
  }, [club])

  let metadata
  if (club) {
    metadata = <ClubMetadata club={club} />
  } else {
    metadata = <Metadata title={`Create ${OBJECT_NAME_TITLE_SINGULAR}`} />
  }

  const canManageClub = apiCheckPermission(
    `clubs.manage_club:${club?.code ?? clubId}`,
    true,
  )

  if (authenticated === false) {
    return <AuthPrompt>{metadata}</AuthPrompt>
  }

  if (authenticated === null || (isEdit && club === null)) {
    return <Loading />
  }

  if (isEdit && (!club || !club.code)) {
    return (
      <div className="has-text-centered" style={{ margin: 30 }}>
        <div className="title is-h1">404 Not Found</div>
        <p>
          The {OBJECT_NAME_SINGULAR} you are looking for does not exist. Perhaps{' '}
          it was recently moved or deleted?
        </p>
        <p>
          If you believe this is an error, please contact <Contact />.
        </p>
      </div>
    )
  }

  if (authenticated && isEdit && !canManageClub) {
    return (
      <AuthPrompt title="Oh no!" hasLogin={false}>
        {metadata}
        You do not have permission to edit the page for{' '}
        {(club && club.name) || `this ${OBJECT_NAME_SINGULAR}`}. To get access,{' '}
        contact <Contact />.
      </AuthPrompt>
    )
  }

  let tabs: {
    name: string
    label: string
    content: ReactElement
    disabled?: boolean
  }[] = []

  if (club && club.code) {
    tabs = [
      {
        name: 'info',
        label: `Edit ${OBJECT_NAME_TITLE_SINGULAR} Page`,
        content: (
          <ClubEditCard
            isEdit={isEdit}
            schools={schools}
            years={years}
            majors={majors}
            tags={tags}
            studentTypes={studentTypes}
            club={club}
            onSubmit={submit}
          />
        ),
      },
      {
        name: 'member',
        label: OBJECT_TAB_MEMBERSHIP_LABEL,
        content: (
          <>
            <InviteCard club={club} />
            {SHOW_MEMBERSHIP_REQUEST && (
              <PotentialMemberCard
                club={club}
                source="membershiprequests"
                actions={[
                  {
                    name: 'Accept',
                    icon: 'check',
                    onClick: async (id: string): Promise<void> => {
                      await doApiRequest(
                        `/clubs/${club.code}/membershiprequests/${id}/accept/?format=json`,
                        { method: 'POST' },
                      )
                    },
                  },
                  {
                    name: 'Delete',
                    className: 'is-danger',
                    icon: 'trash',
                    onClick: async (id: string): Promise<void> => {
                      await doApiRequest(
                        `/clubs/${club.code}/membershiprequests/${id}/?format=json`,
                        { method: 'DELETE' },
                      )
                    },
                  },
                ]}
              />
            )}
            <MembersCard club={club} />
            <AdvisorCard club={club} />
          </>
        ),
        disabled: !isEdit,
      },
      {
        name: 'events',
        label: 'Events',
        content: (
          <>
            <EventsImportCard club={club} />
            <EventsCard club={club} />
          </>
        ),
      },
      {
        name: 'recruitment',
        label: OBJECT_TAB_RECRUITMENT_LABEL,
        content: (
          <>
            {SHOW_APPLICATIONS && <ApplicationsCard club={club} />}
            <QRCodeCard club={club} />
            <EnableSubscriptionCard
              notify={notify}
              club={club}
              onUpdate={reloadClub}
            />
            {club.enables_subscription && (
              <PotentialMemberCard
                header={
                  <p className="mb-5">
                    The table below shows all the users that have subscribed (
                    <Icon name="bell" />) to your {OBJECT_NAME_SINGULAR}. If
                    users have elected to share their bookmarks (
                    <Icon name="bookmark" />) with {OBJECT_NAME_SINGULAR}{' '}
                    officers, they will also show up in the list below.
                  </p>
                }
                club={club}
                source="subscription"
              />
            )}
          </>
        ),
      },
      {
        name: 'applications',
        label: `Applications Page`,
        content: (
          <ApplicationsPage
            isEdit={isEdit}
            schools={schools}
            years={years}
            majors={majors}
            tags={tags}
            studentTypes={studentTypes}
            club={club}
            onSubmit={submit}
          />
        ),
      },
      {
        name: 'resources',
        label: 'Resources',
        content: (
          <>
            <MemberExperiencesCard club={club} />
            <FilesCard club={club} />
          </>
        ),
      },
      {
        name: 'questions',
        label: 'Questions',
        content: <QuestionsCard club={club} />,
      },
      {
        name: 'settings',
        label: 'Settings',
        content: (
          <>
            <RenewCard club={club} />
            <ClubFairCard club={club} />
            <DeleteClubCard onDelete={reloadClub} notify={notify} club={club} />
          </>
        ),
        disabled: !isEdit,
      },
      {
        name: 'analytics',
        label: 'Analytics',
        content: (
          <>
            <AnalyticsCard club={club} />
          </>
        ),
      },
      {
        name: 'organization',
        label: `${OBJECT_NAME_TITLE_SINGULAR} Management`,
        content: (
          <>
            <ClubManagementCard club={club} />
          </>
        ),
        disabled: !SHOW_ORG_MANAGEMENT,
      },
    ]
  }

  const nameOrDefault =
    (club && club.name) || `New ${OBJECT_NAME_TITLE_SINGULAR}`
  const showInactiveTag = !(club && club.active) && isEdit

  const isViewButton = isEdit && club

  return (
    <Container>
      {metadata}
      <InfoPageTitle>
        {nameOrDefault}
        {showInactiveTag && <InactiveTag />}
        {
          <Link
            href={isViewButton ? CLUB_ROUTE() : HOME_ROUTE}
            as={isViewButton && club ? CLUB_ROUTE(club.code) : HOME_ROUTE}
          >
            <a
              className="button is-pulled-right is-secondary is-medium"
              style={{ fontWeight: 'normal' }}
            >
              {isViewButton ? `View ${OBJECT_NAME_TITLE_SINGULAR}` : 'Back'}
            </a>
          </Link>
        }
      </InfoPageTitle>
      {!isEdit && (
        <>
          <p className="mb-3">
            {OBJECT_NAME_TITLE} that you create from this form will enter an
            approval process before being displayed to the public. After your{' '}
            {OBJECT_NAME_SINGULAR} has been approved by the {APPROVAL_AUTHORITY}
            , it will appear on the {SITE_NAME} website.
          </p>
          <p>
            <b>Before creating your {OBJECT_NAME_SINGULAR},</b> please check to{' '}
            see if it already exists on the{' '}
            <Link href={DIRECTORY_ROUTE} as={DIRECTORY_ROUTE}>
              <a>directory page</a>
            </Link>
            . If your {OBJECT_NAME_SINGULAR} already exists, please email{' '}
            <Contact /> to gain access instead of filling out this form.
          </p>
        </>
      )}
      {isEdit ? (
        <BrowserTabView tabs={tabs} tab={tab} route={CLUB_EDIT_ROUTE(clubId)} />
      ) : (
        <div style={{ marginTop: '1em' }}>
          <ClubEditCard
            isEdit={isEdit}
            schools={schools}
            years={years}
            majors={majors}
            tags={tags}
            club={club === null ? {} : club}
            studentTypes={studentTypes}
            onSubmit={submit}
          />
        </div>
      )}
    </Container>
  )
}

export default ClubForm
