import Link from 'next/link'
import { ReactElement, useEffect, useState } from 'react'

import { CLUBS_GREY_LIGHT } from '../../constants/colors'
import { HOME_ROUTE } from '../../constants/routes'
import { Club } from '../../types'
import { doApiRequest } from '../../utils'
import ClubTableRow from '../ClubTableRow'
import { Center, EmptyState, Loading, Text } from '../common'

type FavoritesTabProps = {
  keyword: 'bookmark' | 'subscription'
}

export default ({ keyword }: FavoritesTabProps): ReactElement => {
  const [favorites, setFavorites] = useState<Club[] | null>(null)

  useEffect(() => {
    doApiRequest(
      `/${keyword === 'bookmark' ? 'favorite' : 'subscription'}s/?format=json`,
    )
      .then((res) => res.json())
      .then((values) => setFavorites(values.map((relation) => relation.club)))
  }, [])

  if (favorites == null) {
    return <Loading />
  }

  if (!favorites.length) {
    return (
      <>
        <EmptyState name={`${keyword}s`} />
        <Center>
          <Text color={CLUBS_GREY_LIGHT}>
            No {keyword}s yet! Browse clubs{' '}
            <Link href={HOME_ROUTE}>
              <a>here</a>
            </Link>
            .
          </Text>
        </Center>
      </>
    )
  }

  return (
    <div>
      {favorites.map((club) => (
        <ClubTableRow club={club} key={club.code} />
      ))}
    </div>
  )
}
