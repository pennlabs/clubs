import { useRouter } from 'next/router'
import React, { ReactElement } from 'react'
import styled from 'styled-components'

import { Icon, TransparentButton } from '../../components/common'
import { CLUB_ROUTE, CLUBS_BLUE, M2 } from '../../constants'
import { ClubEvent } from '../../types'
import { ClubName, EventLink, EventName } from './common'
import CoverPhoto from './CoverPhoto'
import DateInterval from './DateInterval'
import HappeningNow from './HappeningNow'

const ModalContainer = styled.div`
  text-align: left;
`

const EventDetails = styled.div`
  padding: 20px;
`

const Description = ({
  contents,
  className,
}: {
  contents: string
  className?: string
}) => (
  <div
    className={className}
    dangerouslySetInnerHTML={{
      __html: contents || '',
    }}
  />
)

const StyledDescription = styled(Description)`
  font-size: ${M2};
  margin-top: 5px;
  margin-bottom: 15px;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;

  & > p {
    word-wrap: break-word;
  }
`
const RightAlign = styled.div`
  & > * {
    float: right;
  }
`

const MetaDataGrid = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
`

const EventModal = (props: {
  event: ClubEvent
  isHappening: boolean
}): ReactElement => {
  const { event, isHappening } = props
  const {
    image_url,
    club_name,
    start_time,
    end_time,
    name,
    url,
    description,
  } = event
  const router = useRouter()

  return (
    <ModalContainer>
      <CoverPhoto
        image={image_url}
        fallback={<p>{club_name.toLocaleUpperCase()}</p>}
      />
      <EventDetails>
        <MetaDataGrid>
          <DateInterval start={new Date(start_time)} end={new Date(end_time)} />
          <RightAlign>{isHappening && <HappeningNow />}</RightAlign>
        </MetaDataGrid>

        <ClubName>{club_name}</ClubName>
        <EventName>{name}</EventName>
        {url && <EventLink href={url}>{url}</EventLink>}
        <StyledDescription contents={description} />
        <RightAlign>
          <TransparentButton
            backgroundColor={CLUBS_BLUE}
            onClick={() => router.push(CLUB_ROUTE(), CLUB_ROUTE(event.club))}
          >
            See Club Details <Icon name="chevrons-right" alt="chevrons-right" />
          </TransparentButton>
        </RightAlign>
      </EventDetails>
    </ModalContainer>
  )
}

export default EventModal
