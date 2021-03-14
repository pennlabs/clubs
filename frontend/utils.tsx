import fetch from 'isomorphic-unfetch'
import LRU from 'lru-cache'
import { NextPageContext } from 'next'
import getConfig from 'next/config'
import React, { createContext, ReactElement, useContext } from 'react'

import { MembershipRank } from './types'
import {
  ALL_CLUB_FIELDS,
  CLUB_FIELDS,
  MEMBERSHIP_ROLE_NAMES,
} from './utils/branding'

const dev = process.env.NODE_ENV !== 'production'

/**
 * Returns true if this is a development environment, or false otherwise.
 */
export function isDevelopment(): boolean {
  return dev
}

const internalCache = new LRU()

/**
 * Cache the return value of a function.
 * This should only be used with publically available information.
 * The time should be specified in milliseconds.
 */
export async function cache<T>(
  key: string,
  func: () => Promise<T>,
  time: number,
): Promise<T> {
  const cached = internalCache.get(key)
  if (cached != null) {
    return cached
  }
  const val = await func()
  internalCache.set(key, val, time)
  return val
}

export function stripTags(val: string): string {
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
    .replace('&nbsp;', ' ')
    .trim()
}

export const OptionsContext = createContext({})

/**
 * A react hook that returns the value of a Django runtime option setting.
 * If the setting is still loading, returns null.
 * @param key The setting to retrieve.
 */
export function useSetting(key: string): string | number | boolean | null {
  const options = useContext(OptionsContext)
  const value = options[key] ?? null
  if (value === 'true') {
    return true
  }
  if (value === 'false') {
    return false
  }
  return value
}

export function getCurrentRelativePath(): string {
  return (
    window.location.pathname + window.location.search + window.location.hash
  )
}

export function getDefaultClubImageURL(): string {
  return '/static/img/hatlogo.png'
}

const { publicRuntimeConfig } = getConfig()

export const SITE_ORIGIN = publicRuntimeConfig.SITE_ORIGIN
export const API_BASE_URL = `${SITE_ORIGIN}/api`

export const EMPTY_DESCRIPTION =
  '<span style="color:#666">This club has not added a description yet.</span>'
  export const EMPTY_MISSION =
  '<span style="color:#666">This club has not added a mission yet.</span>'
export const LOGIN_URL = `${API_BASE_URL}/accounts/login/`
export const LOGOUT_URL = `${API_BASE_URL}/accounts/logout/`

export function getSizeDisplay(size: number, showMembersLabel = true): string {
  const postfix = showMembersLabel ? ' Members' : ''
  if (size === 1) return '< 20' + postfix
  else if (size === 2) return '20 - 50' + postfix
  else if (size === 3) return '50 - 100' + postfix
  else if (size === 4) return '> 100' + postfix
  else return 'Unknown'
}

export function getRoleDisplay(role: MembershipRank): string {
  return MEMBERSHIP_ROLE_NAMES[role] ?? 'Unknown'
}

export function getApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    const url = new URL(path)
    return url.pathname + url.search
  }
  return API_BASE_URL + path
}

export const PermissionsContext = React.createContext<{
  [key: string]: boolean | null
}>({})

/**
 * Prefetch some permissions for the current page.
 * Should be executed at the start of each page with permissions.
 */
export async function preloadPermissions(
  permissions: string[],
): Promise<{ [key: string]: boolean | null }> {
  const resp = await doApiRequest(
    `/settings/permissions/?perm=${encodeURIComponent(
      permissions.join(','),
    )}&format=json`,
  )
  if (!resp.ok) {
    return {}
  }
  return (await resp.json()).permissions
}

/**
 * Check if the user has a Django permission.
 * If you were checking for the "clubs.approve_club" permission, pass the
 * string "clubs.approve_club".
 *
 * If you are checking for a permission that is object based, separate the
 * object identiifer with a colon. For example, "permission:object_id".
 */
export function apiCheckPermission(
  permission: string | string[],
  failSilently?: boolean,
): boolean | null {
  const perms = useContext(PermissionsContext)

  if (Array.isArray(permission)) {
    return permission.some((perm) => perm in perms && perms[perm])
  }

  if (permission in perms) {
    return perms[permission]
  }

  if (failSilently) {
    return false
  }

  // warn the developer that they should preload the permission
  const msg = `The permission '${permission}' was not preloaded on this page. You should preload this permission for efficiency purposes. Loaded permissions: ${JSON.stringify(
    perms,
  )}`
  if (isDevelopment()) {
    throw new Error(msg)
  }

  // in production, return false and hope for the best
  return false
}

/**
 * Lookup a lot of endpoints asynchronously.
 * Should be used primarily by getInitialProps methods.
 */
export async function doBulkLookup(
  paths: ([string, string] | string)[],
  ctx?: NextPageContext,
): Promise<{ [key: string]: any }> {
  const data =
    ctx != null
      ? {
          headers: ctx.req ? { cookie: ctx.req.headers.cookie } : undefined,
        }
      : undefined

  const resps = await Promise.all(
    paths.map((item) =>
      doApiRequest(
        typeof item === 'string' ? `/${item}/?format=json` : item[1],
        data,
      ).then(async (resp) => {
        const contents = await resp.text()
        try {
          return JSON.parse(contents)
        } catch (e) {
          // eslint-disable-next-line no-console
          console.error(`Body contents of failed JSON parsing: ${contents}`)
          throw e
        }
      }),
    ),
  )

  const output = {}
  for (let i = 0; i < paths.length; i++) {
    output[typeof paths[i] === 'string' ? (paths[i] as string) : paths[i][0]] =
      resps[i]
  }

  return output
}

/**
 * Perform an API request to the Django backend server.
 * @param path The path to the REST endpoint, excluding the /api/ component.
 * @param data Additional fetch data to be passed in the request.
 */
export function doApiRequest(
  path: string,
  data?: Omit<RequestInit, 'body' | 'headers'> & {
    body?: FormData | any
    headers?: { [key: string]: string | null | void }
  },
): Promise<Response> {
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
  return fetch(getApiUrl(path), data as RequestInit)
}

export function apiSetFavoriteStatus(
  club: string,
  favorited: boolean,
): Promise<void> {
  if (favorited) {
    return doApiRequest('/favorites/?format=json', {
      method: 'POST',
      body: { club: club },
    }).then(() => undefined)
  } else {
    return doApiRequest(`/favorites/${club}/?format=json`, {
      method: 'DELETE',
    }).then(() => undefined)
  }
}

export function apiSetSubscribeStatus(
  club: string,
  subscribed: boolean,
): Promise<void> {
  if (subscribed) {
    return doApiRequest('/subscriptions/?format=json', {
      method: 'POST',
      body: {
        club: club,
      },
    }).then(() => undefined)
  } else {
    return doApiRequest(`/subscriptions/${club}/?format=json`, {
      method: 'DELETE',
    }).then(() => undefined)
  }
}

/**
 * Convert underscores into spaces and capitalize the first letter of every word.
 */
export function titleize(str: string): string {
  if (!str) return str
  return str
    .replace(/_+/g, ' ')
    .split(' ')
    .map((a) => a[0].toUpperCase() + a.substr(1).toLowerCase())
    .join(' ')
}

/**
 * Given a dictionary that you want to display to the user, converts this
 * dictionary into a displayable list of key value pairs.
 */
export function formatResponse(
  err: { [key: string]: string } | string,
): ReactElement {
  if (typeof err === 'string') {
    return <>{err}</>
  }

  return (
    <>
      {Object.keys(err)
        .filter(
          (line) => !(line === 'success' && typeof err[line] === 'boolean'),
        )
        .filter((line) => !(typeof err[line] === 'number'))
        .map((line) => (
          <div key={line}>
            <b>{titleize(line)}:</b> {err[line]}
          </div>
        ))}
    </>
  )
}

/**
 * Indicates whether a field is shown on the edit page
 * and the club information page.
 *
 * Looks up information from current branding to see which
 * fields should be displayed.
 */
export function isClubFieldShown(name: string): boolean {
  if (ALL_CLUB_FIELDS.has(name) && !CLUB_FIELDS.has(name)) {
    return false
  }
  return true
}

/**
 * Attempt to format a phone number in US phone number format.
 */
export function formatPhoneNumber(phone: string): string {
  const cleaned = ('' + phone).replace(/\D/g, '')
  const match = cleaned.match(/^(1|)?(\d{3})(\d{3})(\d{4})$/)
  if (match) {
    const intlCode = match[1] ? '+1 ' : ''
    return [intlCode, '(', match[2], ') ', match[3], '-', match[4]].join('')
  }
  return phone
}

/**
 * Add an element between each element in an array.
 * @param arr The array of elements to join together.
 * @param sep A string or function that accepts a key argument (for react lists), inserted between each element in the array.
 */
export function intersperse<T, U>(
  arr: T[],
  sep: string | ((idx: number) => U),
): (T | U | string)[] {
  if (arr.length === 0) {
    return []
  }

  return arr.slice(1).reduce(
    (xs: (T | U | string)[], x: T, idx: number) => {
      return xs.concat([typeof sep !== 'string' ? sep(idx) : sep, x])
    },
    [arr[0]],
  )
}

/**
 * Return the starting year of the current school year that we are in.
 * For example, if we are in Fall 2019 or Spring 2020, the current school year should be 2019.
 */
export function getCurrentSchoolYear(): number {
  const now = new Date()
  let year = now.getFullYear()
  if (now.getMonth() < 6) {
    year -= 1
  }
  return year
}

/**
 * Given a date, return a semester string corresponding to that date.
 * For example, if 1/8/2021 was passed in, the return result should be "Spring 2021".
 * Does not support the summer semester.
 */
export function getSemesterFromDate(date: Date | string): string {
  if (typeof date === 'string') {
    date = new Date(date)
  }

  const year = date.getFullYear()
  const sem = date.getMonth() >= 6 ? 'Fall' : 'Spring'
  return `${sem} ${year}`
}
