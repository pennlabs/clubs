from django.urls import include, path
from rest_framework_nested import routers

from clubs.views import (
    AdvisorViewSet,
    ApplicationQuestionViewSet,
    AssetViewSet,
    BadgeClubViewSet,
    BadgeViewSet,
    ClubApplicationViewSet,
    ClubEventViewSet,
    ClubFairViewSet,
    ClubViewSet,
    ClubVisitViewSet,
    EmailInvitesAPIView,
    EventViewSet,
    ExternalMemberListViewSet,
    FavoriteCalendarAPIView,
    FavoriteViewSet,
    MajorViewSet,
    MassInviteAPIView,
    MeetingZoomAPIView,
    MeetingZoomWebhookAPIView,
    MemberInviteViewSet,
    MembershipRequestOwnerViewSet,
    MembershipRequestViewSet,
    MembershipViewSet,
    MemberViewSet,
    NoteViewSet,
    OptionListView,
    QuestionAnswerViewSet,
    ReportViewSet,
    SchoolViewSet,
    ScriptExecutionView,
    SearchQueryViewSet,
    StudentTypeViewSet,
    SubscribeViewSet,
    TagViewSet,
    TestimonialViewSet,
    UserGroupAPIView,
    UserPermissionAPIView,
    UserUpdateAPIView,
    UserUUIDAPIView,
    UserViewSet,
    UserZoomAPIView,
    YearViewSet,
    email_preview,
)


router = routers.SimpleRouter()
router.register(r"clubs", ClubViewSet, basename="clubs")
router.register(r"clubfairs", ClubFairViewSet, basename="clubfairs")
router.register(r"events", EventViewSet, basename="events")
router.register(r"tags", TagViewSet, basename="tags")
router.register(r"badges", BadgeViewSet, basename="badges")
router.register(r"favorites", FavoriteViewSet, basename="favorites")
router.register(r"subscriptions", SubscribeViewSet, basename="subscribes")
router.register(r"clubvisits", ClubVisitViewSet, basename="clubvisits")
router.register(r"searches", SearchQueryViewSet, basename="searches")
router.register(r"memberships", MembershipViewSet, basename="members")
router.register(r"requests", MembershipRequestViewSet, basename="requests")

router.register(r"schools", SchoolViewSet, basename="schools")
router.register(r"majors", MajorViewSet, basename="majors")
router.register(r"student_types", StudentTypeViewSet, basename="student_types"),
router.register(r"reports", ReportViewSet, basename="reports")
router.register(r"years", YearViewSet, basename="years")
router.register(r"users", UserViewSet, basename="users")
router.register(
    r"external/members/(?P<code>.+)", ExternalMemberListViewSet, basename="external"
)

clubs_router = routers.NestedSimpleRouter(router, r"clubs", lookup="club")
clubs_router.register(r"members", MemberViewSet, basename="club-members")
clubs_router.register(r"events", ClubEventViewSet, basename="club-events")
clubs_router.register(r"invites", MemberInviteViewSet, basename="club-invites")
clubs_router.register(r"assets", AssetViewSet, basename="club-assets")
clubs_router.register(r"notes", NoteViewSet, basename="club-notes")
clubs_router.register(r"testimonials", TestimonialViewSet, basename="club-testimonials")
clubs_router.register(r"questions", QuestionAnswerViewSet, basename="club-questions")
clubs_router.register(
    r"membershiprequests",
    MembershipRequestOwnerViewSet,
    basename="club-membership-requests",
)
clubs_router.register(r"advisors", AdvisorViewSet, basename="club-advisors")
clubs_router.register(
    r"applications", ClubApplicationViewSet, basename="club-applications"
)

badges_router = routers.NestedSimpleRouter(router, r"badges", lookup="badge")
badges_router.register(r"clubs", BadgeClubViewSet, basename="badge-clubs")

applications_router = routers.NestedSimpleRouter(
    clubs_router, r"applications", lookup="application"
)
applications_router.register(
    r"questions", ApplicationQuestionViewSet, basename="club-application-questions"
)

urlpatterns = [
    path(r"settings/", UserUpdateAPIView.as_view(), name="settings-detail"),
    path(r"settings/invites/", EmailInvitesAPIView.as_view(), name="email-invites"),
    path(r"settings/zoom/", UserZoomAPIView.as_view(), name="users-zoom"),
    path(
        r"settings/zoom/meetings/",
        MeetingZoomAPIView.as_view(),
        name="users-zoom-meeting",
    ),
    path(
        r"settings/permissions/",
        UserPermissionAPIView.as_view(),
        name="users-permission",
    ),
    path(r"settings/groups/", UserGroupAPIView.as_view(), name="users-group"),
    path(
        r"clubs/<slug:club_code>/invite/",
        MassInviteAPIView.as_view(),
        name="club-invite",
    ),
    path(r"settings/calendar_url/", UserUUIDAPIView.as_view(), name="user-uuid"),
    path(
        r"calendar/<slug:user_secretuuid>/",
        FavoriteCalendarAPIView.as_view(),
        name="favorites-calendar",
    ),
    path(r"emailpreview/", email_preview, name="email-preview"),
    path(r"scripts/", ScriptExecutionView.as_view(), name="scripts"),
    path(r"options/", OptionListView.as_view(), name="options"),
    path(r"social/", include("social_django.urls", namespace="social")),
    path(
        r"webhook/meeting/",
        MeetingZoomWebhookAPIView.as_view(),
        name="webhooks-meeting",
    ),
]

urlpatterns += router.urls
urlpatterns += clubs_router.urls
urlpatterns += badges_router.urls
urlpatterns += applications_router.urls
