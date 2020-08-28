import moment from 'moment'
import { NextPageContext } from 'next'
import Link from 'next/link'
import { ReactElement } from 'react'

import { Container, Icon, InfoPageTitle, Metadata } from '../components/common'
import { CLUB_ROUTE, LIVE_EVENTS, SNOW } from '../constants'
import renderPage from '../renderPage'
import { ClubEvent, ClubEventType } from '../types'
import { doApiRequest } from '../utils'

type FairPageProps = {
  events: ClubEvent[]
}

const FairPage = ({ events }: FairPageProps): ReactElement => {
  const eventsByDay = {}

  events.forEach((item) => {
    const startTimestamp = new Date(item.start_time).getTime()
    const categorySplit = (
      item.badges
        .map(({ label }) => label)
        .find((badge) => badge.startsWith('SAC Fair - ')) ?? 'Miscellaneous'
    ).split('-')
    const category = categorySplit[categorySplit.length - 1]

    if (!(startTimestamp in eventsByDay)) {
      eventsByDay[startTimestamp] = {}
    }
    if (!(category in eventsByDay[startTimestamp])) {
      eventsByDay[startTimestamp][category] = []
    }
    eventsByDay[startTimestamp][category].push(item)
  })

  return (
    <Container background={SNOW}>
      <Metadata title="Virtual Activities Fair" />
      <InfoPageTitle>SAC Virtual Activities Fair</InfoPageTitle>
      <div className="content">
        <p>
          The Student Activities Council Virtual Activities Fair will be held on{' '}
          <b>September 1 - 3</b> from <b>5pm to 8pm</b> on each of the three
          days. The event will be held virtually over Zoom.
        </p>
        <p>
          You can find the schedule for the activities fair in the table below.
        </p>
        <Link href={LIVE_EVENTS} as={LIVE_EVENTS}>
          <a className="button is-primary">
            <Icon name="chevrons-right" /> Go to events
          </a>
        </Link>
        <div className="columns mt-3">
          {Object.entries(eventsByDay)
            .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
            .map(
              ([day, events]: [
                string,
                { [category: string]: ClubEvent[] },
              ]): ReactElement => {
                const parsedDate = moment(parseInt(day))
                const endDate = moment(Object.values(events)[0][0].end_time)
                return (
                  <div key={day} className="column">
                    <div className="mb-3">
                      <b className="has-text-info">
                        {parsedDate.format('LLL')} - {endDate.format('LT')}
                      </b>
                    </div>
                    {Object.entries(events)
                      .sort((a, b) => a[0].localeCompare(b[0]))
                      .map(([category, list]) => (
                        <>
                          <b>{category}</b>
                          <ul className="mt-0 mb-3">
                            {list
                              .sort((a, b) =>
                                a.club_name.localeCompare(b.club_name),
                              )
                              .map((event) => (
                                <li key={event.club}>
                                  <Link
                                    href={CLUB_ROUTE()}
                                    as={CLUB_ROUTE(event.club)}
                                  >
                                    <a>{event.club_name}</a>
                                  </Link>
                                </li>
                              ))}
                          </ul>
                        </>
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
    `/events/?format=json&type=${ClubEventType.FAIR}`,
    data,
  )
  const json = await resp.json()

  return { events: json }
}

export default renderPage(FairPage)
