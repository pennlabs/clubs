import getConfig from 'next/config'
import fetch from 'isomorphic-unfetch'

export function stripTags(val) {
  if (!val) {
    return val
  }
  return val
    .replace(/(<[^>]+>)/gi, '')
    .replace('&amp;', '&')
    .replace('&lt;', '<')
    .replace('&gt;', '>')
    .replace('&ndash;', '-')
    .replace('&mdash;', '-')
    .trim()
}

export function getDefaultClubImageURL() {
  return '/static/img/hatlogo.png'
}

function removeEndingSlash(val) {
  if (typeof val !== 'string') {
    return val
  }
  if (val.endsWith('/')) {
    return val.substring(0, val.length - 1)
  }
  return val
}

export const DEFAULT_SITE_ORIGIN = process.env.NODE_ENV === 'production' ? 'https://pennclubs.com' : `http://localhost:${process.env.PORT || 3000}`
export const SITE_ORIGIN = removeEndingSlash(getConfig().publicRuntimeConfig.API_BASE_URL) || DEFAULT_SITE_ORIGIN
export const API_BASE_URL = `${SITE_ORIGIN}/api`
export const ROLE_OWNER = 0
export const ROLE_OFFICER = 10
export const ROLE_MEMBER = 20

export const EMPTY_DESCRIPTION =
  '<span style="color:#666">This club has not added a description yet.</span>'
export const LOGIN_URL = `${API_BASE_URL}/accounts/login/`
export const LOGOUT_URL = `${API_BASE_URL}/accounts/logout/`

export function getSizeDisplay(size, showMembersLabel = true) {
  const postfix = showMembersLabel ? ' Members' : ''
  if (size === 1) return '< 20' + postfix
  else if (size === 2) return '20 - 50' + postfix
  else if (size === 3) return '50 - 100' + postfix
  else if (size === 4) return '> 100' + postfix
  else return 'Unknown'
}

export function getRoleDisplay(role) {
  if (role <= 0) return 'Owner'
  else if (role <= 10) return 'Officer'
  else return 'Member'
}

export function getApiUrl(path) {
  return API_BASE_URL + path
}

export function doApiRequest(path, data) {
  if (!data) {
    data = {}
  }
  data.credentials = 'include'
  if (typeof document !== 'undefined') {
    data.headers = data.headers || {}
    if (!(data.body instanceof FormData)) {
      data.headers['Content-Type'] = 'application/json'
    }
    data.headers['X-CSRFToken'] = (/csrftoken=(\w+)/.exec(document.cookie) || [
      null,
      null,
    ])[1]
  }
  if (data.body && !(data.body instanceof FormData)) {
    data.body = JSON.stringify(data.body)
  }
  return fetch(getApiUrl(path), data)
}

export function titleize(str) {
  if (!str) return str
  return str
    .replace(/_/g, ' ')
    .split(' ')
    .map(a => a[0].toUpperCase() + a.substr(1).toLowerCase())
    .join(' ')
}

export function formatResponse(err) {
  return Object.keys(err).map(a => (
    <div key={a}>
      <b>{titleize(a)}:</b> {err[a]}
    </div>
  ))
}
