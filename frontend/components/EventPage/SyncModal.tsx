import React, { ReactElement } from 'react'
import styled from 'styled-components'

import { CLUBS_BLUE, CLUBS_GREY, CLUBS_NAVY } from '../../constants/colors'

const ModalContainer = styled.div`
  text-align: left;
  padding: 40px;
`

const Title = styled.div`
  color: ${CLUBS_GREY};
  font-size: 25px;
  font-weight: bold;
`

const Subtitle = styled.div`
  margin: 15px 0;
  color: ${CLUBS_NAVY};
  font-size: 15px;
  font-weight: bold;
`

const SyncModal = (props: { calendarURL: string }): ReactElement => {
  return (
    <ModalContainer>
      <Title>Sync To Calendar</Title>
      <div style={{ display: 'block', marginTop: '15px' }}>
        <div className="field has-addons is-expanded">
          <div className="field-label is-normal" style={{ flexGrow: 0 }}>
            <label className="label">URL:</label>
          </div>
          <div className="control is-expanded">
            <input
              className="input"
              type="text"
              readOnly
              value={props.calendarURL}
              style={{ border: `solid ${CLUBS_BLUE} 1px` }}
            />
          </div>
          <div className="control">
            <a className="button is-info" style={{ background: CLUBS_BLUE }}>
              Copy
            </a>
          </div>
        </div>
      </div>
      <Subtitle>Import to Google Calendar</Subtitle>
      <p>Copy and paste the URL above to import to Google Calendar.</p>
      <Subtitle>Import to iCal</Subtitle>
      <p>Copy and paste the URL above to import to iCal.</p>
    </ModalContainer>
  )
}

export default SyncModal
