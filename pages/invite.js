import fetch from 'isomorphic-unfetch'
import renderPage from '../renderPage.js'
import { doApiRequest, formatResponse, LOGIN_URL } from '../utils'
import React from 'react'
import { Router } from '../routes'

class Invite extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      invite: null,
      error: null
    }

    this.accept = this.accept.bind(this)
  }

  componentDidMount() {
    const { query } = this.props
    doApiRequest(`/clubs/${query.club}/invites/${query.invite}/?format=json`).then((resp) => {
      resp.json().then(data => {
        if (resp.ok) {
          this.setState({ invite: data })
        } else if (resp.status === 403 && data.detail === 'Authentication credentials were not provided.') {
          window.location.href = `${LOGIN_URL}?next=${window.location.href}`
        } else {
          this.setState({ error: data })
        }
      })
    })
  }

  accept() {
    const { query } = this.props
    doApiRequest(`/clubs/${query.club}/invites/${query.invite}/?format=json`, {
      method: 'PATCH',
      body: {
        token: query.token
      }
    }).then((resp) => {
      if (resp.ok) {
        Router.pushRoute('club-view', { club: query.club })
      }
    })
  }

  render() {
    const { invite, error } = this.state
    const { userInfo } = this.props

    if (!invite || !invite.id) {
      return <div className='has-text-centered' style={{ margin: 30 }}>
        <h1 className='title is-h1'>404 Not Found</h1>
        <p>The invite you are looking for does not exist. Perhaps it was already claimed?</p>
        <p>{error && formatResponse(error)}</p>
      </div>
    }

    return (
      <div style={{ padding: '30px 50px' }} className='has-text-centered'>
        <h1 className='title is-1'>Accept Invitation</h1>
        <div className='title is-4' style={{ fontWeight: 'normal' }}><b>{invite.name}</b> has invited you, <b>{invite.email}</b>, to join their club.</div>
        <p>By accepting this invitation, you will be able to view the contact information of other members and internal club documents.</p>
        <br /><br />
        <button className='button is-large is-success' onClick={this.accept}>Accept Invitation</button>
      </div>
    )
  }
}

Invite.getInitialProps = async(props) => {
  return { query: props.query }
}

export default renderPage(Invite)
