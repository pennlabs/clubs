import getConfig from 'next/config'
import { ReactNode } from 'react'

import { ClubEventType } from '../types'

const { publicRuntimeConfig } = getConfig()
const site = publicRuntimeConfig.NEXT_PUBLIC_SITE_NAME

const sites = {
  clubs: {
    SITE_NAME: 'Penn Clubs',
    SCHOOL_NAME: 'University of Pennsylvania',
    SITE_SUBTITLE: 'Student Organizations at the University of Pennsylvania',
    DOMAIN: 'pennclubs.com',

    OBJECT_NAME_PLURAL: 'clubs',
    OBJECT_NAME_LONG_PLURAL: 'student organizations',
    OBJECT_NAME_SINGULAR: 'club',

    OBJECT_NAME_TITLE: 'Clubs',
    OBJECT_NAME_TITLE_SINGULAR: 'Club',

    SITE_LOGO: '/static/img/peoplelogo.png',
    LOGO_BACKGROUND_IMAGE: null,
    HEADER_BACKGROUND_IMAGE: null,
    HEADER_OVERLAY: null,
    SITE_FAVICON: '/static/favicon.ico',
    SITE_TAGLINE: 'Find your people!',
    OG_IMAGE:
      'https://pennlabs-assets.s3.amazonaws.com/metadata-images/penn-clubs.png',

    APPROVAL_AUTHORITY: 'Office of Student Affairs',
    APPROVAL_AUTHORITY_URL: 'https://osa.vpul.upenn.edu/',

    FIELD_PARTICIPATION_LABEL: 'How to Get Involved',

    OBJECT_URL_SLUG: 'club',
    OBJECT_TAB_MEMBERSHIP_LABEL: 'Membership',
    OBJECT_TAB_RECRUITMENT_LABEL: 'Recruitment',
    OBJECT_TAB_ADMISSION_LABEL: 'Admission',
    OBJECT_TAB_FILES_DESCRIPTION:
      'You can upload club constitutions here. Please upload your club constitution in pdf or docx format.',

    CONTACT_EMAIL: 'contact@pennclubs.com',
    FEEDBACK_URL: 'https://airtable.com/shrCsYFWxCwfwE7cf',

    CLUB_FIELDS: [
      'accepting_members',
      'application_required',
      'badges',
      'email_public',
      'founded',
      'github',
      'linkedin',
      'listserv',
      'mission',
      'recruiting_cycle',
      'size',
      'target_majors',
    ],
    // enable showing members for each club
    SHOW_MEMBERS: true,
    // enable the membership request feature
    SHOW_MEMBERSHIP_REQUEST: true,
    // show the links to the ranking algorithm from various parts of the site
    SHOW_RANK_ALGORITHM: true,
    // show the link to the Penn accessibility help page at the bottom of each page
    SHOW_ACCESSIBILITY: false,
    // show the additional links section on each club
    SHOW_ADDITIONAL_LINKS: true,
    // prompt the user to set inactive instead of leaving the club
    SHOW_LEAVE_CONFIRMATION: true,
    // show the searchbar at the top of the page instead of the sidebar
    SHOW_SEARCHBAR_TOP: false,
    // show applications
    SHOW_APPLICATIONS: true,
    // show feedback icon on bottom right
    SHOW_FEEDBACK: true,

    MEMBERSHIP_ROLE_NAMES: { 0: 'Owner', 10: 'Officer', 20: 'Member' },
    OBJECT_MEMBERSHIP_LABEL: 'Members',
    OBJECT_MEMBERSHIP_LABEL_LOWERCASE: "member's",
    OBJECT_INVITE_LABEL: 'Members',
    OBJECT_EVENT_TYPES: [
      ClubEventType.RECRUITMENT,
      ClubEventType.GBM,
      ClubEventType.SPEAKER,
      ClubEventType.FAIR,
      ClubEventType.OTHER,
    ],

    FORM_DESCRIPTION_EXAMPLES: 'Penn Labs',
    FORM_TAG_DESCRIPTION:
      'You will need to at least specify either the Undergraduate or Graduate tag.',
    FORM_LOGO_DESCRIPTION:
      'Changing this field will require reapproval from the Office of Student Affairs.',
    FORM_TARGET_DESCRIPTION: (
      <>
        <b>Does your club restrict membership to certain student groups?</b> If
        you are only looking for certain student groups during your recruitment
        process, please specify those groups here. Otherwise, we will assume
        that you are targeting the general student population.
      </>
    ),
    OBJECT_MEMBERSHIP_DEFAULT_TITLE: 'Member',
    CLUB_EMPTY_STATE: (
      <>
        Looking for university resources? Check out{' '}
        <a href="https://hub.provost.upenn.edu/">Hub@Penn</a>!
      </>
    ),

    PARTNER_LOGOS: [
      {
        name: 'Student Activities Council',
        image: '/static/img/collaborators/sac.png',
        url: 'https://sacfunded.net/',
      },
      {
        name: 'Undergraduate Assembly',
        image: '/static/img/collaborators/ua.png',
        url: 'https://pennua.org/',
        height: 80,
      },
      {
        name: 'Office of Student Affairs',
        image: '/static/img/collaborators/osa.png',
        url: 'https://www.vpul.upenn.edu/osa/',
        className: 'mr-4',
      },
      {
        name: 'Engineering Student Activities Council',
        image: '/static/img/collaborators/esac.png',
        url: 'https://esac.squarespace.com/',
        height: 80,
      },
    ],

    GA_TRACKING_CODE: 'UA-21029575-14',
  },
  fyh: {
    SITE_NAME: 'Hub@Penn',
    SCHOOL_NAME: 'University of Pennsylvania',
    SITE_SUBTITLE: 'Student Resources at the University of Pennsylvania',
    DOMAIN: 'hub.provost.upenn.edu',

    OBJECT_NAME_PLURAL: 'resources',
    OBJECT_NAME_LONG_PLURAL: 'university resources',
    OBJECT_NAME_SINGULAR: 'resource',

    OBJECT_NAME_TITLE: 'Resources',
    OBJECT_NAME_TITLE_SINGULAR: 'Resource',

    SITE_LOGO: '/static/img/penn_shield.png',
    LOGO_BACKGROUND_IMAGE: '/static/img/penn_header_fade.png',
    HEADER_BACKGROUND_IMAGE: '/static/img/hub_banner.png',
    HEADER_OVERLAY: '/static/img/platform-start-point.png',
    SITE_FAVICON: '/static/penn_favicon.ico',
    SITE_TAGLINE:
      "Find the support resources you need on and around Penn's campus!",
    OG_IMAGE:
      'https://pennlabs-assets.s3.amazonaws.com/metadata-images/hub-at-penn.png',

    APPROVAL_AUTHORITY: 'Hub@Penn administrators',
    APPROVAL_AUTHORITY_URL: '/faq',

    FIELD_PARTICIPATION_LABEL: 'Services Offered',

    OBJECT_URL_SLUG: 'org',
    OBJECT_TAB_MEMBERSHIP_LABEL: 'Admins',
    OBJECT_TAB_RECRUITMENT_LABEL: 'Mailing List',
    OBJECT_TAB_ADMISSION_LABEL: 'Usage',
    OBJECT_TAB_FILES_DESCRIPTION: null,
    OBJECT_EVENT_TYPES: [
      ClubEventType.SOCIAL,
      ClubEventType.CAREER,
      ClubEventType.SPEAKER,
      ClubEventType.FAIR,
      ClubEventType.OTHER,
    ],

    CONTACT_EMAIL: 'hub.provost@upenn.edu',
    FEEDBACK_URL: 'https://airtable.com/shrv4RfYIddU1i9o6',

    CLUB_FIELDS: [
      'appointment_needed',
      'available_virtually',
      'signature_events',
      'student_types',
    ],
    SHOW_MEMBERS: false,
    SHOW_MEMBERSHIP_REQUEST: false,
    SHOW_RANK_ALGORITHM: false,
    SHOW_ACCESSIBILITY: true,
    SHOW_ADDITIONAL_LINKS: false,
    SHOW_LEAVE_CONFIRMATION: false,
    SHOW_SEARCHBAR_TOP: true,
    SHOW_APPLICATIONS: false,
    SHOW_FEEDBACK: false,

    MEMBERSHIP_ROLE_NAMES: { 0: 'Owner', 10: 'Editor' },
    OBJECT_MEMBERSHIP_LABEL: 'Staff',
    OBJECT_MEMBERSHIP_LABEL_LOWERCASE: 'staff',
    OBJECT_INVITE_LABEL: 'Editor',

    FORM_DESCRIPTION_EXAMPLES:
      'Office of New Student Orientation & Academic Initiative - NSOAI',
    FORM_TAG_DESCRIPTION:
      'Tags will allow students to find your resource while filtering Hub@Penn. Select as many as apply.',
    FORM_LOGO_DESCRIPTION: 'Upload your approved Penn logo.',
    FORM_TARGET_DESCRIPTION: (
      <>
        <b>Do you offer specialized services for particular student groups?</b>{' '}
        It is assumed that all resources at Penn are available to all Penn
        students. However, if you offer specialized resources, please designate
        the groups that receive those resources here.
      </>
    ),
    OBJECT_MEMBERSHIP_DEFAULT_TITLE: '',
    CLUB_EMPTY_STATE: (
      <>
        Looking for student organizations? Check out{' '}
        <a href="https://pennclubs.com/">Penn Clubs</a>!
      </>
    ),

    PARTNER_LOGOS: [
      {
        name: 'Vice Provost for University Life',
        image: '/static/img/collaborators/vpul.png',
        url: 'https://home.vpul.upenn.edu/',
        className: 'mr-4 mb-4',
      },
      {
        name: 'New Student Orientation and Academic Initatives',
        image: '/static/img/collaborators/nsoai.png',
        url: 'https://www.nso.upenn.edu/',
        className: 'mr-4 mb-4',
      },
    ],

    GA_TRACKING_CODE: 'UA-21029575-19',
  },
}

export const SITE_ID = site
export const SITE_NAME = sites[site].SITE_NAME
export const SITE_SUBTITLE = sites[site].SITE_SUBTITLE
export const SITE_TAGLINE = sites[site].SITE_TAGLINE
export const OG_IMAGE = sites[site].OG_IMAGE
export const SCHOOL_NAME = sites[site].SCHOOL_NAME
export const DOMAIN = sites[site].DOMAIN
export const CONTACT_EMAIL = sites[site].CONTACT_EMAIL
export const FEEDBACK_URL = sites[site].FEEDBACK_URL

export const OBJECT_NAME_PLURAL = sites[site].OBJECT_NAME_PLURAL
export const OBJECT_NAME_LONG_PLURAL = sites[site].OBJECT_NAME_LONG_PLURAL
export const OBJECT_NAME_SINGULAR = sites[site].OBJECT_NAME_SINGULAR

export const OBJECT_NAME_TITLE = sites[site].OBJECT_NAME_TITLE
export const OBJECT_NAME_TITLE_SINGULAR = sites[site].OBJECT_NAME_TITLE_SINGULAR

export const APPROVAL_AUTHORITY = sites[site].APPROVAL_AUTHORITY
export const APPROVAL_AUTHORITY_URL = sites[site].APPROVAL_AUTHORITY_URL

export const SITE_LOGO = sites[site].SITE_LOGO
export const SITE_FAVICON = sites[site].SITE_FAVICON
export const LOGO_BACKGROUND_IMAGE = sites[site].LOGO_BACKGROUND_IMAGE
export const HEADER_BACKGROUND_IMAGE = sites[site].HEADER_BACKGROUND_IMAGE
export const HEADER_OVERLAY = sites[site].HEADER_OVERLAY

export const FIELD_PARTICIPATION_LABEL = sites[site].FIELD_PARTICIPATION_LABEL
export const OBJECT_URL_SLUG = sites[site].OBJECT_URL_SLUG
export const OBJECT_TAB_MEMBERSHIP_LABEL =
  sites[site].OBJECT_TAB_MEMBERSHIP_LABEL
export const OBJECT_TAB_RECRUITMENT_LABEL =
  sites[site].OBJECT_TAB_RECRUITMENT_LABEL
export const OBJECT_TAB_ADMISSION_LABEL = sites[site].OBJECT_TAB_ADMISSION_LABEL
export const OBJECT_TAB_FILES_DESCRIPTION =
  sites[site].OBJECT_TAB_FILES_DESCRIPTION

export const SHOW_MEMBERS = sites[site].SHOW_MEMBERS
export const SHOW_MEMBERSHIP_REQUEST = sites[site].SHOW_MEMBERSHIP_REQUEST
export const SHOW_RANK_ALGORITHM = sites[site].SHOW_RANK_ALGORITHM
export const MEMBERSHIP_ROLE_NAMES: { [key: number]: string } =
  sites[site].MEMBERSHIP_ROLE_NAMES
export const SHOW_ACCESSIBILITY = sites[site].SHOW_ACCESSIBILITY
export const SHOW_ADDITIONAL_LINKS = sites[site].SHOW_ADDITIONAL_LINKS
export const SHOW_LEAVE_CONFIRMATION = sites[site].SHOW_LEAVE_CONFIRMATION
export const SHOW_SEARCHBAR_TOP = sites[site].SHOW_SEARCHBAR_TOP
export const SHOW_APPLICATIONS = sites[site].SHOW_APPLICATIONS
export const SHOW_FEEDBACK = sites[site].SHOW_FEEDBACK

export const OBJECT_MEMBERSHIP_LABEL = sites[site].OBJECT_MEMBERSHIP_LABEL
export const OBJECT_MEMBERSHIP_LABEL_LOWERCASE =
  sites[site].OBJECT_MEMBERSHIP_LABEL_LOWERCASE
export const OBJECT_MEMBERSHIP_DEFAULT_TITLE =
  sites[site].OBJECT_MEMBERSHIP_DEFAULT_TITLE
export const OBJECT_EVENT_TYPES = new Set(sites[site].OBJECT_EVENT_TYPES)
export const CLUB_EMPTY_STATE = sites[site].CLUB_EMPTY_STATE

export const PARTNER_LOGOS = sites[site].PARTNER_LOGOS

export const CLUB_FIELDS = new Set(sites[site].CLUB_FIELDS)
export const ALL_CLUB_FIELDS = new Set(
  Object.values(sites)
    .map(({ CLUB_FIELDS }) => CLUB_FIELDS)
    .flat(),
)

export const GA_TRACKING_CODE = sites[site].GA_TRACKING_CODE

export const FORM_DESCRIPTION_EXAMPLES: ReactNode =
  sites[site].FORM_DESCRIPTION_EXAMPLES
export const FORM_TAG_DESCRIPTION: ReactNode = sites[site].FORM_TAG_DESCRIPTION
export const FORM_LOGO_DESCRIPTION: ReactNode =
  sites[site].FORM_LOGO_DESCRIPTION
export const FORM_TARGET_DESCRIPTION: ReactNode =
  sites[site].FORM_TARGET_DESCRIPTION

export const OBJECT_INVITE_LABEL = sites[site].OBJECT_INVITE_LABEL
