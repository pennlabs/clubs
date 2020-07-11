import PropTypes from 'prop-types'
import s from 'styled-components'

import { CLUBS_GREY } from '../constants/colors'
import { getSizeDisplay } from '../utils'
import { Icon, BookmarkIcon } from './common'
import { Club } from '../types'

const Wrapper = s.div`
  margin-top: 0.25rem;
  padding-top: 0.25rem;
  border-top: 1.5px solid rgba(0, 0, 0, 0.05);
  width: 100%;
  display: flex;
  justify-content: space-between;
`

const iconStyles = {
  marginTop: '-5px',
  marginRight: '5px',
  opacity: 0.5,
  transform: 'translateY(3px)',
}

type DetailsProps = {
  club: Club,
  favorite: boolean,
  updateFavorites: (code: string) => void,
}

const Details = ({
  club,
  favorite,
  updateFavorites,
}: DetailsProps) => {
  const { size, application_required: applicationRequired, accepting_members: acceptingMembers } = club

  return <Wrapper>
    <p style={{ color: CLUBS_GREY, fontSize: '80%', opacity: 0.8 }}>
      <Icon name="user" alt="members" size="0.8rem" style={iconStyles} />
      {getSizeDisplay(size, false)}
      &nbsp;
      {' • '}
      &nbsp;
      <Icon name="edit" alt="applications" size="0.8rem" style={iconStyles} />
      {'Apps for '}
      {{
        1: 'No',
        2: 'Some',
        3: 'All',
      }[applicationRequired] || 'Unknown If'}
      {' Roles'}
      &nbsp;
      {' • '}
      &nbsp;
      {acceptingMembers ? (
        <Icon
          name="check-circle"
          alt="accepting members"
          size="0.8rem"
          style={iconStyles}
        />
      ) : (
          <Icon
            name="x-circle"
            alt="accepting members"
            size="0.8rem"
            style={iconStyles}
          />
        )}
      {acceptingMembers ? 'Taking Members' : 'Not Taking Members'}
    </p>
    <BookmarkIcon
      club={club}
      favorite={favorite}
      updateFavorites={updateFavorites}
      padding="0"
    />
  </Wrapper>
}

export default Details