import { ReactElement, useEffect, useRef, useState } from 'react'
import styled from 'styled-components'

import { PaginatedClubPage } from '../renderPage'
import { Club, Tag } from '../types'
import { doApiRequest } from '../utils'
import { CLUB_EMPTY_STATE, OBJECT_NAME_PLURAL } from '../utils/branding'
import ClubDisplay from './ClubDisplay'
import { Loading } from './common'

type ClubDisplayProps = {
  displayClubs: PaginatedClubPage
  tags: Tag[]
  display: 'list' | 'cards'
}

const EmptyState = styled.div`
  text-align: center;
  margin-top: 5rem;

  & img {
    max-width: 300px;
    margin-bottom: 1rem;
  }
`

const PaginatedClubDisplay = ({
  displayClubs,
  tags,
  display,
}: ClubDisplayProps): ReactElement => {
  const [isLoading, setLoading] = useState<boolean>(false)
  const [clubs, setClubs] = useState<Club[]>(displayClubs.results)
  const [nextUrl, setNextUrl] = useState<string | null>(null)
  const savedNextUrl = useRef<string | null>(displayClubs.next)
  const freshCounter = useRef<number>(0)
  const [refresher, setRefresher] = useState<boolean>(false)

  const fetchNextPage = async (): Promise<PaginatedClubPage | null> => {
    if (nextUrl == null) {
      return null
    }

    setLoading(true)

    // fetch the entry
    const resp = await doApiRequest(nextUrl)
    const json = await resp.json()

    setLoading(false)

    return json
  }

  const loadNextPage = () => {
    if (savedNextUrl.current != null) {
      setNextUrl(savedNextUrl.current)
      savedNextUrl.current = null
    }
  }

  useEffect(() => {
    let isMounted = true
    const counter = freshCounter.current

    fetchNextPage().then((page: PaginatedClubPage | null): void => {
      if (page != null && isMounted && freshCounter.current === counter) {
        savedNextUrl.current = page.next
        setClubs((clubs) => [...clubs, ...page.results])
      }
    })

    return () => {
      isMounted = false
    }
  }, [nextUrl])

  useEffect(() => {
    freshCounter.current += 1
    savedNextUrl.current = null
    setRefresher(true)
    setClubs(displayClubs.results)
    setNextUrl(displayClubs.next)
  }, [displayClubs])

  // hack to fix the weird ghost club appearing
  useEffect(() => {
    if (refresher) {
      setRefresher(false)
    }
  }, [refresher])

  return (
    <>
      {!refresher && (
        <ClubDisplay
          displayClubs={clubs}
          tags={tags}
          display={display}
          onScroll={loadNextPage}
        />
      )}
      {isLoading && <Loading delay={0} />}
<<<<<<< HEAD
      {clubs && clubs.length <= 0 && (
=======
      {(clubs == null || clubs.length <= 0) && (
>>>>>>> add bugfix
        <EmptyState>
          <img
            src="/static/img/button.svg"
            alt={`no ${OBJECT_NAME_PLURAL} found`}
          />
          <div>
            There are no {OBJECT_NAME_PLURAL} matching your search query.
          </div>
          <div>{CLUB_EMPTY_STATE}</div>
        </EmptyState>
      )}
    </>
  )
}

export default PaginatedClubDisplay
