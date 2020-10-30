import { useRouter } from 'next/router'
import { ReactElement, useState } from 'react'
import s from 'styled-components'

import { FAIR_INFO, MEDIUM_GRAY } from '../../constants'
import { Club, MembershipRank, UserInfo } from '../../types'
import { apiCheckPermission, doApiRequest, useSetting } from '../../utils'
import {
  APPROVAL_AUTHORITY,
  APPROVAL_AUTHORITY_URL,
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE_SINGULAR,
  SITE_NAME,
} from '../../utils/branding'
import { Contact, Icon, Modal, Text } from '../common'
import { ModalContent } from './Actions'

const ReviewQuote = s.span`
  white-space: pre-wrap;
  display: block;
  margin-top: 12px;
  margin-bottom: 5px;
  padding: 5px;
  padding-left: 12px;
  border-left: 3px solid ${MEDIUM_GRAY};
  color: ${MEDIUM_GRAY};
  font-size: 1.2em;

  .notification.is-info & {
    color: white;
    border-left-color: white;
  }
`

type Props = {
  club: Club
  userInfo: UserInfo
}

type ConfirmParams = {
  func: () => void
  message: ReactElement | string
}

const ClubApprovalDialog = ({ club, userInfo }: Props): ReactElement | null => {
  const router = useRouter()
  const year = new Date().getFullYear()
  const [comment, setComment] = useState<string>(club.approved_comment || '')
  const [loading, setLoading] = useState<boolean>(false)
  const [confirmModal, setConfirmModal] = useState<ConfirmParams | null>(null)
  const fairInProgress = useSetting('FAIR_OPEN') || useSetting('PRE_FAIR')
  const fairName = useSetting('FAIR_NAME')
  const fairInfo = FAIR_INFO[fairName as string]

  const canApprove = apiCheckPermission('clubs.approve_club')
  const seeFairStatus = apiCheckPermission('clubs.see_fair_status')
  const canDeleteClub = apiCheckPermission('clubs.delete_club')

  const doConfirm = (params: ConfirmParams): void => {
    setConfirmModal(params)
  }

  return (
    <>
      {confirmModal !== null && (
        <Modal
          show={true}
          closeModal={() => setConfirmModal(null)}
          marginBottom={false}
        >
          <ModalContent>
            <div className="mb-3">{confirmModal.message}</div>
            <button
              className="button is-danger"
              onClick={() => {
                confirmModal.func()
                setConfirmModal(null)
              }}
            >
              Confirm
            </button>
          </ModalContent>
        </Modal>
      )}
      {club.approved && canApprove && (
        <div className="notification is-info">
          <div className="mb-3">
            <b>{club.name}</b> has been approved by <b>{club.approved_by}</b>{' '}
            for the school year. If you want to revoke approval for this{' '}
            {OBJECT_NAME_SINGULAR}, use the button below.
          </div>
          {club.approved_comment && (
            <div className="mb-5">
              <ReviewQuote>{club.approved_comment}</ReviewQuote>
            </div>
          )}
          <button
            className="button is-info is-light"
            disabled={loading}
            onClick={() => {
              doConfirm({
                func: () => {
                  setLoading(true)
                  doApiRequest(`/clubs/${club.code}/?format=json`, {
                    method: 'PATCH',
                    body: {
                      approved: null,
                    },
                  })
                    .then(() => router.reload())
                    .finally(() => setLoading(false))
                },
                message: (
                  <>
                    Are you sure you would like to revoke approval for{' '}
                    <b>{club.name}</b>?
                  </>
                ),
              })
            }}
          >
            <Icon name="x" /> Revoke Approval
          </button>
        </div>
      )}
      {(club.active || canDeleteClub) && club.approved !== true ? (
        <div className="notification is-warning">
          <Text>
            {club.approved === false ? (
              <>
                <p>
                  This {OBJECT_NAME_SINGULAR} has been marked as{' '}
                  <b>not approved</b> and is only visible to administrators of{' '}
                  {SITE_NAME}. The reason that your {OBJECT_NAME_SINGULAR} was
                  not approved by the{' '}
                  <a href={APPROVAL_AUTHORITY_URL}>{APPROVAL_AUTHORITY}</a> is
                  listed below. If you believe that this is a mistake, contact{' '}
                  <Contact point="osa" />.
                </p>
                <ReviewQuote>
                  {club.approved_comment || (
                    <>
                      No reason has been given for why your{' '}
                      {OBJECT_NAME_SINGULAR} was not approved. Contact{' '}
                      <Contact point="osa" /> for more details.
                    </>
                  )}
                </ReviewQuote>
              </>
            ) : (
              <>
                {club.is_ghost
                  ? `Changes to this ${OBJECT_NAME_SINGULAR} have`
                  : `This ${OBJECT_NAME_SINGULAR} has`}{' '}
                <b>not been approved yet</b> for the {year}-{year + 1} school
                year and is only visible to {OBJECT_NAME_SINGULAR} members and
                administrators of {SITE_NAME}.
                {club.is_ghost && (
                  <span className="mt-3 is-block">
                    The latest approved version of this {OBJECT_NAME_SINGULAR}{' '}
                    will be shown in the meantime. When your changes have been
                    approved, your {OBJECT_NAME_SINGULAR} page will be updated.
                  </span>
                )}
              </>
            )}
          </Text>
          {(canApprove || canDeleteClub) && (
            <>
              {canApprove && club.active && (
                <>
                  <div className="mb-3">
                    As an administrator for {SITE_NAME}, you can approve or
                    reject this request. Approving this request will display it
                    publically on the {SITE_NAME} website and send out an email
                    notifying {OBJECT_NAME_SINGULAR} members that their{' '}
                    {OBJECT_NAME_SINGULAR} has been renewed. Rejecting this
                    request will send out an email notifying{' '}
                    {OBJECT_NAME_SINGULAR} members that their{' '}
                    {OBJECT_NAME_SINGULAR} was not approved and include
                    instructions on how to request approval again.
                  </div>
                  {club.files.length ? (
                    <div className="mb-3">
                      <b>Club Files:</b>
                      <ul>
                        {club.files.map(({ name, file_url }, i) => (
                          <li key={i}>
                            <a target="_blank" href={file_url}>
                              {name}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="mb-3">
                      This {OBJECT_NAME_SINGULAR} has not uploaded any files.
                    </div>
                  )}
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className="textarea mb-4"
                    placeholder="Enter approval or rejection notes here! Your notes will be emailed to the requester when you approve or reject this request."
                  ></textarea>
                </>
              )}
              <div className="buttons">
                {canApprove && club.active && (
                  <>
                    <button
                      className="button is-success"
                      disabled={loading}
                      onClick={() => {
                        setLoading(true)
                        doApiRequest(`/clubs/${club.code}/?format=json`, {
                          method: 'PATCH',
                          body: {
                            approved: true,
                            approved_comment: comment,
                          },
                        })
                          .then(() => router.reload())
                          .finally(() => setLoading(false))
                      }}
                    >
                      <Icon name="check" /> Approve
                    </button>
                    <button
                      className="button is-danger"
                      disabled={loading}
                      onClick={() => {
                        setLoading(true)
                        doApiRequest(`/clubs/${club.code}/?format=json`, {
                          method: 'PATCH',
                          body: {
                            approved: false,
                            approved_comment: comment,
                          },
                        })
                          .then(() => router.reload())
                          .finally(() => setLoading(false))
                      }}
                    >
                      <Icon name="x" /> Reject
                    </button>
                  </>
                )}
                {canDeleteClub && (
                  <button
                    className="button is-danger is-pulled-right"
                    disabled={loading}
                    onClick={() => {
                      doConfirm({
                        func: () => {
                          setLoading(true)
                          doApiRequest(`/clubs/${club.code}/?format=json`, {
                            method: 'DELETE',
                          })
                            .then(() => router.reload())
                            .finally(() => setLoading(false))
                        },
                        message: (
                          <>
                            <p>
                              Are you sure you want to delete <b>{club.name}</b>
                              ?
                            </p>
                            <p>
                              Here are a list of reasons for using this feature:
                            </p>
                            <div className="content">
                              <ul>
                                <li>
                                  Duplicate {OBJECT_NAME_SINGULAR} entries
                                </li>
                                <li>
                                  Mistakenly created {OBJECT_NAME_SINGULAR} with
                                  user acknowledgement and permission
                                </li>
                              </ul>
                            </div>
                            <p>
                              If you are deleting this {OBJECT_NAME_SINGULAR}{' '}
                              for another reason that is not on this list,
                              please check with <Contact /> first. Thank you!
                            </p>
                          </>
                        ),
                      })
                    }}
                  >
                    <Icon name="trash" /> Delete
                  </button>
                )}
              </div>
            </>
          )}
          {club.approved === false &&
            club.is_member !== false &&
            club.is_member <= MembershipRank.Officer && (
              <>
                <div className="mb-3">
                  You can edit your {OBJECT_NAME_SINGULAR} details using the{' '}
                  <b>Manage {OBJECT_NAME_TITLE_SINGULAR}</b> button on this
                  page. After you have addressed the issues mentioned above, you
                  can request renewal again using the button below.
                </div>
                <button
                  className="button is-warning is-light"
                  onClick={() => {
                    doApiRequest(`/clubs/${club.code}/?format=json`, {
                      method: 'PATCH',
                      body: {
                        approved: null,
                      },
                    }).then(() => router.reload())
                  }}
                >
                  Request Review
                </button>
              </>
            )}
        </div>
      ) : null}
      {seeFairStatus && fairInProgress && (
        <div
          className={`notification ${club.fair ? 'is-success' : 'is-warning'}`}
        >
          {club.fair ? (
            <>
              <Icon name="check" /> <b>{club.name}</b> is signed up for the{' '}
              {fairInfo.name}.
            </>
          ) : (
            <>
              <Icon name="x" /> <b>{club.name}</b> is not signed up for the{' '}
              {fairInfo.name}.
            </>
          )}
        </div>
      )}
    </>
  )
}

export default ClubApprovalDialog
