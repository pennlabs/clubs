import Link from 'next/link'
import { useRouter } from 'next/router'
import { ReactElement } from 'react'
import s from 'styled-components'

import { SHORT_ANIMATION_DURATION } from '../../constants/animations'
import {
  BANNER_TEXT,
  BORDER,
  CLUBS_NAVY,
  CLUBS_RED,
  CLUBS_RED_DARK,
  LOGIN_BACKGROUND,
  WHITE,
  WHITE_ALPHA,
} from '../../constants/colors'
import {
  LINK_MARGIN,
  LINK_SPACING,
  LOGIN_MARGIN,
  LOGIN_OPACITY,
  MD,
  mediaMaxWidth,
} from '../../constants/measurements'
import { SETTINGS_ROUTE } from '../../constants/routes'
import { UserInfo } from '../../types'
import { LOGIN_URL } from '../../utils'
import { logEvent } from '../../utils/analytics'
import { Icon } from '../common'

const StyledIcon = s(Icon)`
  opacity: 0.5;
  margin-right: 4px;
`

const LoginButton = s.a`
  border: 0;
  background-color: ${LOGIN_BACKGROUND};
  padding: 14px 20px;
  margin: auto;
  margin-bottom: ${LOGIN_MARGIN};
  opacity: ${LOGIN_OPACITY};
  color: ${WHITE_ALPHA(0.8)} !important;
  transition: color ${SHORT_ANIMATION_DURATION}ms ease,
              background ${SHORT_ANIMATION_DURATION}ms ease;

  &:hover,
  &:focus,
  &:active {
    background-color: ${LOGIN_BACKGROUND};
    color: ${WHITE} !important;
  }

  ${mediaMaxWidth(MD)} {
    padding: 8px 0;
    padding-top: 0.4rem;
    width: 5rem !important;
  }
`

const StyledLinkAnchor = s.a`
  padding: ${LINK_MARGIN} 20px;
  color: ${BANNER_TEXT} !important;
  display: inline-block;
  cursor: pointer;
`

const StyledLink = (props) => {
  return (
    <Link href={props.href}>
      <StyledLinkAnchor {...props} />
    </Link>
  )
}

const Menu = s.div<{ show?: boolean }>`
  ${mediaMaxWidth(MD)} {
    ${({ show }) => show && 'display: block;'}
  }
`

type Props = {
  userInfo?: UserInfo
  authenticated: boolean | null
  show?: boolean
}

/**
 * Checks authenticated === false to confirm browser has loaded and user is not logged in.
 * Will be undefined if browser has not loaded and true is browser has loaded and user is logged in.
 */
const Links = ({ userInfo, authenticated, show }: Props): ReactElement => {
  const router = useRouter()
  return (
    <Menu className="navbar-menu" show={show}>
      <div className="navbar-end" style={{ padding: '0 1rem' }}>
        <StyledLink href="/events" onClick={() => logEvent('events', 'click')}>
          Events
        </StyledLink>
        <StyledLink href="/faq" onClick={() => logEvent('faq', 'click')}>
          FAQ
        </StyledLink>
        {authenticated === false && (
          <LoginButton
            className="button"
            href={`${LOGIN_URL}?next=${router.asPath}`}
            onClick={() => logEvent('login', 'click')}
          >
            Login
          </LoginButton>
        )}
        {userInfo && (
          <StyledLink href={SETTINGS_ROUTE}>
            <StyledIcon name="user" alt="settings" />
            {userInfo.name || userInfo.username}
          </StyledLink>
        )}
      </div>
    </Menu>
  )
}

export default Links
