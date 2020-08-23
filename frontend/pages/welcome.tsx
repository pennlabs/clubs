import { NextPageContext } from 'next'
import Link from 'next/link'
import { ReactElement, useEffect, useState } from 'react'
import s from 'styled-components'

import {
  Center,
  Container,
  Icon,
  Metadata,
  PhoneContainer,
  Text,
  Title,
} from '../components/common'
import AuthPrompt from '../components/common/AuthPrompt'
import LogoWithText from '../components/LogoWithText'
import ProfileForm from '../components/Settings/ProfileForm'
import { HOME_ROUTE } from '../constants/routes'
import renderPage from '../renderPage'
import { UserInfo } from '../types'
import { doApiRequest } from '../utils'

const Subtitle = s(Title)`
  font-size: 1.3rem;
  margin-bottom: 1rem;
`

const TitleHeader = s.div`
  margin-top: 1rem;
  text-align: center;

  h1 {
    margin-top: 1rem;
  }
`

const markWelcome = () => {
  doApiRequest('/settings/?format=json', {
    method: 'PATCH',
    body: {
      has_been_prompted: true, // eslint-disable-line camelcase
    },
  })
}

type WelcomeProps = {
  authenticated: boolean
  userInfo: UserInfo
  nextUrl: string | undefined
}

const Welcome = ({
  authenticated,
  userInfo: initialUserInfo,
  nextUrl,
}: WelcomeProps): ReactElement => {
  const [userInfo, setUserInfo] = useState<UserInfo>(initialUserInfo)

  if (authenticated === false) {
    return <AuthPrompt />
  }

  if (userInfo === null) {
    return (
      <PhoneContainer>
        <TitleHeader>
          <Title>Loading...</Title>
        </TitleHeader>
      </PhoneContainer>
    )
  }

  useEffect(markWelcome, [])

  return (
    <>
      <Metadata title="Welcome!" />
      <Container>
        <TitleHeader>
          <LogoWithText></LogoWithText>
          <Title>Welcome to Penn Clubs!</Title>
        </TitleHeader>
        <hr />
        <Center>
          <Text>
            Penn Clubs is your central source of information about student
            organizations at Penn.
          </Text>
        </Center>
        <hr />
        <Center>
          <Subtitle>1. Tell us about yourself</Subtitle>
          <Text>
            The info below helps us tailor your Penn Clubs experience to find
            clubs that you're likely to be interested in. It will also be shared
            with clubs that you choose to subscribe to. Feel free to leave
            fields blank if you'd prefer not the share this info.
          </Text>
        </Center>
        <ProfileForm settings={userInfo} onUpdate={setUserInfo} />
        <hr />
        <Center>
          <Subtitle>2. Getting started</Subtitle>
          <Text>
            Here are two common buttons that you'll see around the site.
            Bookmarks and subscriptions can be managed from your Penn Clubs
            account at any time.
          </Text>
          <div className="columns is-mobile">
            <div className="column">
              <div className="button is-link is-large">
                <Icon alt="bookmark" name="bookmark" /> Bookmark
              </div>
              <Text style={{ marginTop: '0.5rem' }}>
                To save a club for later
              </Text>
            </div>
            <div className="column">
              <div className="button is-danger is-large">
                <Icon alt="subscribe" name="bell" /> Subscribe
              </div>
              <Text style={{ marginTop: '0.5rem' }}>
                To join the mailing list
              </Text>
            </div>
          </div>
        </Center>
        <hr />
        <Center>
          <Subtitle>3. Start exploring Penn Clubs!</Subtitle>
          <Link
            href={nextUrl && nextUrl.startsWith('/') ? nextUrl : HOME_ROUTE}
          >
            <a className="button is-success is-large" onClick={markWelcome}>
              {nextUrl && nextUrl.startsWith('/') && nextUrl !== HOME_ROUTE
                ? 'Continue'
                : 'Browse clubs'}
            </a>
          </Link>
        </Center>
      </Container>
    </>
  )
}

Welcome.getInitialProps = async ({ query }: NextPageContext) => {
  return { nextUrl: query.next }
}

export default renderPage(Welcome)
