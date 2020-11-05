import { ReactElement, useEffect, useState } from 'react'
import Select from 'react-select'
import TimeAgo from 'react-timeago'

import { Club, MembershipRank, MembershipRole } from '../../types'
import { doApiRequest, formatResponse, getRoleDisplay } from '../../utils'
import {
  MEMBERSHIP_ROLE_NAMES,
  OBJECT_MEMBERSHIP_LABEL,
  OBJECT_NAME_SINGULAR,
  SCHOOL_NAME,
} from '../../utils/branding'
import { Icon, Text } from '../common'
import BaseCard from './BaseCard'
import { MEMBERSHIP_ROLES } from './MembersCard'

type InviteCardProps = {
  club: Club
}

type Invite = {
  id: number
  email: string
  title: string
  role: number
  updated_at: string
}

export default function InviteCard({ club }: InviteCardProps): ReactElement {
  const [invites, setInvites] = useState<Invite[]>([])
  const [inviteTitle, setInviteTitle] = useState<string>('Member')
  const [inviteRole, setInviteRole] = useState<MembershipRole>(
    MEMBERSHIP_ROLES[0],
  )
  const [invitePercentage, setInvitePercentage] = useState<number | null>(null)
  const [inviteEmails, setInviteEmails] = useState<string>('')
  const [isInviting, setInviting] = useState<boolean>(false)

  const [message, notify] = useState<ReactElement | string | null>(null)

  const reloadInvites = (): void => {
    doApiRequest(`/clubs/${club.code}/invites/?format=json`)
      .then((resp) => resp.json())
      .then(setInvites)
  }

  const deleteInvite = (id: string | number): void => {
    doApiRequest(`/clubs/${club.code}/invites/${id}/?format=json`, {
      method: 'DELETE',
    }).then((resp) => {
      if (resp.ok) {
        notify('Invitation has been removed!')
        reloadInvites()
      } else {
        resp.json().then((err) => {
          notify(formatResponse(err))
        })
      }
    })
  }

  const resendInvite = (id) => {
    doApiRequest(`/clubs/${club.code}/invites/${id}/resend/?format=json`, {
      method: 'PUT',
    })
      .then((resp) => resp.json())
      .then((resp) => {
        notify(resp.detail)
      })
  }

  const sendInviteBatch = async (emails: string[]) => {
    const resp = doApiRequest(`/clubs/${club.code}/invite/?format=json`, {
      method: 'POST',
      body: {
        emails: emails.join('\n'),
        role: inviteRole.value,
        title: inviteTitle,
      },
    })

    const json = (await resp).json()
    return json
  }

  const sendInvites = async () => {
    const emails = inviteEmails
      .split(/(?:\n|\||,)/)
      .map((email) => email.trim())
      .filter((email) => email.length > 0)

    setInviting(true)

    if (emails.length <= 10) {
      try {
        const data = await sendInviteBatch(emails)
        if (data.success) {
          setInviteEmails('')
        }
        notify(formatResponse(data))
      } finally {
        reloadInvites()
        setInviting(false)
      }
    } else {
      setInvitePercentage(0)
      const chunks: string[][] = []
      for (let i = 0; i < emails.length; i += 10) {
        chunks.push(emails.slice(i, i + 10))
      }

      const responses: { sent: number; skipped: number }[] = []
      for (let i = 0; i < chunks.length; i++) {
        const data = await sendInviteBatch(chunks[i])
        if (!data.success) {
          notify(formatResponse(data))
          reloadInvites()
          setInviting(false)
          setInvitePercentage(null)
          return
        }
        setInvitePercentage((i + 1) / chunks.length)
        responses.push(data)
      }

      notify(
        <>
          Sent invites to{' '}
          {responses.map((resp) => resp.sent).reduce((a, b) => a + b, 0)}{' '}
          emails!{' '}
          {responses.map((resp) => resp.skipped).reduce((a, b) => a + b, 0)}{' '}
          emails were skipped because they are already invited or a member.
        </>,
      )
      setInviteEmails('')
      reloadInvites()
      setInviting(false)
      setInvitePercentage(null)
    }
  }

  const updatePermissions = (opt: MembershipRole) => {
    setInviteRole(opt)

    if (MEMBERSHIP_ROLES.map((role) => role.label).includes(inviteTitle)) {
      setInviteTitle(opt.label)
    }
  }

  useEffect(reloadInvites, [])

  return (
    <>
      {message !== null && (
        <div className="notification is-primary">{message}</div>
      )}
      {invites && !!invites.length && (
        <BaseCard title={`Pending Invites (${invites.length})`}>
          <table className="table is-fullwidth">
            <thead>
              <tr>
                <th>Email</th>
                <th>Title (Permissions)</th>
                <th>Invite Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invites.map((item) => (
                <tr key={item.email}>
                  <td>{item.email}</td>
                  <td>
                    {item.title} ({getRoleDisplay(item.role)})
                  </td>
                  <td>
                    <TimeAgo date={item.updated_at} />
                  </td>
                  <td>
                    <button
                      className="button is-small is-link"
                      onClick={() => resendInvite(item.id)}
                    >
                      <Icon name="mail" alt="resend invite" /> Resend
                    </button>{' '}
                    <button
                      className="button is-small is-danger"
                      onClick={() => deleteInvite(item.id)}
                    >
                      <Icon name="x" alt="remove invite" /> Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </BaseCard>
      )}
      <BaseCard title={`Invite ${OBJECT_MEMBERSHIP_LABEL}`}>
        <Text>
          Enter an email address or a list of email addresses separated by
          commas or newlines in the box below.
        </Text>
        <Text>
          All emails listed will be sent an invite to join the{' '}
          {OBJECT_NAME_SINGULAR}. The invite process will go more smoothly if
          you use {SCHOOL_NAME} email addresses, but normal email addresses will
          work provided that the recipient has a valid PennKey account. We will
          not send an invite if the account associated with an email is already
          in the {OBJECT_NAME_SINGULAR} or if an invite associated with that
          email already exists.
        </Text>
        <div className="field">
          <textarea
            value={inviteEmails}
            onChange={(e) => setInviteEmails(e.target.value)}
            className="textarea"
            placeholder="Enter email addresses here!"
            data-testid="invite-emails-input"
          ></textarea>
        </div>
        <div className="field">
          <label className="label">Permissions</label>
          <div className="control">
            <Select
              options={MEMBERSHIP_ROLES}
              value={inviteRole}
              onChange={updatePermissions}
            />
          </div>
          <p className="help">
            {MEMBERSHIP_ROLE_NAMES[MembershipRank.Owner]}s have full control
            over the {OBJECT_NAME_SINGULAR},{' '}
            {MEMBERSHIP_ROLE_NAMES[MembershipRank.Officer]}s can perform
            editing, and {MEMBERSHIP_ROLE_NAMES[MembershipRank.Member]}s have
            read-only permissions.
          </p>
        </div>
        <div className="field">
          <label className="label">Title</label>
          <div className="control">
            <input
              className="input"
              value={inviteTitle}
              onChange={(e) => setInviteTitle(e.target.value)}
            />
          </div>
          <p className="help">
            The title is shown on the {OBJECT_MEMBERSHIP_LABEL.toLowerCase()}{' '}
            listing and will not affect user permissions.
          </p>
        </div>
        {invitePercentage !== null && (
          <div className="mb-3">
            <progress
              className="progress"
              value={(invitePercentage ?? 0) * 100}
              max={100}
            />
          </div>
        )}
        <button
          disabled={isInviting}
          className="button is-primary"
          onClick={sendInvites}
          data-testid="invite-emails-submit"
        >
          <Icon name="mail" alt="send invites" />
          &nbsp; Send Invite(s)
        </button>
      </BaseCard>
    </>
  )
}
