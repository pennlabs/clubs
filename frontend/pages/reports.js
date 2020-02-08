import s from 'styled-components'
import { useEffect, useState } from 'react'
import renderPage from '../renderPage.js'
import { Icon, Flex } from '../components/common'
import { doApiRequest, API_BASE_URL } from '../utils'
import { Sidebar } from '../components/common/Sidebar'
import Checkbox, { CheckboxLabel } from '../components/common/Checkbox'
import { Container, WideContainer } from '../components/common/Container'
import {
  CLUBS_GREY,
  RED,
  ALLBIRDS_GRAY,
  MEDIUM_GRAY,
} from '../constants/colors'

const TallTextArea = s.textarea`
  height: 6em;
`

const GroupLabel = s.h4`
  margin-top: 1em;
  margin-bottom: 0em !important;
  font-size: 32px;
  color: #626572;
`

const HoverListElement = s.li`

  span {
    display: none;
  }

  &:hover span {
    display: inline;
    cursor: pointer;
  }

`

const SelectedManager = ({ value, onClick }) => (
  <HoverListElement>
    {value}

    <span style={{ marginLeft: '1em' }} onClick={onClick}>
      X
    </span>
  </HoverListElement>
)

const Reports = ({ nameToCode }) => {
  const fields = {
    Fields: Object.keys(nameToCode),
  }

  const [includedFields, setIncludedFields] = useState(
    (() => {
      const initial = {}
      Object.keys(fields).forEach(group =>
        fields[group].forEach(f => {
          initial[f] = false
        })
      )
      return initial
    })()
  )

  const query = {
    format: 'xlsx',
    fields: Object.keys(includedFields)
      .filter(field => includedFields[field])
      .map(name => nameToCode[name])
      .filter(e => e !== undefined),
  }

  const generateCheckboxGroup = (groupName, fields) => {
    return (
      <div key={groupName} style={{ flexBasis: '50%', flexShrink: 0 }}>
        <GroupLabel
          key={groupName}
          className="subtitle is-4"
          style={{ color: CLUBS_GREY }}
        >
          {groupName}
        </GroupLabel>
        {fields.map((field, idx) => (
          <div key={idx}>
            <Checkbox
              id={field}
              checked={includedFields[field]}
              onChange={() => {
                setIncludedFields(prev => ({ ...prev, [field]: !prev[field] }))
              }}
            />
            {'  '}
            <CheckboxLabel htmlFor={field}>{field}</CheckboxLabel>
          </div>
        ))}
      </div>
    )
  }

  return (
    <Container>
      <WideContainer>
        <h1 className="title" style={{ color: CLUBS_GREY }}>
          Create a new report
        </h1>
        <div className="box">
          <h3 className="title is-4" style={{ color: CLUBS_GREY }}>
            Report Details
          </h3>
          <div>
            <div className="field">
              <label className="label">Name</label>
              <div className="control">
                <input
                  name="name"
                  className="input"
                  type="text"
                  placeholder='e.g. "Owner emails"'
                />
              </div>
            </div>
            <div className="field">
              <label className="label">Description</label>
              <div className="control">
                <TallTextArea
                  name="description"
                  className="input"
                  type="text"
                  placeholder='e.g. "Pulls all clubs, the emails from club owners, and names of owners"'
                />
              </div>
            </div>
          </div>
        </div>
        <div className="box">
          <h3 className="title is-4" style={{ color: CLUBS_GREY }}>
            Select fields to include
          </h3>
          <div>
            <Flex>
              {Object.keys(fields).map(group =>
                generateCheckboxGroup(group, fields[group])
              )}
            </Flex>
          </div>
        </div>
        <button
          className="button is-info"
          onClick={() => {
            window.open(
              `${API_BASE_URL}/clubs/?format=xlsx&fields=${query.fields.join(
                ','
              )}`,
              '_blank'
            )
          }}
        >
          Generate Report
        </button>
      </WideContainer>
    </Container>
  )
}

Reports.getInitialProps = async props => {
  const fieldsReq = await doApiRequest('/clubs/fields/?format=json')
  const fieldsRes = await fieldsReq.json()

  return { nameToCode: fieldsRes }
}

export default renderPage(Reports)
