import re

import simple_history
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.db.models import Count, Exists, OuterRef
from django.utils import timezone
from django.utils.safestring import mark_safe

from clubs.management.commands.merge_duplicates import merge_clubs, merge_tags
from clubs.management.commands.remind import send_reminder_to_club
from clubs.models import (
    Advisor,
    ApplicationQuestion,
    ApplicationQuestionResponse,
    Asset,
    Badge,
    Club,
    ClubApplication,
    ClubFair,
    ClubFairRegistration,
    ClubVisit,
    Event,
    Favorite,
    Major,
    Membership,
    MembershipInvite,
    MembershipRequest,
    Note,
    NoteTag,
    Profile,
    QuestionAnswer,
    RecurringEvent,
    Report,
    School,
    SearchQuery,
    StudentType,
    Subscribe,
    Tag,
    TargetMajor,
    TargetSchool,
    TargetStudentType,
    TargetYear,
    Testimonial,
    Year,
    ZoomMeetingVisit,
)


class HasOwnerListFilter(admin.SimpleListFilter):
    title = "has owner"
    parameter_name = "has_owner"

    def lookups(self, request, model_admin):
        return [("true", "True"), ("false", "False")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(has_owner=val == "true")
        else:
            return queryset


class HasInviteListFilter(admin.SimpleListFilter):
    title = "has invite"
    parameter_name = "has_invite"

    def lookups(self, request, model_admin):
        return [("true", "True"), ("false", "False")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(has_invite=val == "true")
        else:
            return queryset


def do_merge_clubs(modeladmin, request, queryset):
    if queryset.count() < 2:
        modeladmin.message_user(
            request,
            "You must select at least two clubs to merge!",
            level=messages.ERROR,
        )
        return
    if queryset.count() > 5:
        modeladmin.message_user(
            request,
            "You have selected more than 5 clubs, "
            "you probably do not want to do this.",
            level=messages.ERROR,
        )
        return
    club_names = list(queryset.order_by("name").values_list("name", flat=True))
    tags = list(queryset)
    first, rest = tags[0], tags[1:]
    for club in rest:
        merge_clubs(first, club)
    modeladmin.message_user(
        request,
        "Merged the following clubs: {} into {}".format(
            ", ".join(club_names), first.name
        ),
        level=messages.SUCCESS,
    )


do_merge_clubs.short_description = "Merge selected clubs"


def send_edit_reminder(modeladmin, request, queryset):
    success_count = 0
    total_count = 0
    for club in queryset.order_by("code"):
        if send_reminder_to_club(club):
            success_count += 1
        total_count += 1
    modeladmin.message_user(
        request,
        "Sent edit page reminder emails to {}/{} club(s).".format(
            success_count, total_count
        ),
        level=messages.SUCCESS,
    )


send_edit_reminder.short_description = "Send edit page reminder"


def mark_approved(modeladmin, request, queryset):
    if not request.user.has_perm("clubs.approve_club"):
        modeladmin.message_user(
            request,
            "You do not have permission to approve clubs!",
            level=messages.ERROR,
        )
        return

    num_updated = queryset.filter(approved=False).update(
        approved=True, approved_by=request.user, approved_on=timezone.now()
    )
    modeladmin.message_user(
        request,
        "Marked {} club(s) as approved!".format(num_updated),
        level=messages.SUCCESS,
    )


mark_approved.short_description = "Approve clubs"


class ClubAdminForm(forms.ModelForm):
    parent_orgs = forms.ModelMultipleChoiceField(
        queryset=Club.objects.annotate(num_children=Count("children_orgs")).order_by(
            "-num_children"
        ),
        required=False,
    )


class ClubChildrenInline(TabularInline):
    model = Club.children_orgs.through
    fk_name = "to_club"
    extra = 0
    verbose_name = "Children org"
    verbose_name_plural = "Children orgs"


class ClubAdmin(simple_history.admin.SimpleHistoryAdmin):
    search_fields = ("name", "subtitle", "email", "code")
    list_display = ("name", "email", "has_owner", "has_invite", "active", "approved")
    list_filter = (
        "size",
        "application_required",
        "accepting_members",
        "enables_subscription",
        "recruiting_cycle",
        "active",
        "approved",
        HasOwnerListFilter,
        HasInviteListFilter,
    )
    inlines = [ClubChildrenInline]
    actions = [do_merge_clubs, send_edit_reminder, mark_approved]
    form = ClubAdminForm

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                has_owner=Exists(
                    Membership.objects.filter(club=OuterRef("pk"), role__lte=0)
                ),
                has_invite=Exists(MembershipInvite.objects.filter(club=OuterRef("pk"))),
            )
        )

    def has_invite(self, obj):
        return obj.has_invite

    has_invite.boolean = True

    def has_owner(self, obj):
        return obj.has_owner

    has_owner.boolean = True


class ClubFairAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "contact", "start_time")
    search_fields = ("name", "organization", "contact")
    list_filter = ("start_time", "end_time")


class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "type", "start_time", "end_time")
    search_fields = ("name", "club__name")
    list_filter = ("start_time", "end_time")

    def club(self, obj):
        return obj.club.name


class FavoriteAdmin(admin.ModelAdmin):
    search_fields = ("person__username", "person__email", "club__name", "club__pk")
    list_display = ("person", "club")

    def person(self, obj):
        return obj.person.username

    def club(self, obj):
        return obj.club.name


class SubscribeAdmin(admin.ModelAdmin):
    search_fields = ("person__username", "person__email", "club__name", "club__pk")
    list_display = ("person", "club", "email")

    def person(self, obj):
        return obj.person.username

    def club(self, obj):
        return obj.club.name

    def email(self, obj):
        return obj.person.email


class MembershipRequestAdmin(admin.ModelAdmin):
    search_fields = ("person__username", "person__email", "club__name", "club__pk")
    list_display = ("person", "club", "email", "withdrew", "is_member")
    list_filter = ("withdrew",)

    def person(self, obj):
        return obj.person.username

    def club(self, obj):
        return obj.club.name

    def email(self, obj):
        return obj.person.email

    def is_member(self, obj):
        return obj.club.membership_set.filter(person__pk=obj.person.pk).exists()

    is_member.boolean = True


class MembershipAdmin(admin.ModelAdmin):
    search_fields = (
        "person__username",
        "person__email",
        "club__name",
        "club__pk",
        "title",
    )
    list_display = ("person", "club", "role", "title")
    list_filter = ("role", "active", "public")

    def person(self, obj):
        return obj.person.username

    def club(self, obj):
        return obj.club.name


class ProfileAdmin(admin.ModelAdmin):
    search_fields = ("user__username", "user__email")
    list_display = ("user", "email", "graduation_year", "studies", "has_been_prompted")
    list_filter = ("graduation_year", "school", "major", "has_been_prompted")

    def email(self, obj):
        return str(obj.user.email or None)

    def studies(self, obj):
        major = ", ".join(obj.major.values_list("name", flat=True))
        school = ", ".join(obj.school.values_list("name", flat=True))
        return "{} - {}".format(school or None, major or None)


class MembershipInviteAdmin(admin.ModelAdmin):
    search_fields = ("email", "club__name", "club__pk")
    list_display = ("email", "club", "role", "title", "active")
    list_filter = ("role", "active")

    def club(self, obj):
        return obj.club.name


class AdvisorAdmin(admin.ModelAdmin):
    search_fields = ("name", "title", "email", "phone", "club__name")
    list_display = ("name", "title", "email", "phone", "club", "public")

    def club(self, obj):
        return obj.club.name


def do_merge_tags(modeladmin, request, queryset):
    if queryset.count() < 2:
        modeladmin.message_user(
            request, "You must select at least two tags to merge!", level=messages.ERROR
        )
        return
    tag_names = list(queryset.order_by("name").values_list("name", flat=True))
    tags = list(queryset)
    first, rest = tags[0], tags[1:]
    for tag in rest:
        merge_tags(first, tag)
    modeladmin.message_user(
        request,
        "Merged the following tags: {} into {}".format(
            ", ".join(tag_names), first.name
        ),
        level=messages.SUCCESS,
    )


do_merge_tags.short_description = "Merge selected tags"


class TagAdmin(admin.ModelAdmin):
    def club_count(self, obj):
        return obj.club_set.count()

    search_fields = ("name",)
    list_display = ("name", "club_count")
    actions = [do_merge_tags]


class BadgeAdmin(admin.ModelAdmin):
    def club_count(self, obj):
        return obj.club_set.count()

    def badge_color(self, obj):
        if not re.match(r"^([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", obj.color):
            return obj.color
        return mark_safe(
            f"<div style='background-color: #{obj.color}; \
                width:1em; \
                height:1em; \
                border:1px solid black; \
                border-radius:3px' />"
        )

    search_fields = ("label",)
    list_display = ("label", "purpose", "org", "club_count", "badge_color", "visible")
    list_filter = ("visible", "purpose")
    actions = [do_merge_tags]


class MajorAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class ReportAdmin(admin.ModelAdmin):
    search_fields = ("name", "description")
    list_display = ("name", "creator", "public")
    list_filter = ("created_at", "public")


class YearAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "year")


class QuestionAnswerAdmin(admin.ModelAdmin):
    search_fields = ("question", "answer")
    list_display = ("club", "question", "answer", "approved")
    list_filter = ("approved", "updated_at")


class ZoomMeetingVisitAdmin(admin.ModelAdmin):
    search_fields = ("person__username", "event__club__code")
    list_display = ("person", "event", "join_time")
    list_filter = (("leave_time", admin.EmptyFieldListFilter),)


admin.site.register(Asset)
admin.site.register(ApplicationQuestion)
admin.site.register(ApplicationQuestionResponse)
admin.site.register(Advisor, AdvisorAdmin)
admin.site.register(Club, ClubAdmin)
admin.site.register(ClubFair, ClubFairAdmin)
admin.site.register(ClubApplication)
admin.site.register(ClubFairRegistration)
admin.site.register(ClubVisit)
admin.site.register(Badge, BadgeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(School)
admin.site.register(SearchQuery)
admin.site.register(Subscribe, SubscribeAdmin)
admin.site.register(MembershipRequest, MembershipRequestAdmin)
admin.site.register(Major, MajorAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(MembershipInvite, MembershipInviteAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(QuestionAnswer, QuestionAnswerAdmin)
admin.site.register(RecurringEvent)
admin.site.register(Report, ReportAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(TargetMajor)
admin.site.register(TargetSchool)
admin.site.register(TargetYear)
admin.site.register(TargetStudentType)
admin.site.register(Testimonial)
admin.site.register(StudentType)
admin.site.register(Note)
admin.site.register(NoteTag)
admin.site.register(Year, YearAdmin)
admin.site.register(ZoomMeetingVisit, ZoomMeetingVisitAdmin)
