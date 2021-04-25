import Link from 'next/link'
import { useRouter } from 'next/router'
import React, { ReactElement, useEffect, useState, useMemo,  } from 'react'
import { toast, TypeOptions } from 'react-toastify'
import styled from 'styled-components'
import HashTabView from '../TabView';
import Toggle from '../Settings/Toggle'
import {
  CLUBS_GREY,
  CLUBS_GREY_LIGHT,
  CLUBS_BLUE,
  EVENT_TYPE_COLORS,
  FULL_NAV_HEIGHT,
  BG_GRADIENT,
  ALLBIRDS_GRAY,
  H1_TEXT,
  HOVER_GRAY,
  MD,
  mediaMaxWidth,
  SNOW,
  ANIMATION_DURATION,
  BORDER_RADIUS,
  CARD_HEADING,
  SM,
  WHITE,
} from '~/constants'
import {Icon} from '../common/Icon'
import Table from '../common/Table'

import {Tag} from  '../common/Tags'

const StyledSetting = styled.div`
  margin-bottom: 20px;
`
const StyledResponses = styled.div`
margin-bottom: 40px;
`

const FormsCard = styled.div<CardProps>`
  padding: 0px;
  box-shadow: 0 0 0 transparent;
  transition: all ${ANIMATION_DURATION}ms ease;
  border-radius: ${BORDER_RADIUS};
  box-shadow: 0 0 0 ${WHITE};
  background-color: ${({ hovering }) => (hovering ? HOVER_GRAY : WHITE)};
  border: 1px solid ${ALLBIRDS_GRAY};
  justify-content: space-between;
  height: 65vh;

  

  ${mediaMaxWidth(SM)} {
    width: calc(100%);
    padding: 8px;
  }
`

const SettingsCard = styled.div<CardProps>`
  padding: 0px;
  box-shadow: 0 0 0 transparent;
  transition: all ${ANIMATION_DURATION}ms ease;
  border-radius: ${BORDER_RADIUS};
  box-shadow: 0 0 0 ${WHITE};
  background-color: ${({ hovering }) => (hovering ? HOVER_GRAY : WHITE)};
  border: 1px solid ${ALLBIRDS_GRAY};
  justify-content: space-between;
  height: 32vh;

  

  ${mediaMaxWidth(SM)} {
    width: calc(100%);
    padding: 8px;
  }
`
const FormsCardWrapper = styled.div`
position: relative;
margin-top:40px;
  ${mediaMaxWidth(SM)} {
    padding-top: 0;
    padding-bottom: 1rem;
    
  }
`

const SettingsCardWrapper = styled.div`
position: relative;
margin-top:40px;
  ${mediaMaxWidth(SM)} {
    padding-top: 0;
    padding-bottom: 1rem;
    
  }
`
const ManageFormsContainer = styled.div`
position: absolute;
bottom: 10px;
left: 50%;
transform: translateX(-50%);
cursor:pointer;

`

const StyledHeader = styled.div.attrs({ className: 'is-clearfix' })`
  margin-bottom: 20px;
  color: ${CLUBS_BLUE};
  font-size: 18px;
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

const FormWrapper = styled.div`
border-bottom: 1px solid ${ALLBIRDS_GRAY};
height: 50px;
padding : 12px;
cursor: pointer;

&:hover,
  &:active,
  &:focus {
    box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
    background-color: ${SNOW}
  }
`

const GeneralSettings = () => {
  return <div>
     <div style={{ display: 'flex', flexDirection: 'row', width: '100' }}>
        <span>Collect Email Addresses</span>
        <div style={{ marginLeft: 'auto' }}>
        <Toggle
            club={null}
            active={true}
            toggle={()=>{}}
          />
        </div>
      </div>
    
      <div style={{ display: 'flex', flexDirection: 'row', width: '100' }}>
        <span>Allow edit after submissions</span>
        <div style={{ marginLeft: 'auto' }}>
        <Toggle
            club={null}
            active={true}
            toggle={()=>{}}
          />
        </div>
      </div>
  </div>
}

const SharingSettings = () => {
  return <div>
    Sharing
  </div>
}

const AdvancedSettings = () => {
  return  <div>
    Advanced
  </div>
}

const tabs = [
  {
    name: 'General',
    content: <GeneralSettings />,
  },
  { name: 'Sharing', content:<SharingSettings /> },
  { name: 'Advanced', content: <AdvancedSettings /> },
]



const Form = (f:any) => {
  const {form} = f
  return <FormWrapper>
    {form.name} 
    <span className='is-pulled-right'>
    <Icon name='user' alt='members' size ='1.2rem' style={{marginRight:'8px'}} />
    <span style={{marginRight:'20px'}}>
    {form.applicantsNumber}
    </span>
    <Icon name='chevron-right' />
    
    </span>
  </FormWrapper>
} 

const forms = [{name:'form1', applicantsNumber: 7}, {name:'form2', applicantsNumber:6}]


const ApplicaionsPage = () => {

  const responseTableFields = [
    {label: 'Email', name: 'email'},
    {label: 'Name', name: 'name'},
    {label: 'Status', name: 'status', render: (_, index) => (
      <span className= {`tag is-${responses[index].status == 'rejected' ?
       'danger' :responses[index].status == 'accepted' ? 'success' : 'info' }  is-light`}>
        {responses[index].status}
      </span>
    )},
    {label: 'Submitted', name:'submitted'},
    {lable: 'Actions', name:'actions'}
  ];

  const responses = [
    {name:'Mohamed', email:'alnasir7@seas.upenn.edu', status: 'pending', submitted:'11 April 2021'},
    {name:'Campel', email:'campel7@seas.upenn.edu', status: 'pending', submitted:'13 April 2021'},
    {name:'Lucy', email:'lucy@seas.upenn.edu', status: 'rejected', submitted:'26 March 2021'},
    {name:'Eric', email:'eric@seas.upenn.edu', status: 'accepted', submitted:'20 March 2021'},
  ]

  const columns = useMemo(
    () =>
    responseTableFields.map(({ label, name }) => ({
        Header: label ?? name,
        accessor: name,
      })),
    [responseTableFields],
  )





  return <div className ="columns" >
  <div className = "column is-one-third" style={{marginRight:'100px'}}>
  <StyledHeader className='is-pulled-left' >Forms</StyledHeader>
  <span className='is-pulled-right'>
  <span className="tag is-info is-light" style={{cursor: 'pointer'}}>New Form +</span>
  </span>
  <FormsCardWrapper>
  <FormsCard className='card'>
    {forms.map( form => 
      <Form form={form} />)
    }
  <ManageFormsContainer>
    <span className = 'tag is-link is-normal'>
      Manage Forms
    </span>
  </ManageFormsContainer>
    </FormsCard>
    </FormsCardWrapper>
  </div>
  <div className = "column is-two-thirds">
  <StyledSetting>
  <StyledHeader>
    Settings
    
  </StyledHeader>
  <SettingsCard className='card'>
  <HashTabView
        background={BG_GRADIENT}
        tabs={tabs}
        tabClassName="is-boxed" 
      />
      </SettingsCard>
  </StyledSetting>
  <StyledResponses>
  <StyledHeader style={{marginBottom:"2px"}} >Responses</StyledHeader>
  <Table
        data={responses.map((item, index) =>
          item.id ? item : { ...item, id: index },
        )}
        columns={responseTableFields}
        searchableColumns={['name']}
        filterOptions={[]}
      />
  </StyledResponses>
  </div>
  </div >
}

export default ApplicaionsPage
