import moment from 'moment-timezone'
import { NextPageContext } from 'next'
import Link from 'next/link'
import { ReactElement } from 'react'

import {
  Contact,
  Container,
  Icon,
  InfoPageTitle,
  Metadata,
} from '../components/common'
import { CLUB_ROUTE, LIVE_EVENTS, SNOW } from '../constants'
import renderPage from '../renderPage'
import { doApiRequest, useSetting } from '../utils'
import {
  OBJECT_NAME_LONG_PLURAL,
  OBJECT_NAME_SINGULAR,
  OBJECT_NAME_TITLE,
  OBJECT_NAME_TITLE_SINGULAR,
  SITE_NAME,
} from '../utils/branding'

type FairPageProps = {
  events: {
    start_time: string
    end_time: string
    events: {
      category: string | null
      events: { name: string; code: string }[]
    }[]
  }[]
}

const FairPage = ({ events }: FairPageProps): ReactElement => {
  const isFairOpen = useSetting('FAIR_OPEN')
  const isPreFair = useSetting('PRE_FAIR')
  const fairName = useSetting('FAIR_NAME') ?? 'Upcoming Fair'
  const fairOrgName = useSetting('FAIR_ORG_NAME') ?? 'partner organization'
  const fairContact = useSetting('FAIR_CONTACT') ?? 'the partner organization'
  const fairTime = useSetting('FAIR_TIME') ?? 'TBD'
  const fairAdditionalInfo = useSetting('FAIR_INFO') ?? ''

  return (
    <Container background={SNOW}>
      <Metadata title={fairName as string} />
      <InfoPageTitle>{fairName} – Student Guide</InfoPageTitle>
      <div className="content">
        {!isPreFair && !isFairOpen && (
          <div className="notification is-warning">
            <Icon name="alert-triangle" /> There is currently no activities fair
            that is currently occuring or upcoming. If you believe this is an
            error, please contact <Contact />.
          </div>
        )}
        <p>
          <b>Hi there! Welcome to {SITE_NAME}!</b> We are the official platform
          for {OBJECT_NAME_LONG_PLURAL} on campus, and we are excited to get you
          connected to clubs on our platform this year. In collaboration with
          the {fairOrgName}, we will be hosting the virtual fair for this
          semester. Below is some important information that will set you up for
          a successful experience.
        </p>
        <p>
          <b>How the {fairName} will be run:</b>
        </p>
        <ul>
          <li>
            The {fairName} will be held on <b>{fairTime}</b>.
          </li>
          <li>
            The main fair functionality is each {OBJECT_NAME_SINGULAR}'s
            informational Zoom meeting, which will all be visible on our{' '}
            {isFairOpen ? (
              <a href="https://pennclubs.com/events">Live Events Page</a>
            ) : (
              'Live Events Page'
            )}
            . Representatives of each club will be available in these meetings
            to answer questions, give short presentations, and otherwise
            interact with students.
          </li>
          <li>
            You can also visit each {OBJECT_NAME_SINGULAR}'s individual page.
            Each {OBJECT_NAME_SINGULAR}'s page has a description, contact
            information, and a FAQ feature that {OBJECT_NAME_SINGULAR} officers
            will be monitoring throughout the fair that you can use to ask
            questions. Questions can be submitted anonymously.
          </li>
          <li>
            To keep track of clubs you are interested in, we encourage you to
            use some of the tools on our platform!
            <ul>
              <li>
                The{' '}
                <b>
                  <Icon name="bookmark" /> Bookmark
                </b>{' '}
                button will allow you to save a club for later for your own
                personal reference. {OBJECT_NAME_TITLE} will not be able to see
                your contact information unless you have allowed it.
              </li>
              <li>
                The{' '}
                <b>
                  <Icon name="bell" /> Subscribe
                </b>{' '}
                button will put your name on a club's mailing list.{' '}
                {OBJECT_NAME_TITLE_SINGULAR}
                officers can use this list to send you updates on their
                application process, upcoming meetings, and more.
              </li>
            </ul>
          </li>
        </ul>
        <p>
          <b>Configuring Zoom:</b>
        </p>
        <ul>
          <li>
            If you have not already activated your Zoom account, click "Sign in"
            at <a href="https://upenn.zoom.us/">this link</a> and sign in with
            your PennKey. You will not be able to attend any of the live events
            without signing in to your Zoom account.
          </li>
          <li>
            If you have not already downloaded the Zoom desktop client, we
            highly encourage you to do so to take advantage of all Zoom
            features. Click <a href="https://zoom.us/download">here</a> to
            download the desktop client.
          </li>
        </ul>
        <p>
          <b>Code of Conduct:</b>
        </p>
        <ul>
          <li>
            Please be respectful in attending information sessions. If the
            session is busy with many attendees, allow each other to take turns
            asking questions. Where appropriate, use the 'raise hand' feature to
            reduce interruptions.
          </li>
          <li>
            Please use appropriate language in the chat windows on Zoom. There
            will be peer to peer monitoring, ensuring that student participants
            and club members are not misusing any features during these
            sessions.
          </li>
        </ul>
        <p>
          <b>Contact:</b>
        </p>
        <ul>
          <li>
            If you have any questions or concerns regarding the {fairName},
            please contact <Contact email={fairContact as string} />.
          </li>
          <li>
            If you have any questions or concerns regarding the {SITE_NAME}{' '}
            platform, please contact <Contact />.
          </li>
        </ul>
        {fairAdditionalInfo && fairAdditionalInfo.length && (
          <p>{fairAdditionalInfo}</p>
        )}
        <p>
          You can find the schedule for the activities fair in the table below.
        </p>
        {isFairOpen && (
          <Link href={LIVE_EVENTS} as={LIVE_EVENTS}>
            <a className="button is-primary">
              <Icon name="chevrons-right" /> Go to events
            </a>
          </Link>
        )}
        <div className="columns mt-3">
          {events.map(
            ({ start_time, end_time, events }, i): ReactElement => {
              const parsedDate = moment(start_time).tz('America/New_York')
              const endDate = moment(end_time).tz('America/New_York')
              return (
                <div key={i} className="column">
                  <div className="mb-3">
                    <b className="has-text-info">
                      {parsedDate.format('LLL')} - {endDate.format('LT z')}
                    </b>
                  </div>
                  {events.map(({ category, events }) => (
                    <div key={category}>
                      <b>{category}</b>
                      <ul className="mt-0 mb-3">
                        {events.map((event) => (
                          <li key={event.code}>
                            <Link
                              href={CLUB_ROUTE()}
                              as={CLUB_ROUTE(event.code)}
                            >
                              <a>{event.name}</a>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )
            },
          )}
        </div>
      </div>
    </Container>
  )
}

FairPage.getInitialProps = async (ctx: NextPageContext) => {
  const { req } = ctx
  const data = {
    headers: req ? { cookie: req.headers.cookie } : undefined,
  }

  const resp = await doApiRequest(
    `/events/fair/?date=${ctx.query.date as string}&format=json`,
    data,
  )
  const json = await resp.json()

  return { events: json }
}

export default renderPage(FairPage)
