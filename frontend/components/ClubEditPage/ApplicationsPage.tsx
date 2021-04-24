import Link from 'next/link'
import { useRouter } from 'next/router'
import React, { ReactElement, useEffect, useState } from 'react'
import { toast, TypeOptions } from 'react-toastify'
import styled from 'styled-components'
import {
  CLUBS_GREY,
  CLUBS_GREY_LIGHT,
  EVENT_TYPE_COLORS,
  FULL_NAV_HEIGHT,
  MD,
  mediaMaxWidth,
  SNOW,
  WHITE,
} from '~/constants'

const StyledSetting = styled.div`
  margin-bottom: 40px;
`
const StyledResponses = styled.div`
margin-bottom: 40px;
`

const StyledHeader = styled.div.attrs({ className: 'is-clearfix' })`
  margin: 20px 0;
  & > .info {
    float: left;
  }
  .tools {
    float: right;
    margin: 0;
    margin-left: auto;
    & > div {
      margin-left: 20px;
      display: inline-block;
    }
  }

  ${mediaMaxWidth(MD)} {
    .tools {
      margin-top: 20px;
    }
  }
`

const ApplicaionsPage = () => {
  return <div className ="columns" >
  <div className = "column is-one-third">
  <StyledHeader>Forms</StyledHeader>
  </div>
  <div className = "column is-two-thirds">
  <StyledSetting>
  <StyledHeader>Settings</StyledHeader>
  </StyledSetting>
  <StyledResponses>
  <StyledHeader>Responses</StyledHeader>
  </StyledResponses>
  </div>
  </div >
}

export default ApplicaionsPage
