import equal from 'deep-equal'
import { NextPageContext } from 'next'
import { ReactElement, useEffect, useRef, useState } from 'react'
import styled from 'styled-components'

import { Metadata, Title, WideContainer } from '../components/common'
import AuthPrompt from '../components/common/AuthPrompt'
import EventCard from '../components/EventPage/EventCard'
import SearchBar, {
  getInitialSearch,
  SearchbarRightContainer,
  SearchInput,
} from '../components/SearchBar'
import { CLUBS_GREY, SNOW } from '../constants'
import renderPage from '../renderPage'
import { Badge, ClubEvent, Tag } from '../types'
import { doApiRequest } from '../utils'
import { ListLoadIndicator } from '.'

interface EventPageProps {
  authenticated: boolean | null
  liveEvents: ClubEvent[]
  upcomingEvents: ClubEvent[]
  tags: Tag[]
  badges: Badge[]
}

const CardList = styled.div`
  & .event {
    display: inline-block;
    vertical-align: top;
    width: 400px;
  }
`

/**
 * Randomize the order the events are shown in, but prioritize the ones with
 * filled out information.
 */
const randomizeEvents = (events: ClubEvent[]): ClubEvent[] => {
  const withRankings = events.map((event) => {
    let rank = Math.random()
    if (event.image_url) {
      rank += 2
    }
    if (
      event.description &&
      event.description.length > 3 &&
      event.description !== 'Replace this description!'
    ) {
      rank += 2
    }
    if (event.url) {
      rank += 3
    }
    return {
      event,
      rank,
      startDate: new Date(event.start_time),
      endDate: new Date(event.end_time),
    }
  })
  return withRankings
    .sort((a, b) => {
      if (a.startDate < b.startDate) {
        return -1
      }
      if (b.startDate < a.startDate) {
        return 1
      }
      return b.rank - a.rank
    })
    .map((a) => a.event)
}

function EventPage({
  authenticated,
  upcomingEvents: initialUpcomingEvents,
  liveEvents: initialLiveEvents,
  tags,
  badges,
}: EventPageProps): ReactElement {
  const [upcomingEvents, setUpcomingEvents] = useState<ClubEvent[]>(() =>
    randomizeEvents(initialUpcomingEvents),
  )
  const [liveEvents, setLiveEvents] = useState<ClubEvent[]>(() =>
    randomizeEvents(initialLiveEvents),
  )

  const [searchInput, setSearchInput] = useState<SearchInput>(
    getInitialSearch(),
  )
  const currentSearch = useRef<SearchInput>(getInitialSearch())
  const [isLoading, setLoading] = useState<boolean>(false)

  useEffect(() => {
    if (equal(searchInput, currentSearch.current)) {
      return
    }

    currentSearch.current = searchInput

    const { nameInput, selectedTags } = searchInput

    let isCurrent = true

    const tagSelected = selectedTags
      .filter((tag) => tag.name === 'Tags')
      .map((tag) => tag.value)
    const badgesSelected = selectedTags
      .filter((tag) => tag.name === 'Badges')
      .map((tag) => tag.value)
    const sizeSelected = selectedTags
      .filter((tag) => tag.name === 'Size')
      .map((tag) => tag.value)

    const requiredApplication =
      selectedTags.findIndex(
        (tag) => tag.name === 'Application' && tag.value === 1,
      ) !== -1
    const noRequiredApplication =
      selectedTags.findIndex(
        (tag) => tag.name === 'Application' && tag.value === 2,
      ) !== -1
    const acceptingMembers =
      selectedTags.findIndex(
        (tag) => tag.name === 'Application' && tag.value === 3,
      ) !== -1

    const params = new URLSearchParams()
    params.set('format', 'json')

    if (searchInput.nameInput) {
      params.set('search', nameInput)
    }
    if (tagSelected.length > 0) {
      params.set('club__tags', tagSelected.join(','))
    }
    if (badgesSelected.length > 0) {
      params.set('club__badges', badgesSelected.join(','))
    }
    if (sizeSelected.length > 0) {
      params.set('club__size__in', sizeSelected.join(','))
    }

    // XOR here, if both are yes they cancel out, if both are no
    // we do no filtering
    if (noRequiredApplication !== requiredApplication) {
      if (noRequiredApplication) {
        params.set('club__application_required__in', '1')
      } else {
        params.set('club__application_required__in', '2,3')
      }
    }

    if (acceptingMembers) {
      params.set('club__accepting_members', 'true')
    }

    setLoading(true)

    Promise.all([
      doApiRequest(`/events/live/?${params.toString()}`)
        .then((resp) => resp.json())
        .then((resp) => {
          if (isCurrent) {
            setLiveEvents(randomizeEvents(resp))
          }
        }),
      doApiRequest(`/events/upcoming/?${params.toString()}`)
        .then((resp) => resp.json())
        .then((resp) => {
          if (isCurrent) {
            setUpcomingEvents(randomizeEvents(resp))
          }
        }),
    ]).then(() => setLoading(false))

    return () => {
      isCurrent = false
    }
  }, [searchInput])

  if (!authenticated) {
    return <AuthPrompt />
  }

  return (
    <>
      <Metadata title="Events" />
      <div style={{ backgroundColor: SNOW }}>
        <SearchBar
          tags={tags}
          badges={badges}
          updateSearch={setSearchInput}
          searchValue={searchInput}
          options={{ ordering: { disabled: true } }}
        />
        <SearchbarRightContainer>
          <WideContainer background={SNOW} fullHeight>
            <Title
              className="title"
              style={{ color: CLUBS_GREY, marginTop: '30px' }}
            >
              Live Events
            </Title>
            {isLoading && <ListLoadIndicator />}
            <CardList>
              {liveEvents.map((e) => (
                <EventCard key={e.id} event={e} isHappening={true} />
              ))}
            </CardList>
            <br />
            <Title className="title" style={{ color: CLUBS_GREY }}>
              Upcoming Events
            </Title>
            {isLoading && <ListLoadIndicator />}
            <CardList>
              {upcomingEvents.map((e) => (
                <EventCard key={e.id} event={e} isHappening={false} />
              ))}
            </CardList>
          </WideContainer>
        </SearchbarRightContainer>
      </div>
    </>
  )
}

EventPage.getInitialProps = async (ctx: NextPageContext) => {
  const { req } = ctx
  const data = {
    headers: req ? { cookie: req.headers.cookie } : undefined,
  }

  const [liveEvents, upcomingEvents, tags, badges] = await Promise.all([
    doApiRequest('/events/live/?format=json', data).then((resp) => resp.json()),
    doApiRequest('/events/upcoming/?format=json', data).then((resp) =>
      resp.json(),
    ),
    doApiRequest('/tags/?format=json', data).then((resp) => resp.json()),
    doApiRequest('/badges/?format=json', data)
      .then((resp) => resp.json())
      .then((resp) => resp.filter(({ purpose }) => purpose === 'fair')),
  ])

  return { liveEvents, upcomingEvents, tags, badges }
}

export default renderPage(EventPage)
