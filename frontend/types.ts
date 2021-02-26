/* eslint-disable camelcase */
export enum MembershipRank {
  Owner = 0,
  Officer = 10,
  Member = 20,
}

export interface MembershipRole {
  value: number
  label: string
}

export interface Report {
  id: number
  name: string
  creator: string
  description: string
  public: boolean
  created_at: string
  updated_at: string
  parameters: string
}

export interface Membership {
  name: string
  title: string
  role: MembershipRank
  active: boolean
  public: boolean
  image: string | null
  email: string
  username: string
}

export interface Testimonial {
  id: number
  text: string
}

export enum ClubEventType {
  OTHER = 0,
  RECRUITMENT = 1,
  GBM = 2,
  SPEAKER = 3,
  FAIR = 4,
  SOCIAL = 5,
  CAREER = 6,
}

export interface ClubEvent {
  badges: Badge[]
  club: string | null
  club_name: string | null
  description: string
  end_time: string
  id: number
  image_url: string | null
  is_ics_event: boolean
  large_image_url: string | null
  location: string | null
  name: string
  pinned: boolean
  start_time: string
  type: ClubEventType
  url: string | null
}

export interface ClubApplication {
  id: number
  name: string
  application_start_time: string
  application_end_time: string
  result_release_time: string
  external_url: string
}

export enum ClubSize {
  Small = 1,
  Medium = 2,
  Large = 3,
  VeryLarge = 4,
}

export enum ClubApplicationRequired {
  Open = 1,
  Tryout = 2,
  Audition = 3,
  Application = 4,
  ApplicationAndInterview = 5,
}

export enum ClubRecruitingCycle {
  Unknown = 1,
  Fall = 2,
  Spring = 3,
  Both = 4,
  Open = 5,
}

export interface Tag {
  id: number
  name: string
  clubs?: number
}

export interface Badge {
  id: number
  label: string
  color: string
  purpose: string
  description: string
}

export interface QuestionAnswer {
  id: number
  approved: boolean
  question: string
  answer: string
  author: string
  responder: string
}

export interface Advisor {
  id: number
  name: string
  title: string
  department: string
  email: string
  phone: string
  public: boolean
}

export interface Club {
  accepting_members: boolean
  active: boolean
  advisor_set: Advisor[]
  application_required: ClubApplicationRequired
  appointment_needed: boolean
  approved: boolean | null
  approved_by: string | null
  approved_comment: string | null
  available_virtually: boolean
  badges: Badge[]
  code: string
  description: string
  email: string
  enables_subscription: boolean
  events: ClubEvent[]
  facebook: string
  fairs: number[]
  favorite_count: number
  files: File[]
  github: string
  how_to_get_involved: string
  ics_import_url: string
  image_url: string
  instagram: string
  is_favorite: boolean
  is_ghost: boolean
  is_member: MembershipRank | false
  is_request: boolean
  is_subscribe: boolean
  linkedin: string
  listserv: string
  members: Membership[]
  membership_count: number
  mission: string
  name: string
  recruiting_cycle: ClubRecruitingCycle
  signature_events: string
  size: ClubSize
  student_types: StudentType[]
  subtitle: string
  tags: Tag[]
  target_majors: Major[]
  target_schools: School[]
  target_years: Year[]
  testimonials: Testimonial[]
  twitter: string
  website: string
}

export interface ClubFair {
  id: number
  name: string
  organization: string
  contact: string
  time: string

  information: string
  registration_information: string
  registration_start_time: string | null
  registration_end_time: string

  start_time: string
  end_time: string

  questions: string
}

export interface File {
  id: number
  name: string
  created_at: string
  file_url: string
}

export interface UserInfo {
  email: string
  graduation_year: number
  has_been_prompted: boolean
  image_url: string
  is_superuser: boolean
  major: Major[]
  name: string
  school: School[]
  share_bookmarks: boolean
  show_profile: boolean
  username: string
}

export interface UserProfile {
  clubs: (Club & {
    membership: { active: boolean; title: string; role: number }
  })[]
  email: string
  graduation_year: number | null
  image_url: string | null
  major: Major[]
  name: string
  public: boolean
  school: School[]
  username: string
}

export type UserMembership = {
  club: Club
  role: MembershipRank
  title: string
  active: boolean
  public: boolean
}

export interface ExtendedUserInfo extends UserInfo {
  membership_set: {
    code: string
    role: MembershipRank
  }[]
  subscribe_set: { club: string }[]
  favorite_set: { club: string }[]
}

export interface School {
  id: number
  name: string
  is_graduate: boolean
}

export interface Major {
  id: number
  name: string
}

export interface Year {
  id: number
  name: string
  year: number
}

export interface StudentType {
  id: number
  name: string
}

export enum VisitType {
  ClubPage = 1,
  EventModal = 2,
  EventLink = 3,
  ManagePage = 4,
  FairPage = 5,
}

export type DynamicQuestion = {
  name: string
  label: string
  type: string
  choices?: { id: string; label: string }[]
}
