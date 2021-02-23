import { Field } from 'formik'
import { ReactElement } from 'react'

import { Club, MembershipRank, MembershipRole } from '../../types'
import { getApiUrl, getRoleDisplay } from '../../utils'
import {
  MEMBERSHIP_ROLE_NAMES,
  OBJECT_MEMBERSHIP_LABEL,
  OBJECT_NAME_SINGULAR,
} from '../../utils/branding'
import { Icon } from '../common'
import { CheckboxField, SelectField, TextField } from '../FormComponents'
import { ModelForm } from '../ModelForm'
import BaseCard from './BaseCard'

export const MEMBERSHIP_ROLES: MembershipRole[] = [
  {
    value: MembershipRank.Member,
    label: MEMBERSHIP_ROLE_NAMES[MembershipRank.Member] ?? 'Unknown',
  },
  {
    value: MembershipRank.Officer,
    label: MEMBERSHIP_ROLE_NAMES[MembershipRank.Officer] ?? 'Unknown',
  },
  {
    value: MembershipRank.Owner,
    label: MEMBERSHIP_ROLE_NAMES[MembershipRank.Owner] ?? 'Unknown',
  },
]

type MembersCardProps = {
  club: Club
}

export default function MembersCard({ club }: MembersCardProps): ReactElement {
  return (
    <BaseCard title={OBJECT_MEMBERSHIP_LABEL}>
      <ModelForm
        keyField="username"
        deleteVerb="Kick"
        noun={OBJECT_MEMBERSHIP_LABEL}
        allowCreation={false}
        confirmDeletion={true}
        baseUrl={`/clubs/${club.code}/members/`}
        fields={
          <>
            <Field name="title" as={TextField} />
            <Field
              name="role"
              as={SelectField}
              choices={MEMBERSHIP_ROLES.filter(
                ({ value }) => value in MEMBERSHIP_ROLE_NAMES,
              )}
              serialize={({ value }) => value}
              valueDeserialize={(val: number) =>
                MEMBERSHIP_ROLES.find((x) => x.value === val)
              }
              isMulti={false}
            />
            <Field
              name="active"
              as={CheckboxField}
              label={`Is this person an active member of your ${OBJECT_NAME_SINGULAR}? Uncheck this box for alumni or retired members.`}
            />
          </>
        }
        tableFields={[
          {
            name: 'name',
          },
          {
            name: 'title',
            label: 'Title (Permissions)',
            converter: (a, all) => (
              <>
                {a} ({getRoleDisplay(all.role)}){' '}
                <Icon
                  name={all.active ? 'check' : 'x'}
                  className={`has-text-${all.active ? 'success' : 'danger'}`}
                />
              </>
            ),
          },
          {
            name: 'email',
          },
        ]}
        filterOptions={[
          {
            label: 'role',
            options: [
              { key: 0, label: 'Owner' },
              { key: 20, label: 'Member' },
              { key: 10, label: 'Officer' },
            ],
            filterFunction: (selection, object) => object.role === selection,
          },
          {
            label: 'Active',
            options: [
              { key: true, label: 'Active' },
              { key: false, label: 'Inactive' },
            ],
            filterFunction: (selection, object) => object.active === selection,
          },
        ]}
        searchableColumns = {["name", "email"]}
        currentTitle={(obj) =>
          obj != null ? `${obj.name} (${obj.email})` : 'Kicked Member'
        }
      />
      <div style={{ marginTop: '1em' }}>
        <a
          href={getApiUrl(`/clubs/${club.code}/members/?format=xlsx`)}
          className="button is-link is-small"
        >
          <Icon alt="download" name="download" /> Download{' '}
          {OBJECT_MEMBERSHIP_LABEL} List
        </a>
      </div>
    </BaseCard>
  )
}
