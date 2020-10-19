const site = process.env.NEXT_PUBLIC_SITE_NAME || 'clubs'

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
    SITE_FAVICON: '/static/favicon.ico',
    SITE_TAGLINE: 'Find your people!',

    APPROVAL_AUTHORITY: 'Office of Student Affairs',
    APPROVAL_AUTHORITY_URL: 'https://osa.vpul.upenn.edu/',

    FIELD_PARTICIPATION_LABEL: 'How to Get Involved',

    OBJECT_URL_SLUG: 'club',
    OBJECT_TAB_MEMBERSHIP_LABEL: 'Membership',
    OBJECT_TAB_RECRUITMENT_LABEL: 'Recruitment',
    OBJECT_TAB_ADMISSION_LABEL: 'Admission',

    CONTACT_EMAIL: 'contact@pennclubs.com',
    FEEDBACK_URL: 'https://airtable.com/shrCsYFWxCwfwE7cf',

    CLUB_FIELDS: [
      'size',
      'founded',
      'github',
      'linkedin',
      'listserv',
      'application_required',
      'accepting_members',
    ],
    SHOW_MEMBERS: true,
    SHOW_MEMBERSHIP_REQUEST: true,

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
    SITE_FAVICON: '/static/penn_favicon.ico',
    SITE_TAGLINE:
      "Find the support resources you need on and around Penn's campus!",

    APPROVAL_AUTHORITY: 'Office of Student Affairs',
    APPROVAL_AUTHORITY_URL: 'https://osa.vpul.upenn.edu/',

    FIELD_PARTICIPATION_LABEL: 'Services Offered',

    OBJECT_URL_SLUG: 'org',
    OBJECT_TAB_MEMBERSHIP_LABEL: 'Admins',
    OBJECT_TAB_RECRUITMENT_LABEL: 'Mailing List',
    OBJECT_TAB_ADMISSION_LABEL: 'Usage',

    CONTACT_EMAIL: 'hub.provost@upenn.edu',
    FEEDBACK_URL: 'https://airtable.com/shrm3UcvjpPEl0qXq',

    CLUB_FIELDS: [
      'appointment_needed',
      'available_virtually',
      'signature_events',
    ],
    SHOW_MEMBERS: false,
    SHOW_MEMBERSHIP_REQUEST: false,

    PARTNER_LOGOS: [
      {
        name: 'Office of Student Affairs',
        image: '/static/img/collaborators/osa.png',
        url: 'https://www.vpul.upenn.edu/osa/',
        className: 'mr-4',
      },
    ],
  },
}

export const SITE_ID = site
export const SITE_NAME = sites[site].SITE_NAME
export const SITE_SUBTITLE = sites[site].SITE_SUBTITLE
export const SITE_TAGLINE = sites[site].SITE_TAGLINE
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

export const FIELD_PARTICIPATION_LABEL = sites[site].FIELD_PARTICIPATION_LABEL
export const OBJECT_URL_SLUG = sites[site].OBJECT_URL_SLUG
export const OBJECT_TAB_MEMBERSHIP_LABEL =
  sites[site].OBJECT_TAB_MEMBERSHIP_LABEL
export const OBJECT_TAB_RECRUITMENT_LABEL =
  sites[site].OBJECT_TAB_RECRUITMENT_LABEL
export const OBJECT_TAB_ADMISSION_LABEL = sites[site].OBJECT_TAB_ADMISSION_LABEL

export const SHOW_MEMBERS = sites[site].SHOW_MEMBERS
export const SHOW_MEMBERSHIP_REQUEST = sites[site].SHOW_MEMBERSHIP_REQUEST

export const PARTNER_LOGOS = sites[site].PARTNER_LOGOS

export const CLUB_FIELDS = new Set(sites[site].CLUB_FIELDS)
export const ALL_CLUB_FIELDS = new Set(
  Object.values(sites)
    .map(({ CLUB_FIELDS }) => CLUB_FIELDS)
    .flat(),
)
