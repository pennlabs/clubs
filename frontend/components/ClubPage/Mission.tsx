import { ReactElement } from 'react'
import styled from 'styled-components'

import { Club } from '../../types'
import { EMPTY_MISSION } from '../../utils'
import { StrongText } from '../common'

const Wrapper = styled.div`
  display: flex;
  justify-content: space-between;
  flex-direction: row;
  align-items: center;
  flex: 1;
`

type Props = {
  club: Club
}

const Mission = ({ club }: Props): ReactElement => (
  <Wrapper>
    <div style={{ width: '100%' }}>
      <StrongText>Mission</StrongText>
      <div
        className="content"
        dangerouslySetInnerHTML={{
          __html: club.mission || EMPTY_MISSION,
        }}
      />
    </div>
  </Wrapper>
)

export default Mission
