import s from 'styled-components'
import { Icon, Text, StrongText, Card } from '../common'
import { useState, useEffect } from 'react'

const Events = ({ data }) => {

  const BigParagraph = s.p`
    font-size: 0.8rem;
    font-weight: bold;
  `

  const SmallParagraph = s.p`
    font-size: 0.8rem;
  `

  const Wrapper = s.div`
    marginBottom: 0.5rem;
    display: flex;
  `

  if (!data || !data.length) {
    return null
  }

  return (
    <Card bordered style={{ marginBottom: '1rem' }}>
      <StrongText>Events</StrongText>
      {data.map((entry, index) => {
        return (
          <Wrapper key={index}>
            <Icon name='calendar' style={{ marginRight: "7px" }} size="32px" alt='Calendar icon' />
            <div>
              <BigParagraph>
                {new Intl.DateTimeFormat("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "2-digit",
                  hour: "numeric",
                  minute: "numeric"
                }).format(new Date(entry.start_time))} | {entry.location}
              </BigParagraph>
              <SmallParagraph>
                {entry.name}
              </SmallParagraph>
            </div>
          </Wrapper>
        )
      })}
    </Card>
  )
}

export default Events
