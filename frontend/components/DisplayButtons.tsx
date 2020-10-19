import Link from 'next/link'
import { ReactElement } from 'react'
import s from 'styled-components'

import {
  ADD_BUTTON,
  ALLBIRDS_GRAY,
  BLACK_ALPHA,
  CLUBS_BLUE,
  WHITE,
  WHITE_ALPHA,
} from '../constants/colors'
import { BODY_FONT } from '../constants/styles'
import {
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE_SINGULAR,
} from '../utils/branding'
import { Icon } from './common'

const DisplayButtonsTag = s.div`
  float: right;
  font-family: ${BODY_FONT};

  .button {
    margin-left: 8px;
  }
`

const AddClubButton = s.a`
  background-color: ${ADD_BUTTON};
  color: ${WHITE_ALPHA(0.8)} !important;
`

const iconStyles = {
  transform: 'translateY(0px)',
  opacity: 0.6,
  color: `${BLACK_ALPHA(0.8)} !important`,
}

const iconStylesDark = {
  transform: 'translateY(0px)',
  opacity: 0.6,
  color: `${WHITE_ALPHA(0.8)} !important`,
}

const buttonStyles = {
  backgroundColor: WHITE,
  border: `1px solid ${ALLBIRDS_GRAY}`,
  fontFamily: BODY_FONT,
}

const DisplayButtons = ({
  switchDisplay,
}: DisplayButtonsProps): ReactElement => (
  <DisplayButtonsTag>
    <button
      onClick={() => switchDisplay('cards')}
      className="button is-small"
      style={buttonStyles}
    >
      <Icon name="grid" alt="switch to grid view" style={iconStyles} />
    </button>
    <button
      onClick={() => switchDisplay('list')}
      className="button is-small"
      style={buttonStyles}
    >
      <Icon name="list" alt="switch to list view" style={iconStyles} />
    </button>
    <Link href="/create">
      <AddClubButton className="button is-small">
        <Icon
          name="plus"
          alt={`create ${OBJECT_NAME_SINGULAR}`}
          style={iconStylesDark}
        />
        Add {OBJECT_NAME_TITLE_SINGULAR}
      </AddClubButton>
    </Link>
  </DisplayButtonsTag>
)

type DisplayButtonsProps = {
  switchDisplay: (disp: 'list' | 'cards') => void
}

export default DisplayButtons
