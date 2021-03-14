import argparse
import collections
import datetime
import functools
import io
import json
import os
import re
import secrets
import string
from urllib.parse import urlparse

import pytz
import qrcode
import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from dateutil.parser import parse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.management import call_command, get_commands, load_command_class
from django.core.validators import validate_email
from django.db.models import Count, DurationField, ExpressionWrapper, F, Prefetch, Q
from django.db.models.functions import Lower, Trunc
from django.db.models.query import prefetch_related_objects
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from ics import Calendar as ICSCal
from ics import Event as ICSEvent
from ics import parse as ICSParse
from options.models import Option
from rest_framework import filters, generics, parsers, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnList
from rest_framework.views import APIView
from social_django.utils import load_strategy
from tatsu.exceptions import FailedParse

from clubs.filters import RandomOrderingFilter, RandomPageNumberPagination
from clubs.mixins import XLSXFormatterMixin
from clubs.models import (
    Advisor,
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
    QuestionAnswer,
    RecurringEvent,
    Report,
    School,
    SearchQuery,
    StudentType,
    Subscribe,
    Tag,
    Testimonial,
    Year,
    ZoomMeetingVisit,
    get_mail_type_annotation,
)
from clubs.permissions import (
    AssetPermission,
    ClubFairPermission,
    ClubItemPermission,
    ClubPermission,
    DjangoPermission,
    EventPermission,
    InvitePermission,
    IsSuperuser,
    MemberPermission,
    MembershipRequestPermission,
    NotePermission,
    ProfilePermission,
    QuestionAnswerPermission,
    ReadOnly,
    find_membership_helper,
)
from clubs.serializers import (
    AdvisorSerializer,
    AssetSerializer,
    AuthenticatedClubSerializer,
    AuthenticatedMembershipSerializer,
    BadgeSerializer,
    ClubApplicationSerializer,
    ClubConstitutionSerializer,
    ClubFairSerializer,
    ClubListSerializer,
    ClubMinimalSerializer,
    ClubSerializer,
    EventSerializer,
    EventWriteSerializer,
    ExternalMemberListSerializer,
    FavoriteSerializer,
    FavoriteWriteSerializer,
    MajorSerializer,
    MembershipInviteSerializer,
    MembershipRequestSerializer,
    MembershipSerializer,
    MinimalUserProfileSerializer,
    NoteSerializer,
    QuestionAnswerSerializer,
    ReportClubSerializer,
    ReportSerializer,
    SchoolSerializer,
    SearchQuerySerializer,
    StudentTypeSerializer,
    SubscribeBookmarkSerializer,
    SubscribeSerializer,
    TagSerializer,
    TestimonialSerializer,
    UserClubVisitSerializer,
    UserClubVisitWriteSerializer,
    UserMembershipInviteSerializer,
    UserMembershipRequestSerializer,
    UserMembershipSerializer,
    UserProfileSerializer,
    UserSerializer,
    UserSubscribeSerializer,
    UserSubscribeWriteSerializer,
    UserUUIDSerializer,
    WritableClubApplicationSerializer,
    WritableClubFairSerializer,
    YearSerializer,
)
from clubs.utils import fuzzy_lookup_club, html_to_text


def file_upload_endpoint_helper(request, code):
    obj = get_object_or_404(Club, code=code)
    if "file" in request.data and isinstance(request.data["file"], UploadedFile):
        asset = Asset.objects.create(
            creator=request.user,
            club=obj,
            file=request.data["file"],
            name=request.data["file"].name,
        )
    else:
        return Response(
            {"detail": "No image file was uploaded!"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({"detail": "Club file uploaded!", "id": asset.id})


def upload_endpoint_helper(request, cls, field, save=True, **kwargs):
    """
    Given a Model class with lookup arguments or a Model object, save the uploaded image
    to the image field specified in the argument.

    The save parameter can be used to control whether the Model is actually saved to
    the database. This parameter only applies if you pass in a Model object.

    Returns a response that can be given to the end user.
    """
    if isinstance(cls, type):
        obj = get_object_or_404(cls, **kwargs)
    else:
        obj = cls
    if "file" in request.data and isinstance(request.data["file"], UploadedFile):
        getattr(obj, field).delete(save=False)
        setattr(obj, field, request.data["file"])
        if save:
            obj._change_reason = f"Update '{field}' image field"
            obj.save()
    else:
        return Response(
            {"detail": "No image file was uploaded!"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "detail": f"{obj.__class__.__name__} image uploaded!",
            "url": getattr(obj, field).url,
        }
    )


def find_relationship_helper(relationship, club_object, found):
    """
    Format and retrieve all parents or children of a club into tree.
    """
    children = getattr(club_object, relationship).all().prefetch_related(relationship)
    children_recurse = []
    for child in children:
        if child.code not in found:
            found.add(child.code)
            children_recurse.append(
                find_relationship_helper(relationship, child, found)
            )
            found.remove(child.code)
        else:
            children_recurse.append({"name": child.name, "code": child.code})

    return {
        "name": club_object.name,
        "code": club_object.code,
        "children": children_recurse,
    }


def filter_note_permission(queryset, club, user):
    """
    Filter the note queryset so that only notes the user has access
    to remain in the queryset
    """
    creating_club_membership = Membership.objects.filter(club=club, person=user).first()
    subject_club_membership = Membership.objects.filter(club=club, person=user).first()

    # Convert memberships into actual numerical representation
    if creating_club_membership is None:
        creating_club_membership = Note.PERMISSION_PUBLIC
    else:
        creating_club_membership = creating_club_membership.role

    if subject_club_membership is None:
        subject_club_membership = Note.PERMISSION_PUBLIC
    else:
        subject_club_membership = subject_club_membership.role

    queryset = queryset.filter(
        creating_club_permission__gte=creating_club_membership
    ) | queryset.filter(outside_club_permission__gte=subject_club_membership)

    return queryset


def hour_to_string_helper(hour):
    hour_string = ""
    if hour == 0:
        hour_string = "12am"
    elif hour < 12:
        hour_string = f"{hour}am"
    elif hour == 12:
        hour_string = "12pm"
    else:
        hour_string = f"{hour - 12}pm"

    return hour_string


class ReportViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return a list of reports that can be generated.
    """

    permission_classes = [DjangoPermission("clubs.generate_reports") | IsSuperuser]
    serializer_class = ReportSerializer
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return Report.objects.filter(Q(creator=self.request.user) | Q(public=True))


class ClubsSearchFilter(filters.BaseFilterBackend):
    """
    A DRF filter to implement custom filtering logic for the frontend.
    If model is not a Club, expects the model to have a club foreign key to Club.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.GET.dict()

        def parse_year(field, value, operation, queryset):
            if value.isdigit():
                suffix = ""
                if operation in {"lt", "gt", "lte", "gte"}:
                    suffix = f"__{operation}"
                return {f"{field}__year{suffix}": int(value)}
            if value.lower() in {"none", "null"}:
                return {f"{field}__isnull": True}
            return {}

        def parse_int(field, value, operation, queryset):
            if operation == "in":
                values = value.strip().split(",")
                sizes = [int(size) for size in values if size]
                return {f"{field}__in": sizes}

            if "," in value:
                values = [int(x.strip()) for x in value.split(",") if x]
                if operation == "and":
                    for value in values:
                        queryset = queryset.filter(**{field: value})
                    return queryset
                return {f"{field}__in": values}

            if value.isdigit():
                suffix = ""
                if operation in {"lt", "gt", "lte", "gte"}:
                    suffix = f"__{operation}"
                return {f"{field}{suffix}": int(value)}
            if value.lower() in {"none", "null"}:
                return {f"{field}__isnull": True}
            return {}

        def parse_many_to_many(label, field, value, operation, queryset):
            tags = value.strip().split(",")
            if operation == "or":
                if tags[0].isdigit():
                    tags = [int(tag) for tag in tags if tag]
                    return {f"{field}__id__in": tags}
                else:
                    return {f"{field}__{label}__in": tags}

            if tags[0].isdigit() or operation == "id":
                tags = [int(tag) for tag in tags if tag]
                for tag in tags:
                    queryset = queryset.filter(**{f"{field}__id": tag})
            else:
                for tag in tags:
                    queryset = queryset.filter(**{f"{field}__{label}": tag})
            return queryset

        def parse_badges(field, value, operation, queryset):
            return parse_many_to_many("label", field, value, operation, queryset)

        def parse_tags(field, value, operation, queryset):
            return parse_many_to_many("name", field, value, operation, queryset)

        def parse_boolean(field, value, operation, queryset):
            value = value.strip().lower()

            if operation == "in":
                if set(value.split(",")) == {"true", "false"}:
                    return

            if value in {"true", "yes"}:
                boolval = True
            elif value in {"false", "no"}:
                boolval = False
            elif value in {"null", "none"}:
                boolval = None
            else:
                return

            if boolval is None:
                return {f"{field}__isnull": True}

            return {f"{field}": boolval}

        def parse_string(field, value, operation, queryset):
            if operation == "in":
                values = [x.strip() for x in value.split(",")]
                values = [x for x in values if x]
                return {f"{field}__in": values}
            return {f"{field}": value}

        def parse_datetime(field, value, operation, queryset):
            try:
                value = parse(value.strip())
            except (ValueError, OverflowError):
                return

            if operation in {"gt", "lt", "gte", "lte"}:
                return {f"{field}__{operation}": value}
            return

        fields = {
            "accepting_members": parse_boolean,
            "active": parse_boolean,
            "application_required": parse_int,
            "appointment_needed": parse_boolean,
            "approved": parse_boolean,
            "available_virtually": parse_boolean,
            "badges": parse_badges,
            "code": parse_string,
            "enables_subscription": parse_boolean,
            "favorite_count": parse_int,
            "founded": parse_year,
            "recruiting_cycle": parse_int,
            "size": parse_int,
            "tags": parse_tags,
            "target_majors": parse_tags,
            "target_schools": parse_tags,
            "target_years": parse_tags,
            "target_students": parse_tags,
        }

        def parse_fair(field, value, operation, queryset):
            try:
                value = int(value.strip())
            except ValueError:
                return

            fair = ClubFair.objects.filter(id=value).first()
            if fair:
                return {
                    "start_time__gte": fair.start_time,
                    "end_time__lte": fair.end_time,
                }

        if not queryset.model == Club:
            fields = {f"club__{k}": v for k, v in fields.items()}

        if queryset.model == Event:
            fields.update(
                {
                    "type": parse_int,
                    "start_time": parse_datetime,
                    "end_time": parse_datetime,
                    "fair": parse_fair,
                }
            )

        query = {}

        for param, value in params.items():
            field = param.split("__")
            if field[0] == "club":
                prefix = field.pop(0)
                field[0] = f"{prefix}__{field[0]}"

            if len(field) <= 1:
                field = field[0]
                type = "eq"
            else:
                type = field[1].lower()
                field = field[0]

            if field not in fields:
                continue

            condition = fields[field](field, value.strip(), type, queryset)
            if isinstance(condition, dict):
                query.update(condition)
            elif condition is not None:
                queryset = condition

        queryset = queryset.filter(**query)

        return queryset


class ClubsOrderingFilter(RandomOrderingFilter):
    """
    Custom ordering filter for club objects.
    If used by a non club model, the object must have a foreign key to Club named club.
    """

    def get_valid_fields(self, queryset, view, context={}):
        # report generators can order by any field
        request = context.get("request")
        if (
            request is not None
            and request.user.is_authenticated
            and request.user.has_perm("clubs.generate_reports")
        ):
            valid_fields = [
                (field.name, field.verbose_name)
                for field in queryset.model._meta.fields
            ]
            valid_fields += [
                (key, key.title().split("__")) for key in queryset.query.annotations
            ]
            valid_fields += [
                (f"club__{field.name}", f"Club - {field.verbose_name}")
                for field in Club._meta.fields
            ]
            return valid_fields

        # other people can order by whitelist
        return super().get_valid_fields(queryset, view, context)

    def filter_queryset(self, request, queryset, view):
        ordering = [
            arg for arg in request.GET.get("ordering", "").strip().split(",") if arg
        ]
        if not ordering and hasattr(view, "ordering"):
            ordering = [view.ordering]

        if "featured" in ordering:
            if queryset.model == Club:
                return queryset.order_by("-rank", "-favorite_count", "-id")
            return queryset.order_by(
                "-club__rank", "-club__favorite_count", "-club__id"
            )
        else:
            # prevent invalid SQL lookups from custom ordering properties
            if hasattr(view, "ordering") and view.ordering in {
                "featured",
                "alphabetical",
                "random",
            }:
                old_ordering = view.ordering
                view.ordering = "-id"
            else:
                old_ordering = None

            new_queryset = super().filter_queryset(request, queryset, view)

            # restore ordering property
            if old_ordering is not None:
                view.ordering = old_ordering

        if "alphabetical" in ordering:
            new_queryset = new_queryset.order_by(Lower("name"))

        return new_queryset


class ClubFairViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of ongoing and upcoming club fairs.

    create:
    Schedule a new club fair.

    update:
    Update some attributes related to an existing club fair.
    All fields must be specified.

    partial_update:
    Update some attributes related to an existing club fair.
    Only specified fields are updated.

    destroy:
    Delete a club fair.
    """

    permission_classes = [ClubFairPermission | IsSuperuser]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return WritableClubFairSerializer
        return ClubFairSerializer

    @action(detail=False, methods=["get"])
    def current(self, request, *args, **kwargs):
        """
        Return only the current club fair instance in a list or an empty list
        if there is no fair going on.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                $ref: "#/components/schemas/ClubFair"
        ---
        """
        now = timezone.now()
        fair = ClubFair.objects.filter(
            start_time__lte=now + datetime.timedelta(minutes=2),
            end_time__gte=now - datetime.timedelta(minutes=2),
        ).first()
        if fair is None:
            return Response([])
        else:
            return Response([ClubFairSerializer(instance=fair).data])

    @action(detail=True, methods=["get"])
    def live(self, *args, **kwargs):
        """
        Returns all events, grouped by id, with the number of participants currently
        in the meeting, the officers or owners in the meeting, and the number of
        participants who have already attended the meeting.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            additionalProperties:
                                type: object
                                properties:
                                    participant_count:
                                        type: integer
                                    already_attended:
                                        type: integer
                                    officers:
                                        type: array
                                        items:
                                            type: string
                                    median:
                                        type: number
        ---
        """
        fair = self.get_object()
        clubs = fair.participating_clubs.all()
        events = (
            Event.objects.filter(
                club__in=clubs,
                type=Event.FAIR,
                start_time__gte=fair.start_time,
                end_time__lte=fair.end_time,
            )
            .annotate(
                participant_count=Count(
                    "visits__person",
                    distinct=True,
                    filter=Q(visits__leave_time__isnull=True),
                )
            )
            .annotate(
                already_attended=Count(
                    "visits__person",
                    distinct=True,
                    filter=Q(visits__leave_time__isnull=False),
                )
            )
            .filter(visits__leave_time__isnull=False)
            .annotate(
                durations=ExpressionWrapper(
                    F("visits__leave_time") - F("visits__join_time"),
                    output_field=DurationField(),
                )
            )
        )

        median_list = collections.defaultdict(list)
        for event_id, duration in events.values_list("id", "durations").order_by(
            "durations"
        ):
            median_list[event_id].append(duration.total_seconds())
        median_list = {k: v[len(v) // 2] if v else 0 for k, v in median_list.items()}

        event_list = events.values_list("id", "participant_count", "already_attended")
        officer_mapping = collections.defaultdict(list)
        for k, v in events.filter(
            club__in=clubs,
            club__membership__role__lte=10,
            visits__leave_time__isnull=True,
        ).values_list("id", "club__membership__person__username"):
            officer_mapping[k].append(v)

        formatted = {}
        for event_id, particpant_count, already_attended in event_list:
            formatted[event_id] = {
                "participant_count": particpant_count,
                "already_attended": already_attended,
                "officers": officer_mapping.get(event_id, []),
                "median": median_list.get(event_id, 0),
            }
        return Response(formatted)

    @action(detail=True, methods=["post"])
    def create_events(self, request, *args, **kwargs):
        """
        Create events for each club registered for this activities fair.
        This endpoint will create one event per club spanning the
        entire listed duration.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            start_time:
                                type: string
                            end_time:
                                type: string
                            suffix:
                                type: string
                            clubs:
                                type: string
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                events:
                                    type: number
        ---
        """
        start_time = None
        end_time = None
        query = None
        suffix = request.data.get("suffix") or "default"
        clubs = [c.strip() for c in re.split(r"[,\t\n]", request.data.get("clubs", ""))]
        clubs = [c for c in clubs]

        if clubs:
            query = Q(code__in=clubs)

        if "start_time" in request.data:
            start_time = parse(request.data["start_time"])
        if "end_time" in request.data:
            end_time = parse(request.data["end_time"])

        fair = self.get_object()
        events = fair.create_events(
            start_time=start_time, end_time=end_time, suffix=suffix, filter=query
        )
        return Response({"events": len(events)})

    @action(detail=True, methods=["get"])
    def events(self, request, *args, **kwargs):
        """
        Return all of the events related to this club fair
        and whether they are properly configured.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: object
                                properties:
                                    code:
                                        type: string
                                        description: >
                                            The club code for the club.
                                    name:
                                        type: string
                                        description: >
                                            The name of the club.
                                    approved:
                                        type: boolean
                                        description: >
                                            Whether this club has been approved by the
                                            approval authority or not.
                                    badges:
                                        type: array
                                        description: >
                                            A list of badges associated with this
                                            club and fair.
                                        items:
                                            type: string
                                    meetings:
                                        type: array
                                        description: >
                                            The meeting links for the fair events.
                                        items:
                                            type: string
        ---
        """
        fair = self.get_object()
        clubs = fair.participating_clubs.all()

        # collect events
        events = collections.defaultdict(list)
        for k, v in Event.objects.filter(
            club__in=clubs,
            type=Event.FAIR,
            start_time__gte=fair.start_time,
            end_time__lte=fair.end_time,
        ).values_list("club__code", "url"):
            events[k].append(v)

        # collect badges
        badges = collections.defaultdict(list)
        for code, lbl in Badge.objects.filter(purpose="fair", fair=fair).values_list(
            "club__code", "label"
        ):
            badges[code].append(lbl)

        return Response(
            [
                {
                    "code": code,
                    "name": name,
                    "approved": approved or ghost,
                    "meetings": events.get(code, []),
                    "badges": badges.get(code, []),
                }
                for code, name, approved, ghost in clubs.order_by("name").values_list(
                    "code", "name", "approved", "ghost"
                )
            ]
        )

    @action(detail=True, methods=["post"])
    def register(self, request, *args, **kwargs):
        """
        Register a club for this club fair.
        Pass in a "club" string parameter with the club code
        and a "status" parameter that is true to register the club,
        or false to unregister.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            status:
                                type: boolean
                                description: >
                                    Whether to register or unregister this club for
                                    the fair. By default, the endpoint will attempt
                                    to register the club.
                            club:
                                type: string
                                description: >
                                    The code of the club that you are trying
                                    to register.
                            answers:
                                type: array
                                description: >
                                    The answers to the required fair questions.
                                    Each element in the array is an answer to a fair
                                    question, in the same order of the related
                                    fair questions.
                        required:
                            - club
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                    description: >
                                        Whether or not this club has been registered.
                                message:
                                    type: string
                                    description: A success or error message.
        ---
        """
        fair = self.get_object()

        if not request.user.is_authenticated:
            raise PermissionDenied

        club = get_object_or_404(Club, code=request.data.get("club"))

        # get register/unregister action status
        status = request.data.get("status")
        if isinstance(status, str):
            status = status.strip().lower() == "true"
        elif not isinstance(status, bool):
            status = True

        # get answers to questions
        num_questions = len(json.loads(fair.questions)) if fair.questions else 0
        answer_objects = request.data.get("answers", [])
        answers = json.dumps(answer_objects)

        # make sure questions are answered
        if (
            status
            and num_questions > 0
            and (
                not all(ans is not None for ans in answer_objects)
                or len(answer_objects) < num_questions
            )
        ):
            return Response(
                {
                    "success": False,
                    "message": "Please fill out all of the questions in the form.",
                }
            )

        # make sure club constitution is uploaded for SAC clubs
        if (
            status
            and fair.organization == "Student Activities Council"
            and club.badges.filter(label="SAC").exists()
        ):
            if club.asset_set.count() <= 0 or not any(
                asset.name.lower().endswith((".pdf", ".doc", ".docx"))
                for asset in club.asset_set.all()
            ):
                if not request.user.is_superuser:
                    return Response(
                        {
                            "success": False,
                            "message": "As a SAC affiliated club, "
                            "you must upload a club constitution "
                            "before registering for this fair.",
                        }
                    )

        # check if registration has started
        now = timezone.now()
        if (
            fair.registration_start_time is not None
            and fair.registration_start_time > now
        ):
            return Response(
                {
                    "success": False,
                    "message": "Registration for this activities fair "
                    "has not opened yet.",
                }
            )

        # check if deadline has passed
        if fair.registration_end_time < now:
            return Response(
                {
                    "success": False,
                    "message": "The deadline has passed to register "
                    "for this activities fair. "
                    f"Please email {fair.contact} for assistance.",
                }
            )

        # check if user can actually register club
        mship = find_membership_helper(request.user, club)
        if (
            mship is not None
            and mship.role <= Membership.ROLE_OFFICER
            or request.user.is_superuser
        ):
            # register or unregister club
            if status:
                ClubFairRegistration.objects.update_or_create(
                    club=club,
                    fair=fair,
                    defaults={"answers": answers, "registrant": request.user},
                )
            else:
                fair.participating_clubs.remove(club)
            return Response({"success": True})
        else:
            raise PermissionDenied

    def get_queryset(self):
        now = timezone.now()
        return ClubFair.objects.filter(end_time__gte=now).order_by("start_time")


class ClubViewSet(XLSXFormatterMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return a single club with all information fields present.

    list:
    Return a list of clubs with partial information for each club.

    create:
    Add a new club record.
    After creation, the club will need to go through the approval process.

    update:
    Update all fields in the club.
    You must specify all of the fields or use a patch request.

    partial_update:
    Update certain fields in the club.
    Only specify the fields that you want to change.

    destroy:
    Delete a club. Consider marking the club as inactive instead of deleting the club.
    """

    queryset = (
        Club.objects.all()
        .annotate(
            favorite_count=Count("favorite", distinct=True),
            membership_count=Count("membership", distinct=True, filter=Q(active=True)),
        )
        .prefetch_related("tags")
        .order_by("-favorite_count", "name")
    )
    permission_classes = [ClubPermission | IsSuperuser]
    filter_backends = [filters.SearchFilter, ClubsSearchFilter, ClubsOrderingFilter]
    search_fields = ["name", "subtitle", "code", "terms"]
    ordering_fields = ["favorite_count", "name"]
    ordering = "featured"

    lookup_field = "code"
    http_method_names = ["get", "post", "put", "patch", "delete"]
    pagination_class = RandomPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        # additional prefetch optimizations
        person = self.request.user
        if not person.is_authenticated:
            person = None

        if self.action in {"list", "retrieve"}:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "favorite_set",
                    queryset=Favorite.objects.filter(person=person),
                    to_attr="user_favorite_set",
                ),
                Prefetch(
                    "subscribe_set",
                    queryset=Subscribe.objects.filter(person=person),
                    to_attr="user_subscribe_set",
                ),
                Prefetch(
                    "membership_set",
                    queryset=Membership.objects.filter(person=person),
                    to_attr="user_membership_set",
                ),
            )

            if self.action in {"retrieve"}:
                queryset = queryset.prefetch_related(
                    "asset_set",
                    Prefetch("badges", queryset=Badge.objects.filter(visible=True)),
                    "student_types",
                    "target_majors",
                    "target_schools",
                    "target_years",
                    "testimonials",
                    Prefetch(
                        "membership_set",
                        queryset=Membership.objects.filter(active=True)
                        .order_by("role", "person__first_name", "person__last_name")
                        .prefetch_related("person__profile"),
                    ),
                )

        # if there is a search query made by a signed-in user, save it to the database
        if self.request.query_params.get("search") and isinstance(
            self.request.user, get_user_model()
        ):
            SearchQuery(
                person=self.request.user, query=self.request.query_params.get("search"),
            ).save()

        # select subset of clubs if requested
        subset = self.request.query_params.get("in", None)

        if subset:
            subset = [x.strip() for x in subset.strip().split(",")]
            queryset = queryset.filter(code__in=subset)

        # filter out archived clubs
        queryset = queryset.filter(archived=False)

        # filter by approved clubs
        if (
            self.request.user.has_perm("clubs.see_pending_clubs")
            or self.request.query_params.get("bypass", "").lower() == "true"
            or self.action not in {"list"}
        ):
            return queryset
        else:
            return queryset.filter(Q(approved=True) | Q(ghost=True))

    @action(detail=True, methods=["post"])
    def upload(self, request, *args, **kwargs):
        """
        Upload the club logo.
        Marks the club as pending approval since the logo has changed.
        Also create a thumbnail version of the club logo.
        ---
        requestBody:
            content:
                multipart/form-data:
                    schema:
                        type: object
                        properties:
                            file:
                                type: object
                                format: binary
        responses:
            "200":
                description: Returned if the file was successfully uploaded.
                content: &upload_resp
                    application/json:
                        schema:
                            type: object
                            properties:
                                detail:
                                    type: string
                                    description: The status of the file upload.
                                url:
                                    type: string
                                    nullable: true
                                    description: >
                                        The URL of the newly uploaded file.
                                        Only exists if the file was
                                        successfully uploaded.
            "400":
                description: Returned if there was an error while uploading the file.
                content: *upload_resp
        ---
        """
        # ensure user is allowed to upload image
        club = self.get_object()

        # reset approval status after upload
        resp = upload_endpoint_helper(request, club, "image", save=False)
        if status.is_success(resp.status_code):
            club.approved = None
            club.approved_by = None
            club.approved_on = None
            if club.history.filter(approved=True).exists():
                club.ghost = True

            club._change_reason = "Mark pending approval due to image change"
            club.save(
                update_fields=[
                    "image",
                    "approved",
                    "approved_by",
                    "approved_on",
                    "ghost",
                ]
            )

            # create thumbnail
            club.create_thumbnail(request)

        return resp

    @action(detail=True, methods=["post"])
    def upload_file(self, request, *args, **kwargs):
        """
        Upload a file for the club.
        ---
        requestBody:
            content:
                multipart/form-data:
                    schema:
                        type: object
                        properties:
                            file:
                                type: object
                                format: binary
        responses:
            "200":
                description: Returned if the file was successfully uploaded.
                content: &upload_resp
                    application/json:
                        schema:
                            type: object
                            properties:
                                detail:
                                    type: string
                                    description: The status of the file upload.
                                url:
                                    type: string
                                    nullable: true
                                    description: >
                                        The URL of the newly uploaded file.
                                        Only exists if the file was successfully
                                        uploaded.
            "400":
                description: Returned if there was an error while uploading the file.
                content: *upload_resp
        ---
        """
        # ensure user is allowed to upload file
        club = self.get_object()

        return file_upload_endpoint_helper(request, code=club.code)

    @action(detail=True, methods=["get"])
    def children(self, request, *args, **kwargs):
        """
        Return a recursive list of all children that this club is a parent of.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                name:
                                    type: string
                                code:
                                    type: string
                                children:
                                    type: array
                                    description: >
                                        An array of clubs containing
                                        the fields in this object.
        ---
        """
        club = self.get_object()
        child_tree = find_relationship_helper("children_orgs", club, {club.code})
        return Response(child_tree)

    @action(detail=True, methods=["get"])
    def parents(self, request, *args, **kwargs):
        """
        Return a recursive list of all parents that this club is a child to.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                name:
                                    type: string
                                code:
                                    type: string
                                children:
                                    type: array
                                    description: >
                                        An array of clubs containing
                                        the fields in this object.
        ---
        """
        club = self.get_object()
        parent_tree = find_relationship_helper("parent_orgs", club, {club.code})
        return Response(parent_tree)

    @action(detail=True, methods=["get"])
    def alumni(self, request, *args, **kwargs):
        """
        Return the members of this club who are no longer active.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            additionalProperties:
                                type: array
                                items:
                                    type: object
                                    properties:
                                        name:
                                            type: string
                                        username:
                                            type: string
        ---
        """
        club = self.get_object()
        results = collections.defaultdict(list)
        for first, last, year, show, username in club.membership_set.filter(
            active=False, public=True
        ).values_list(
            "person__first_name",
            "person__last_name",
            "person__profile__graduation_year",
            "person__profile__show_profile",
            "person__username",
        ):
            results[year].append(
                {
                    "name": f"{first} {last}".strip(),
                    "username": username if show else None,
                }
            )
        return Response(results)

    @action(detail=True, methods=["get"], url_path="notes-about")
    def notes_about(self, request, *args, **kwargs):
        """
        Return a list of notes about this club, used by members of parent organizations.
        """
        club = self.get_object()
        queryset = Note.objects.filter(subject_club__code=club.code)
        queryset = filter_note_permission(queryset, club, self.request.user)
        serializer = NoteSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def qr(self, request, *args, **kwargs):
        """
        Return a QR code png image representing a link to the club on Penn Clubs.
        ---
        operationId: Generate QR Code for Club
        responses:
            "200":
                description: Return a png image representing a QR code to the fair page.
                content:
                    image/png:
                        schema:
                            type: binary
        ---
        """
        club = self.get_object()

        url = f"https://{settings.DEFAULT_DOMAIN}/club/{club.code}/fair"
        response = HttpResponse(content_type="image/png")
        qr_image = qrcode.make(url, box_size=20, border=0)
        qr_image.save(response, "PNG")
        return response

    @action(detail=True, methods=["get"])
    def subscription(self, request, *args, **kwargs):
        """
        Return a list of all students that have subscribed to the club,
        including their names and emails.

        If a student has indicated that they want to share their bookmarks as well,
        include this information in the results.
        """
        club = self.get_object()
        subscribes = (
            Subscribe.objects.filter(club=club)
            .select_related("person", "person__profile", "club")
            .prefetch_related("person__profile__school", "person__profile__major")
        )
        shared_bookmarks = (
            Favorite.objects.exclude(
                person__pk__in=subscribes.values_list("person__pk", flat=True)
            )
            .filter(club=club, person__profile__share_bookmarks=True)
            .select_related("person", "person__profile", "club")
            .prefetch_related("person__profile__school", "person__profile__major")
        )
        bookmark_serializer = SubscribeBookmarkSerializer(shared_bookmarks, many=True)
        serializer = SubscribeSerializer(subscribes, many=True)
        output = serializer.data + bookmark_serializer.data
        return Response(ReturnList(output, serializer=serializer))

    @action(detail=True, methods=["get"])
    def analytics_pie_charts(self, request, *args, **kwargs):
        """
        Returns demographic information about bookmarks
        and subscriptions in pie chart format.
        ---
        parameters:
            - name: category
              in: query
              type: string
            - name: metric
              in: query
              type: string
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                content:
                                    type: array
        ---
        """
        club = self.get_object()
        lower_bound = timezone.now() - datetime.timedelta(days=30 * 6)
        category = self.request.query_params.get("category")
        metric = self.request.query_params.get("metric")

        def get_breakdown(category, metric):
            if category == "graduation_year":
                category_join = "person__profile__graduation_year"
            else:
                category_join = "person__profile__school__name"

            if metric == "favorite":
                queryset = Favorite.objects.filter(
                    club=club, created_at__gte=lower_bound
                )
            elif metric == "subscribe":
                queryset = Subscribe.objects.filter(
                    club=club, created_at__gte=lower_bound
                )
            else:
                queryset = ClubVisit.objects.filter(
                    club=club, created_at__gte=lower_bound, visit_type=1
                )

            return {
                "content": list(
                    queryset.values(category_join).annotate(count=Count("id"))
                ),
            }

        return Response(get_breakdown(category, metric))

    @action(detail=True, methods=["get"])
    def analytics(self, request, *args, **kwargs):
        """
        Returns a list of all analytics (club visits, favorites,
        subscriptions) for a club.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                max:
                                    type: integer
                                    description: >
                                        The maximum value among all categories.
                                        Useful when deciding how tall a
                                        line chart should be.
                                visits:
                                    type: array
                                favorites:
                                    type: array
                                subscriptions:
                                    type: array
        ---
        """
        club = self.get_object()
        group = self.request.query_params.get("group", "hour")
        if "date" in request.query_params:
            date = datetime.datetime.strptime(request.query_params["date"], "%Y-%m-%d")
        else:
            date = datetime.datetime.combine(
                datetime.date.today(), datetime.datetime.min.time()
            )

        # parse date range
        if "start" in request.query_params:
            start = parse(request.query_params["start"])
        else:
            start = date

        if "end" in request.query_params:
            end = parse(request.query_params["end"])
        else:
            end = start + datetime.timedelta(days=1)

        # retrieve data
        def get_count(queryset):
            """
            Return a json serializable aggregation of
            analytics data for a specific model.
            """
            objs = (
                queryset.annotate(group=Trunc("created_at", group))
                .values("group")
                .annotate(count=Count("id"))
            )
            for item in objs:
                item["group"] = item["group"].isoformat()
            return list(objs)

        visits_data = get_count(
            ClubVisit.objects.filter(
                club=club,
                created_at__gte=start,
                created_at__lte=end,
                visit_type=ClubVisit.CLUB_PAGE,
            )
        )
        favorites_data = get_count(
            Favorite.objects.filter(
                club=club, created_at__gte=start, created_at__lte=end
            )
        )
        subscriptions_data = get_count(
            Subscribe.objects.filter(
                club=club, created_at__gte=start, created_at__lte=end
            )
        )

        max_value = max(
            max([v["count"] for v in visits_data], default=0),
            max([v["count"] for v in favorites_data], default=0),
            max([v["count"] for v in subscriptions_data], default=0),
        )

        analytics_dict = {
            "visits": visits_data,
            "favorites": favorites_data,
            "subscriptions": subscriptions_data,
            "max": max_value,
        }

        return Response(analytics_dict)

    def get_operation_id(self, **kwargs):
        if kwargs["action"] == "fetch" and kwargs["method"] == "DELETE":
            return "deleteIcsEvents"

    @action(detail=True, methods=["post", "delete"])
    def fetch(self, request, *args, **kwargs):
        """
        Fetch the ICS calendar events from the club's ICS calendar URL.
        ---
        requestBody: {}
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                    description: Whether or not events were fetched.
                                message:
                                    type: string
                                    description: A success or error message.
        ---
        """
        club = self.get_object()

        if request.method == "DELETE":
            now = timezone.now()
            num = club.events.filter(is_ics_event=True, start_time__gte=now).delete()[0]
            return Response(
                {
                    "success": True,
                    "message": f"Deleted all {num} imported ICS calendar events!",
                }
            )

        if not club.ics_import_url:
            return Response(
                {
                    "success": False,
                    "message": "No ICS calendar URL set, so no events were imported.",
                }
            )

        try:
            num_events = club.add_ics_events()
        except requests.exceptions.RequestException:
            return Response(
                {
                    "success": False,
                    "message": "Failed to fetch events from server, "
                    "are you sure your URL is correct?",
                }
            )
        except FailedParse:
            return Response(
                {
                    "success": False,
                    "message": "Failed to parse ICS events, "
                    "are you sure this is an ICS file?",
                }
            )

        return Response({"success": True, "message": f"Fetched {num_events} events!"})

    @action(detail=False, methods=["get"])
    def directory(self, request, *args, **kwargs):
        """
        Custom return endpoint for the directory page, allows the page to load faster.
        ---
        operationId: Club Directory List
        ---
        """
        serializer = ClubMinimalSerializer(
            Club.objects.all()
            .exclude(Q(approved=False) | Q(archived=True))
            .order_by(Lower("name")),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def constitutions(self, request, *args, **kwargs):
        """
        A special endpoint for SAC affilaited clubs to check if
        they have uploaded a club constitution.
        ---
        operationId: List Club Constitutions
        ---
        """
        badge = Badge.objects.filter(label="SAC").first()
        if badge:
            query = (
                Club.objects.filter(badges=badge, archived=False)
                .order_by(Lower("name"))
                .prefetch_related(Prefetch("asset_set", to_attr="prefetch_asset_set"),)
            )
            if request.user.is_authenticated:
                query = query.prefetch_related(
                    Prefetch(
                        "membership_set",
                        queryset=Membership.objects.filter(person=request.user),
                        to_attr="user_membership_set",
                    )
                )
            serializer = ClubConstitutionSerializer(
                query, many=True, context={"request": request}
            )
            return Response(serializer.data)
        else:
            return Response({"error": "The SAC badge does not exist in the database."})

    @action(detail=False, methods=["post"])
    def lookup(self, request, *args, **kwargs):
        """
        An endpoint to look up club codes from club names.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        properties:
                            clubs:
                                type: string
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                output:
                                    type: string
        ---
        """
        clubs = [c.strip() for c in re.split(r"[\t\n]", request.data.get("clubs", ""))]
        clubs = [c for c in clubs if c]
        simple = {
            name: code
            for name, code in Club.objects.filter(name__in=clubs).values_list(
                "name", "code"
            )
        }
        output = []
        for name in clubs:
            if name in simple:
                output.append(simple[name])
            elif name:
                fuzzy = fuzzy_lookup_club(name)
                if fuzzy is None:
                    fuzzy = "None"
                else:
                    fuzzy = fuzzy.code
                output.append(fuzzy)
            else:
                output.append(name)
        return Response({"output": "\n".join(output).strip()})

    @action(detail=False, methods=["post"])
    def bulk(self, request, *args, **kwargs):
        """
        An endpoint to perform certain club edit operations in bulk.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        properties:
                            action:
                                type: string
                                description: The bulk action to perform.
                            clubs:
                                type: string
                                description: >
                                    A list of club codes, separated by
                                    comma, newline, space, or tab.
                            tags:
                                type: array
                                items:
                                    type: object
                                    parameters:
                                        id:
                                            type: number
                            badges:
                                type: array
                                items:
                                    type: object
                                    parameters:
                                        id:
                                            type: number
                            fairs:
                                type: array
                                items:
                                    type: object
                                    parameters:
                                        id:
                                            type: number
                        required:
                            - action
                            - clubs
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                    description: >
                                        Whether or not this club has been registered.
                                message:
                                    type: string
                                    description: >
                                        A success message. Only set if operation passes.
                                error:
                                    type: string
                                    description: >
                                        An error message. Only set if an error occurs.
        ---
        """
        if not request.user.is_authenticated or not request.user.has_perm(
            "clubs.manage_club"
        ):
            return Response(
                {"error": "You do not have permission to perform this action."}
            )

        action = request.data.get("action")
        if action is None:
            return Response({"error": "You must specify the action to perform!"})

        # lookup clubs by code
        clubs = [
            code.strip()
            for code in re.split(r"[,\t\n]", request.data.get("clubs", "").strip())
        ]
        clubs = [code for code in clubs if code]
        if not clubs:
            return Response(
                {
                    "error": "You must specify the list of codes "
                    "you want to apply this action to."
                }
            )
        club_objs = Club.objects.filter(code__in=clubs)
        missing_clubs = set(clubs) - set(club_objs.values_list("code", flat=True))

        # abort if none exist
        if not club_objs.exists():
            clubs_str = ", ".join(clubs)
            return Response(
                {
                    "error": "No objects were found matching those codes. "
                    f"Codes tried: {clubs_str}"
                }
            )

        tags = request.data.get("tags", [])
        badges = request.data.get("badges", [])
        fairs = request.data.get("fairs", [])

        if not tags and not badges and not fairs:
            return Response(
                {"error": "You must specify some related objects to manipulate!"}
            )

        tags = Tag.objects.filter(id__in=[tag["id"] for tag in tags])
        badges = Badge.objects.filter(id__in=[badge["id"] for badge in badges])
        fairs = ClubFair.objects.filter(id__in=[fair["id"] for fair in fairs])

        count = 0
        if tags or badges:
            for club in club_objs:
                if action == "add":
                    club.tags.add(*tags)
                    club.badges.add(*badges)
                    count += 1
                elif action == "remove":
                    club.tags.remove(*tags)
                    club.badges.remove(*badges)
                    count += 1

        if fairs:
            for fair in fairs:
                if action == "add":
                    registered_clubs = set(
                        ClubFairRegistration.objects.filter(fair=fair).values_list(
                            "club__code", flat=True
                        )
                    )
                    unregistered_clubs = [
                        club for club in club_objs if club.code not in registered_clubs
                    ]
                    ClubFairRegistration.objects.bulk_create(
                        [
                            ClubFairRegistration(
                                club=club, fair=fair, registrant=request.user
                            )
                            for club in unregistered_clubs
                        ]
                    )
                    count += len(unregistered_clubs)
                elif action == "remove":
                    count += ClubFairRegistration.objects.filter(
                        club__in=club_objs, fair=fair
                    ).delete()[0]

        msg = f"{count} object(s) have been updated!"
        if missing_clubs:
            msg += (
                f" Could not find {len(missing_clubs)} club(s) by code: "
                f"{', '.join(missing_clubs)}"
            )

        return Response({"success": True, "message": msg})

    def get_filename(self):
        """
        For excel spreadsheets, return the user-specified filename if it exists
        or the default filename otherwise.
        """
        name = self.request.query_params.get("xlsx_name")
        if name:
            return "{}.xlsx".format(slugify(name))
        return super().get_filename()

    def check_approval_permission(self, request):
        """
        Only users with specific permissions can modify the approval field.
        """
        if (
            request.data.get("approved", None) is not None
            or request.data.get("approved_comment", None) is not None
        ):
            # users without approve permission cannot approve
            if not request.user.has_perm("clubs.approve_club"):
                raise PermissionDenied

            # an approval request must not modify any other fields
            if set(request.data.keys()) - {"approved", "approved_comment"}:
                raise DRFValidationError(
                    "You can only pass the approved and approved_comment fields "
                    "when performing club approval."
                )

        if request.data.get("fair", None) is not None:
            if set(request.data.keys()) - {"fair"}:
                raise DRFValidationError(
                    "You can only pass the fair field when registering "
                    "or deregistering for the SAC fair."
                )

    def partial_update(self, request, *args, **kwargs):
        self.check_approval_permission(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.check_approval_permission(request)
        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        Return a list of all clubs.
        Note that some fields are removed in order to improve response time.
        """
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """
        Set archived boolean to be True so that the club appears to have been deleted
        """

        instance.archived = True
        instance.archived_by = self.request.user
        instance.archived_on = timezone.now()
        instance.save()

    @action(detail=False, methods=["GET"])
    def fields(self, request, *args, **kwargs):
        """
        Return the list of fields that can be exported in the Excel file.
        The list of fields is taken from the associated serializer, with model names
        overriding the serializer names if they exist. Custom fields are also available
        with certain permission levels.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            additionalProperties:
                                type: object
                                additionalProperties:
                                    type: string
        ---
        """
        # use the title given in the models.py if it exists,
        # fallback to the field name otherwise
        name_to_title = {}
        name_to_relation = {}
        for f in Club._meta._get_fields(reverse=False):
            name_to_title[f.name] = f.verbose_name.title()
            name_to_relation[f.name] = f.is_relation

        # return a list of additional dynamically generated fields
        serializer_class = self.get_serializer_class()
        if hasattr(serializer_class, "get_additional_fields"):
            fields = serializer_class.get_additional_fields()
        else:
            fields = {}

        # compute list of fields on Club
        club_fields = serializer_class().get_fields()
        for field, obj in club_fields.items():
            if isinstance(
                obj, (serializers.ModelSerializer, serializers.ListSerializer)
            ):
                name_to_relation[field] = True

        fields.update(
            {
                "basic": {
                    name_to_title.get(f, f.replace("_", " ").title()): f
                    for f in serializer_class.Meta.fields
                    if not name_to_relation.get(f, False)
                },
                "related": {
                    name_to_title.get(f, f.replace("_", " ").title()): f
                    for f in serializer_class.Meta.fields
                    if name_to_relation.get(f, False)
                },
            }
        )

        return Response(fields)

    def get_serializer_class(self):
        """
        Return a serializer class that is appropriate for the action being performed.
        Some serializer classes return less information, either for permission reasons
        or to improve performance.
        """
        if self.action == "upload":
            return AssetSerializer
        if self.action == "subscription":
            return SubscribeSerializer
        if self.action == "directory":
            return ClubMinimalSerializer
        if self.action == "constitutions":
            return ClubConstitutionSerializer
        if self.action == "notes_about":
            return NoteSerializer
        if self.action in {"list", "fields"}:
            if self.request is not None and (
                self.request.accepted_renderer.format == "xlsx"
                or self.action == "fields"
            ):
                if self.request.user.has_perm("clubs.generate_reports"):
                    return ReportClubSerializer
                else:
                    return ClubSerializer
            return ClubListSerializer
        if self.request is not None and self.request.user.is_authenticated:
            see_pending = self.request.user.has_perm("clubs.see_pending_clubs")
            manage_club = self.request.user.has_perm("clubs.manage_club")
            is_member = (
                "code" in self.kwargs
                and Membership.objects.filter(
                    person=self.request.user, club__code=self.kwargs["code"]
                ).exists()
            )
            if see_pending or manage_club or is_member:
                return AuthenticatedClubSerializer
        return ClubSerializer


class SchoolViewSet(viewsets.ModelViewSet):
    """
    list:
    Retrieve a list of all of the schools (ex: Wharton, Engineering).

    retrieve:
    Retrieve a single school by ID.

    create:
    Add a new school to the list of schools.

    destroy:
    Delete a school from the list of schools.
    """

    serializer_class = SchoolSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    queryset = School.objects.all().order_by("is_graduate", "name")


class MajorViewSet(viewsets.ModelViewSet):
    """
    list:
    Retrieve a list of all the majors (ex: Computer Science, BAS).

    retrieve:
    Retrieve a single major by ID.

    create:
    Add a new major to the list of majors.

    destroy:
    Remove a major from the list of majors.
    """

    serializer_class = MajorSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    queryset = Major.objects.all()


class StudentTypeViewSet(viewsets.ModelViewSet):
    """
    list:
    Retrieve a list of all the student types
    (ex: Online Student, Transfer Student, etc).

    retrieve:
    Retrieve a single student type by ID.

    create:
    Add a new student type to the list of student types.

    destroy:
    Remove a student type from the list of student types.
    """

    serializer_class = StudentTypeSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    queryset = StudentType.objects.all().order_by("name")


class YearViewSet(viewsets.ModelViewSet):
    """
    list:
    Retrieve a list of all of the graduation years
    (ex: Freshman, Sophomore, Junior, Senior).

    retrieve:
    Retrieve a single graduation year by ID.

    create:
    Add a new graduation year to the list of graduation years.

    destroy:
    Remove a graduation year from the list of graduation years.
    """

    serializer_class = YearSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    queryset = Year.objects.all()

    def list(self, request, *args, **kwargs):
        """
        Sort items by reverse year. Since this calculation is done in Python, we need
        to apply it after the SQL query has been processed.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer_class()(queryset, many=True)
        return Response(sorted(serializer.data, key=lambda k: k["year"], reverse=True))


class AdvisorSearchFilter(filters.BaseFilterBackend):
    """
    A DRF filter to implement custom filtering logic for advisor objects.
    """

    def filter_queryset(self, request, queryset, view):
        public = request.GET.get("public")

        if public is not None:
            public = public.strip().lower()
            if public in {"true", "false"}:
                queryset = queryset.filter(public=public == "true")

        return queryset


class AdvisorViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of advisors for this club.

    create:
    Add an advisor to this club.

    put:
    Update an advisor for this club. All fields are required.

    patch:
    Update an advisor for this club. Only specified fields are updated.

    retrieve:
    Return a single advisor.

    destroy:
    Delete an advisor.
    """

    serializer_class = AdvisorSerializer
    permission_classes = [ClubItemPermission | IsSuperuser]
    filter_backends = [AdvisorSearchFilter]
    lookup_field = "id"
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        return Advisor.objects.filter(club__code=self.kwargs.get("club_code")).order_by(
            "name"
        )


class ClubEventViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of events for this club.

    retrieve:
    Return a single event.

    destroy:
    Delete an event.
    """

    permission_classes = [EventPermission | IsSuperuser]
    filter_backends = [filters.SearchFilter, ClubsSearchFilter, ClubsOrderingFilter]
    search_fields = [
        "name",
        "club__name",
        "club__subtitle",
        "description",
        "club__code",
    ]
    lookup_field = "id"
    http_method_names = ["get", "post", "put", "patch", "delete"]
    pagination_class = RandomPageNumberPagination

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return EventWriteSerializer
        return EventSerializer

    @action(detail=True, methods=["post"])
    def upload(self, request, *args, **kwargs):
        """
        Upload a picture for the event.
        ---
        requestBody:
            content:
                multipart/form-data:
                    schema:
                        type: object
                        properties:
                            file:
                                type: object
                                format: binary
        responses:
            "200":
                description: Returned if the file was successfully uploaded.
                content: &upload_resp
                    application/json:
                        schema:
                            type: object
                            properties:
                                detail:
                                    type: string
                                    description: The status of the file upload.
                                url:
                                    type: string
                                    description: >
                                        The URL of the newly uploaded file.
                                        Only exists if the file was successfully
                                        uploaded.
            "400":
                description: Returned if there was an error while uploading the file.
                content: *upload_resp
        ---
        """
        event = Event.objects.get(id=kwargs["id"])
        self.check_object_permissions(request, event)

        resp = upload_endpoint_helper(request, Event, "image", pk=event.pk)

        # if image uploaded, create thumbnail
        if status.is_success(resp.status_code):
            event.create_thumbnail(request)

        return resp

    def create(self, request, *args, **kwargs):
        """
        Has the option to create a recurring event by specifying an offset and an
        end date. Additionaly, do not let non-superusers create events with the
        `FAIR` type through the API.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        allOf:
                            - $ref: "#/components/schemas/EventWrite"
                            - type: object
                              properties:
                                is_recurring:
                                    type: boolean
                                    description: >
                                        If this value is set, then make
                                        recurring events instead of a single event.
                                offset:
                                    type: number
                                    description: >
                                        The offset between recurring events, in days.
                                        Only specify this if the event is recurring.
                                end_date:
                                    type: string
                                    format: date-time
                                    description: >
                                        The date when all items in the recurring event
                                        series should end. Only specify this if the
                                        event is recurring.

        ---
        """
        # get event type
        type = request.data.get("type", 0)
        if type == Event.FAIR and not self.request.user.is_superuser:
            raise DRFValidationError(
                detail="Approved activities fair events have already been created. "
                "See above for events to edit, and "
                f"please email {settings.FROM_EMAIL} if this is en error."
            )

        # handle recurring events
        if request.data.get("is_recurring", None) is not None:
            parent_recurring_event = RecurringEvent.objects.create()
            event_data = request.data.copy()
            start_time = parse(event_data.pop("start_time"))
            end_time = parse(event_data.pop("end_time"))
            offset = event_data.pop("offset")
            end_date = parse(event_data.pop("end_date"))
            event_data.pop("is_recurring")

            result_data = []
            while start_time < end_date:
                event_data["start_time"] = start_time
                event_data["end_time"] = end_time
                event_serializer = EventWriteSerializer(
                    data=event_data, context={"request": request, "view": self}
                )
                if event_serializer.is_valid():
                    ev = event_serializer.save()
                    ev.parent_recurring_event = parent_recurring_event
                    result_data.append(ev)
                else:
                    return Response(
                        event_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                start_time = start_time + datetime.timedelta(days=offset)
                end_time = end_time + datetime.timedelta(days=offset)

            Event.objects.filter(pk__in=[e.pk for e in result_data]).update(
                parent_recurring_event=parent_recurring_event
            )

            return Response(EventSerializer(result_data, many=True).data)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Do not let non-superusers delete events with the FAIR type through the API.
        """
        event = self.get_object()

        if event.type == Event.FAIR and not self.request.user.is_superuser:
            raise DRFValidationError(
                detail="You cannot delete activities fair events. "
                f"If you would like to do this, email {settings.FROM_EMAIL}."
            )

        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        qs = Event.objects.all()
        is_club_specific = self.kwargs.get("club_code") is not None
        if is_club_specific:
            qs = qs.filter(club__code=self.kwargs["club_code"])
            qs = qs.filter(
                Q(club__approved=True) | Q(type=Event.FAIR) | Q(club__ghost=True),
                club__archived=False,
            )
        else:
            qs = qs.filter(
                Q(club__approved=True)
                | Q(type=Event.FAIR)
                | Q(club__ghost=True)
                | Q(club__isnull=True),
                Q(club__isnull=True) | Q(club__archived=False),
            )

        return (
            qs.select_related("club", "creator")
            .prefetch_related(
                Prefetch(
                    "club__badges",
                    queryset=Badge.objects.filter(
                        fair__id=self.request.query_params.get("fair")
                    )
                    if "fair" in self.request.query_params
                    else Badge.objects.filter(visible=True),
                )
            )
            .order_by("start_time")
        )


class EventViewSet(ClubEventViewSet):
    """
    list:
    Return a list of events for the entire site.

    retrieve:
    Return a single event.

    destroy:
    Delete an event.
    """

    def get_operation_id(self, **kwargs):
        return f"{kwargs['operId']} (Global)"

    @action(detail=False, methods=["get"])
    def fair(self, request, *args, **kwargs):
        """
        Get the minimal information required for a fair directory listing.
        Groups by the start date of the event, and then the event category.
        Each event's club must have an associated fair badge in order to be displayed.
        ---
        parameters:
            - name: date
              in: query
              required: false
              description: >
                A date in YYYY-MM-DD format.
                If specified, will preview how this endpoint looked on the specified
                date.
              type: string
            - name: fair
              in: query
              required: false
              description: >
                A fair id. If specified, will preview how this endpoint will look for
                that fair. Overrides the date field if both are specified.
              type: number
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                fair:
                                    type: object
                                    $ref: "#/components/schemas/ClubFair"
                                events:
                                    type: array
                                    items:
                                        type: object
                                        properties:
                                            start_time:
                                                type: string
                                                format: date-time
                                            end_time:
                                                type: string
                                                format: date-time
                                            events:
                                                type: array
                                                items:
                                                    type: object
                                                    properties:
                                                        category:
                                                            type: string
                                                        events:
                                                            type: array
                                                            items:
                                                                type: object
                                                                properties:
                                                                    name:
                                                                        type: string
                                                                    code:
                                                                        type: string
        ---
        """
        # accept custom date for preview rendering
        date = request.query_params.get("date")
        if date in {"null", "undefined"}:
            date = None
        if date:
            date = parse(date)

        # accept custom fair for preview rendering
        fair = request.query_params.get("fair")
        if fair in {"null", "undefined"}:
            fair = None
        if fair:
            fair = int(re.sub(r"\D", "", fair))

        # cache the response for this endpoint with short timeout
        if date is None:
            key = f"events:fair:directory:{request.user.is_authenticated}:{fair}"
            cached = cache.get(key)
            if cached:
                return Response(cached)
        else:
            key = None

        # lookup fair from id
        if fair:
            fair = get_object_or_404(ClubFair, id=fair)
        else:
            fair = (
                ClubFair.objects.filter(
                    end_time__gte=timezone.now() - datetime.timedelta(minutes=30)
                )
                .order_by("start_time")
                .first()
            )
        if not date and fair is not None:
            date = fair.start_time.date()

        now = date or timezone.now()
        events = Event.objects.filter(
            type=Event.FAIR, club__badges__purpose="fair", club__badges__fair=fair
        )

        # filter event range based on the fair times or provide a reasonable fallback
        if fair is None:
            events = events.filter(
                start_time__lte=now + datetime.timedelta(days=7),
                end_time__gte=now - datetime.timedelta(days=1),
            )
        else:
            events = events.filter(
                start_time__lte=fair.end_time, end_time__gte=fair.start_time
            )

        events = events.values_list(
            "start_time", "end_time", "club__name", "club__code", "club__badges__label"
        ).distinct()
        output = {}
        for event in events:
            # group by start date
            ts = int(event[0].replace(second=0, microsecond=0).timestamp())
            if ts not in output:
                output[ts] = {
                    "start_time": event[0],
                    "end_time": event[1],
                    "events": {},
                }

            # group by category
            category = event[4]
            if category not in output[ts]["events"]:
                output[ts]["events"][category] = {
                    "category": category,
                    "events": [],
                }

            output[ts]["events"][category]["events"].append(
                {"name": event[2], "code": event[3]}
            )
        for item in output.values():
            item["events"] = list(
                sorted(item["events"].values(), key=lambda cat: cat["category"])
            )
            for category in item["events"]:
                category["events"] = list(
                    sorted(category["events"], key=lambda e: e["name"].casefold())
                )

        output = list(sorted(output.values(), key=lambda cat: cat["start_time"]))
        final_output = {
            "events": output,
            "fair": ClubFairSerializer(instance=fair).data,
        }
        if key:
            cache.set(key, final_output, 60 * 5)

        return Response(final_output)

    @action(detail=False, methods=["get"])
    def owned(self, request, *args, **kwargs):
        """
        Return all events that the user has officer permissions over.
        """
        if not request.user.is_authenticated:
            return Response([])

        now = timezone.now()

        events = self.filter_queryset(self.get_queryset()).filter(
            club__membership__person=request.user,
            club__membership__role__lte=Membership.ROLE_OFFICER,
            start_time__gte=now,
        )

        return Response(EventSerializer(events, many=True).data)


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of testimonials for this club.

    create:
    Create a new testimonial for this club.

    update:
    Update a testimonial for this club.
    All fields must be specified.

    partial_update:
    Update a testimonial for this club.
    Specify only the fields you want to update.

    retrieve:
    Retrieve a single testimonial.

    destroy:
    Delete a testimonial.
    """

    serializer_class = TestimonialSerializer
    permission_classes = [ClubItemPermission | IsSuperuser]

    def get_queryset(self):
        return Testimonial.objects.filter(club__code=self.kwargs["club_code"])


class QuestionAnswerViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of questions and answers for this club.

    create:
    Create a new question for this club.

    update:
    Change the question or the answer for this club.

    retrieve:
    Return a single testimonial.

    destroy:
    Delete a testimonial.
    """

    serializer_class = QuestionAnswerSerializer
    permission_classes = [QuestionAnswerPermission | IsSuperuser]

    def get_queryset(self):
        club_code = self.kwargs["club_code"]
        questions = QuestionAnswer.objects.filter(
            club__code=club_code, club__archived=False
        )

        if not self.request.user.is_authenticated:
            return questions.filter(approved=True)

        membership = Membership.objects.filter(
            club__code=club_code, person=self.request.user
        ).first()

        if self.request.user.is_superuser or (
            membership is not None and membership.role <= Membership.ROLE_OFFICER
        ):
            return questions

        return questions.filter(Q(approved=True) | Q(author=self.request.user))


class MembershipViewSet(viewsets.ModelViewSet):
    """
    list: Return a list of clubs that the logged in user is a member of.
    """

    serializer_class = UserMembershipSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = Membership.objects.filter(
            person=self.request.user, club__archived=False
        ).prefetch_related("club__tags")
        person = self.request.user
        queryset = queryset.prefetch_related(
            Prefetch(
                "club__favorite_set",
                queryset=Favorite.objects.filter(person=person),
                to_attr="user_favorite_set",
            ),
            Prefetch(
                "club__subscribe_set",
                queryset=Subscribe.objects.filter(person=person),
                to_attr="user_subscribe_set",
            ),
            Prefetch(
                "club__membership_set",
                queryset=Membership.objects.filter(person=person),
                to_attr="user_membership_set",
            ),
        )
        return queryset


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    list: Return a list of clubs that the logged in user has favorited.

    create: Favorite a club.

    destroy: Unfavorite a club.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "club__code"
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = Favorite.objects.filter(
            person=self.request.user, club__archived=False
        ).prefetch_related("club__tags")

        person = self.request.user
        queryset = queryset.prefetch_related(
            Prefetch(
                "club__favorite_set",
                queryset=Favorite.objects.filter(person=person),
                to_attr="user_favorite_set",
            ),
            Prefetch(
                "club__subscribe_set",
                queryset=Subscribe.objects.filter(person=person),
                to_attr="user_subscribe_set",
            ),
            Prefetch(
                "club__membership_set",
                queryset=Membership.objects.filter(person=person),
                to_attr="user_membership_set",
            ),
        )

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return FavoriteWriteSerializer
        return FavoriteSerializer


class UserUUIDAPIView(generics.RetrieveAPIView):
    """
    get: Retrieve the calendar URL with the appropriate uuid for the given user.
    """

    queryset = get_user_model().objects.all()
    serializer_class = UserUUIDSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get_operation_id(self, **kwargs):
        return "Retrieve Calendar Url"

    def get_object(self):
        user = self.request.user
        return user


class SubscribeViewSet(viewsets.ModelViewSet):
    """
    list: Return a list of clubs that the logged in user has subscribed to.

    create: Subscribe to a club.

    destroy: Unsubscribe from a club.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "club__code"
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = Subscribe.objects.filter(
            person=self.request.user, club__archived=False
        ).prefetch_related("club__tags")

        person = self.request.user
        queryset = queryset.prefetch_related(
            Prefetch(
                "club__favorite_set",
                queryset=Favorite.objects.filter(person=person),
                to_attr="user_favorite_set",
            ),
            Prefetch(
                "club__subscribe_set",
                queryset=Subscribe.objects.filter(person=person),
                to_attr="user_subscribe_set",
            ),
            Prefetch(
                "club__membership_set",
                queryset=Membership.objects.filter(person=person),
                to_attr="user_membership_set",
            ),
        )

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return UserSubscribeWriteSerializer
        return UserSubscribeSerializer


class ClubVisitViewSet(viewsets.ModelViewSet):
    """
    list: Return a list of clubs that the logged in user has visited.

    create: Visit a club.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "club__code"
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return ClubVisit.objects.filter(person=self.request.user, club__archived=False)

    def get_serializer_class(self):
        if self.action == "create":
            return UserClubVisitWriteSerializer
        return UserClubVisitSerializer


class SearchQueryViewSet(viewsets.ModelViewSet):
    """
    create: Add a new search query

    list: Superuser sees all queries, any other user sees only their own
    """

    serializer_class = SearchQuerySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return SearchQuery.objects.all()
        else:
            return SearchQuery.objects.filter(person=self.request.user)


class MembershipRequestViewSet(viewsets.ModelViewSet):
    """
    list: Return a list of clubs that the logged in user has sent membership request to.

    create: Sent membership request to a club.

    destroy: Deleted a membership request from a club.
    """

    serializer_class = UserMembershipRequestSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "club__code"
    http_method_names = ["get", "post", "delete"]

    def create(self, request, *args, **kwargs):
        """
        If a membership request object already exists, reuse it.
        """
        club = request.data.get("club", None)
        obj = MembershipRequest.objects.filter(
            club__code=club, person=request.user
        ).first()
        if obj is not None:
            obj.withdrew = False
            obj.save(update_fields=["withdrew"])
            return Response(UserMembershipRequestSerializer(obj).data)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Don't actually delete the membership request when it is withdrawn.

        This is to keep track of repeat membership requests and avoid spamming the club
        owners with requests.
        """
        obj = self.get_object()
        obj.withdrew = True
        obj.save(update_fields=["withdrew"])

        return Response({"success": True})

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            person=self.request.user, withdrew=False, club__archived=False,
        )


class MembershipRequestOwnerViewSet(XLSXFormatterMixin, viewsets.ModelViewSet):
    """
    list:
    Return a list of users who have sent membership request to the club.

    destroy:
    Delete a membership request for a specific user.
    """

    serializer_class = MembershipRequestSerializer
    permission_classes = [MembershipRequestPermission | IsSuperuser]
    http_method_names = ["get", "post", "delete"]
    lookup_field = "person__username"

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            club__code=self.kwargs["club_code"], withdrew=False
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, *ages, **kwargs):
        """
        Accept a membership request as a club officer.
        ---
        requestBody: {}
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                    description: >
                                        True if this request was properly processed.
        ---
        """
        request_object = self.get_object()
        Membership.objects.get_or_create(
            person=request_object.person, club=request_object.club
        )
        request_object.delete()
        return Response({"success": True})


class MemberViewSet(XLSXFormatterMixin, viewsets.ModelViewSet):
    """
    list:
    Return a list of members that are in the club.
    Returns more information about each member if the logged in user
    is a superuser or in the club.

    update:
    Update the role/title/status for a membership.
    You must specify all fields or use a patch request.

    partial_update:
    Update the role/title/status for a membership.
    Specify only the fields you want to change.

    retrieve:
    Return information about a specific membership between a student and the club.

    create:
    Add a member to a club.

    destroy:
    Kick out a member from a club.
    """

    serializer_class = MembershipSerializer
    permission_classes = [MemberPermission | IsSuperuser]
    http_method_names = ["get", "post", "put", "patch", "delete"]
    lookup_field = "person__username"

    def get_queryset(self):
        return (
            Membership.objects.filter(club__code=self.kwargs["club_code"])
            .order_by("-active", "role", "person__last_name", "person__first_name")
            .select_related("person", "person__profile")
        )

    def get_serializer_class(self):
        if self.request is not None and self.request.user.is_authenticated:
            if self.request.user.has_perm("clubs.manage_club") or (
                "club_code" in self.kwargs
                and Membership.objects.filter(
                    person=self.request.user, club__code=self.kwargs["club_code"]
                ).exists()
            ):
                return AuthenticatedMembershipSerializer
        return MembershipSerializer


class AssetViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of files that belong to this club.

    retrieve:
    Retrieve the contents of the specific file that belongs to this club.

    create:
    Upload a new file to the club file repository.

    destroy:
    Delete a file from the club file repository.
    """

    serializer_class = AssetSerializer
    permission_classes = [AssetPermission | IsSuperuser]
    parser_classes = [parsers.MultiPartParser]
    http_method_names = ["get", "post", "delete"]

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        resp = HttpResponse(obj.file, content_type="application/octet-stream")
        resp["Content-Disposition"] = "attachment; filename={}".format(obj.name)
        return resp

    def get_queryset(self):
        return Asset.objects.filter(club__code=self.kwargs["club_code"])


class NoteViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of notes that this club has created for other clubs.

    retrieve:
    Return a specific note that this club has created for another club.

    create:
    Create a new note on another club.

    destroy:
    Destroy an existing note on another club.
    """

    serializer_class = NoteSerializer
    permission_classes = [NotePermission | IsSuperuser]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        club = get_object_or_404(Club, code=self.kwargs["club_code"])

        queryset = Note.objects.filter(creating_club__code=self.kwargs["club_code"])
        queryset = filter_note_permission(queryset, club, self.request.user)

        return queryset


class TagViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of tags.

    get:
    Return details for a specific tag by name.
    """

    queryset = (
        Tag.objects.all().annotate(clubs=Count("club", distinct=True)).order_by("name")
    )
    serializer_class = TagSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    http_method_names = ["get"]
    lookup_field = "name"


class BadgeViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of badges.

    get:
    Return details for a specific badge by name.
    """

    serializer_class = BadgeSerializer
    permission_classes = [ReadOnly | IsSuperuser]
    http_method_names = ["get"]
    lookup_field = "name"

    def get_queryset(self):
        show_all = self.request.query_params.get("all", "false") == "true"
        fair = self.request.query_params.get("fair", None)

        if show_all:
            return Badge.objects.all()
        elif fair and fair not in {"null", "undefined"}:
            return Badge.objects.filter(fair__id=fair)

        return Badge.objects.filter(visible=True)


def parse_boolean(inpt):
    if not isinstance(inpt, str):
        return inpt
    inpt = inpt.strip().lower()
    if inpt in {"true", "yes", "y"}:
        return True
    elif inpt in {"false", "no", "n"}:
        return False
    return None


class FavoriteCalendarAPIView(APIView):
    def get(self, request, *args, **kwargs):
        """
        Return a .ics file of the user's favorite club events.
        ---
        parameters:
            - name: global
              in: query
              required: false
              description: >
                If specified, either only show global events
                if true or exclude global events if false.
            - name: all
              in: query
              required: false
              description: >
                If set to true, show all events instead of only subscribed events.
        responses:
            "200":
                description: Return a calendar file in ICS format.
                content:
                    text/calendar:
                        schema:
                            type: string
        ---
        """
        is_global = parse_boolean(request.query_params.get("global"))
        is_all = parse_boolean(request.query_params.get("all"))

        calendar = ICSCal(creator=f"{settings.BRANDING_SITE_NAME} ({settings.DOMAIN})")
        calendar.extra.append(
            ICSParse.ContentLine(
                name="X-WR-CALNAME", value=f"{settings.BRANDING_SITE_NAME} Events"
            )
        )

        # only fetch events newer than the past month
        one_month_ago = timezone.now() - datetime.timedelta(days=30)
        all_events = Event.objects.filter(start_time__gte=one_month_ago)

        # filter based on user supplied flags
        q = Q(club__favorite__person__profile__uuid_secret=kwargs["user_secretuuid"])
        if is_global is None:
            q |= Q(club__isnull=True)

        if is_global:
            all_events = all_events.filter(club__isnull=True)
        elif not is_all:
            all_events = all_events.filter(q)

        all_events = all_events.distinct().select_related("club")

        for event in all_events:
            e = ICSEvent()
            e.name = "{} - {}".format(event.club.name, event.name)
            e.begin = event.start_time

            # ensure event is at least 15 minutes for display purposes
            e.end = (
                (event.start_time + datetime.timedelta(minutes=15))
                if event.start_time >= event.end_time
                else event.end_time
            )

            # put url in location if location does not exist, otherwise put url in body
            if event.location:
                e.location = event.location
            else:
                e.location = event.url
            e.url = event.url
            e.description = "{}\n\n{}".format(
                event.url or "" if not event.location else "",
                html_to_text(event.description),
            ).strip()
            e.uid = f"{event.ics_uuid}@{settings.DOMAIN}"
            e.created = event.created_at
            e.last_modified = event.updated_at
            e.categories = [event.club.name]

            calendar.events.add(e)

        response = HttpResponse(calendar, content_type="text/calendar")
        response["Content-Disposition"] = "attachment; filename=favorite_events.ics"
        return response


class FakeView(object):
    """
    Dummy view used for permissions checking by the UserPermissionAPIView.
    """

    def __init__(self, action):
        self.action = action


class UserGroupAPIView(APIView):
    """
    get: Return the major permission groups and their members on the site.
    """

    permission_classes = [DjangoPermission("clubs.manage_club")]

    def get(self, request):
        """
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: object
                                properties:
                                    code:
                                        type: string
                                    members:
                                        type: object
                                        properties:
                                            username:
                                                type: string
                                            name:
                                                type: string
        ---
        """
        perms = [
            "approve_club",
            "generate_reports",
            "manage_club",
            "see_fair_status",
            "see_pending_clubs",
        ]
        output = {}
        for name in perms:
            perm = Permission.objects.get(codename=name)
            output[name] = (
                get_user_model()
                .objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm))
                .distinct()
                .values_list("username", "first_name", "last_name")
            )
        output["superuser"] = (
            get_user_model()
            .objects.filter(is_superuser=True)
            .values_list("username", "first_name", "last_name")
        )
        output = [
            {
                "code": k,
                "members": [
                    {"username": x[0], "name": f"{x[1]} {x[2]}".strip()} for x in v
                ],
            }
            for k, v in output.items()
        ]
        return Response(output)


class UserPermissionAPIView(APIView):
    """
    get: Check if a user has a specific permission or list of permissions separated by
    commas, or return a list of all user permissions.

    This endpoint can accept general Django permissions or per object Django
    permissions, with the permission name and lookup key for the object separated by a
    colon. A general Django permission will grant access to the per object version
    if the user has the general permission.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                permissions:
                                    type: object
                                    additionalProperties:
                                        type: boolean
        ---
        """
        raw_perms = [
            perm.strip()
            for perm in request.GET.get("perm", "").strip().split(",")
            if perm
        ]

        if not request.user.is_authenticated:
            return Response({"permissions": {k: False for k in raw_perms}})

        general_perms = [p for p in raw_perms if ":" not in p]
        object_perms = [p for p in raw_perms if ":" in p]

        # process general permissions
        ret = {}
        all_perms = request.user.get_all_permissions()
        if raw_perms:
            for perm in general_perms:
                ret[perm] = request.user.is_superuser or perm in all_perms
        else:
            for perm in all_perms:
                ret[perm] = True

        # process object specific permissions
        lookups = {}

        for perm in object_perms:
            key, value = perm.split(":", 1)

            # if user has the global permission for all objects
            if request.user.is_superuser or key in all_perms:
                ret[perm] = True
                continue

            # otherwise, add permission to individual lookup queue
            if key not in lookups:
                lookups[key] = []
            ret[perm] = None
            lookups[key].append(value)

        # lookup individual permissions grouped by permission
        for key, values in lookups.items():
            if key in {"clubs.manage_club", "clubs.delete_club"}:
                perm_checker = ClubPermission()
                view = FakeView("destroy" if key == "clubs.delete_club" else "update")
                objs = Club.objects.filter(code__in=values)
                global_perm = perm_checker.has_permission(request, view)
                for obj in objs:
                    perm = f"{key}:{obj.code}"
                    ret[perm] = global_perm and perm_checker.has_object_permission(
                        request, view, obj
                    )

        return Response({"permissions": ret})


def zoom_api_call(user, verb, url, *args, **kwargs):
    """
    Perform an API call to Zoom with various checks.

    If the call returns a token expired event,
    refresh the token and try the call one more time.
    """
    if not settings.SOCIAL_AUTH_ZOOM_OAUTH2_KEY:
        raise DRFValidationError(
            "Server is not configured with Zoom OAuth2 credentials."
        )

    if not user.is_authenticated:
        raise DRFValidationError("You are not authenticated.")

    social = user.social_auth.filter(provider="zoom-oauth2").first()
    if social is None:
        raise DRFValidationError("You have not linked your Zoom account yet.")

    is_retry = "retry" in kwargs
    if is_retry:
        del kwargs["retry"]

    out = requests.request(
        verb,
        url.format(uid=social.uid),
        *args,
        headers={"Authorization": f"Bearer {social.get_access_token(load_strategy())}"},
        **kwargs,
    )

    if out.status_code == 204:
        return out

    # check for token expired event
    data = out.json()
    if data.get("code") == 124 and not is_retry:
        social.refresh_token(load_strategy())
        kwargs["retry"] = True
        return zoom_api_call(user, verb, url, *args, **kwargs)

    return out


def generate_zoom_password():
    """
    Create a secure Zoom password for the meeting.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(10))


class MeetingZoomWebhookAPIView(APIView):
    """
    get: Given an event id, return the number of people on the Zoom call.

    post: Trigger this webhook. Should be triggered when a Zoom event occurs.
    Not available to the public, requires Zoom verification token.
    """

    def get(self, request):
        """
        ---
        parameters:
            - name: event
              in: query
              type: integer
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                attending:
                                    type: integer
                                    description: >
                                        Number of users currently attending the meeting.
                                        Includes the club officers.
                                officers:
                                    type: integer
                                    description: >
                                        Number of officers attending the meeting.
                                attended:
                                    type: integer
                                    description: >
                                        Number of users that attended the meeting
                                        before. Does not include currently attending
                                        users.
                                time:
                                    type: number
                                    description: >
                                        Number of seconds that the median user attended
                                        the meeting.
        ---
        """
        event_id = request.query_params.get("event")

        time_query = (
            ZoomMeetingVisit.objects.filter(
                event__id=event_id, leave_time__isnull=False
            )
            .annotate(
                time=ExpressionWrapper(
                    F("leave_time") - F("join_time"), DurationField()
                )
            )
            .order_by("time")
        )
        time_index = time_query.count()
        if time_index > 0:
            time_index //= 2
            median_time = time_query[time_index].time
        else:
            median_time = 0

        return Response(
            {
                "attending": ZoomMeetingVisit.objects.filter(
                    event__id=event_id, leave_time__isnull=True
                ).count(),
                "attended": ZoomMeetingVisit.objects.filter(
                    event__id=event_id, leave_time__isnull=False
                )
                .values("person")
                .distinct()
                .count(),
                "officers": ZoomMeetingVisit.objects.filter(
                    event__id=event_id,
                    leave_time__isnull=True,
                    person=F("event__club__membership__person"),
                )
                .values("person")
                .distinct()
                .count(),
                "time": median_time,
            }
        )

    def post(self, request):
        # security check to make sure request contains zoom provided token
        if settings.ZOOM_VERIFICATION_TOKEN:
            authorization = request.META.get("HTTP_AUTHORIZATION")
            if authorization != settings.ZOOM_VERIFICATION_TOKEN:
                return Response(
                    {
                        "detail": "Your authorization token is invalid!",
                        "success": False,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        action = request.data.get("event")
        event_id = None
        if action == "meeting.participant_joined":
            email = (
                request.data.get("payload", {})
                .get("object", {})
                .get("participant", {})
                .get("email", None)
            )

            if email:
                username = email.split("@")[0]
                person = get_user_model().objects.filter(username=username).first()
            else:
                person = None

            meeting_id = (
                request.data.get("payload", {}).get("object", {}).get("id", None)
            )
            regex = (
                rf"https?:\/\/([A-z]*.)?zoom.us/[^\/]*\/{meeting_id}(\?pwd=[A-z,0-9]*)?"
            )
            event = Event.objects.filter(url__regex=regex).first()

            participant_id = (
                request.data.get("payload", {})
                .get("object", {})
                .get("participant", {})
                .get("user_id", None)
            )
            join_time = (
                request.data.get("payload", {})
                .get("object", {})
                .get("participant", {})
                .get("join_time", None)
            )

            if event:
                ZoomMeetingVisit.objects.create(
                    person=person,
                    event=event,
                    meeting_id=meeting_id,
                    participant_id=participant_id,
                    join_time=join_time,
                )
                event_id = event.id
        elif action == "meeting.participant_left":
            meeting_id = (
                request.data.get("payload", {}).get("object", {}).get("id", None)
            )
            participant_id = (
                request.data.get("payload", {})
                .get("object", {})
                .get("participant", {})
                .get("user_id", None)
            )
            leave_time = (
                request.data.get("payload", {})
                .get("object", {})
                .get("participant", {})
                .get("leave_time", None)
            )

            meeting = (
                ZoomMeetingVisit.objects.filter(
                    meeting_id=meeting_id,
                    participant_id=participant_id,
                    leave_time__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )
            if meeting is not None:
                meeting.leave_time = leave_time
                meeting.save()
                event_id = meeting.event.id

        if event_id is not None:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f"events-live-{event_id}", {"type": "join_leave", "event": action}
                )

        return Response({"success": True})


class MeetingZoomAPIView(APIView):
    """
    get: Return a list of upcoming Zoom meetings for a user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                meetings:
                                    type: object
                                    additionalProperties:
                                        type: string
                                extra_details:
                                    type: object
                                    additionalProperties:
                                        type: string
        ---
        """
        refresh = request.query_params.get("refresh", "false").lower() == "true"

        if request.user.is_authenticated:
            key = f"zoom:meetings:{request.user.username}"
            if not refresh:
                res = cache.get(key)
                if res is not None:
                    return Response(res)

        try:
            data = zoom_api_call(
                request.user, "GET", "https://api.zoom.us/v2/users/{uid}/meetings"
            )
        except requests.exceptions.HTTPError as e:
            raise DRFValidationError(
                "An error occured while fetching meetings for current user."
            ) from e

        # get meeting ids
        body = data.json()
        meetings = [meeting["id"] for meeting in body.get("meetings", [])]

        # get user events
        if request.user.is_authenticated:
            events = Event.objects.filter(
                club__membership__role__lte=Membership.ROLE_OFFICER,
                club__membership__person=request.user,
            )
        else:
            events = []

        extra_details = {}
        for event in events:
            if event.url is not None and "zoom.us" in event.url:
                match = re.search(r"(\d+)", urlparse(event.url).path)
                if match is not None:
                    zoom_id = int(match[1])
                    if zoom_id in meetings:
                        try:
                            individual_data = zoom_api_call(
                                request.user,
                                "GET",
                                f"https://api.zoom.us/v2/meetings/{zoom_id}",
                            ).json()
                            extra_details[individual_data["id"]] = individual_data
                        except requests.exceptions.HTTPError:
                            pass

        response = {
            "success": data.ok,
            "meetings": body,
            "extra_details": extra_details,
        }
        if response["success"]:
            cache.set(key, response, 120)
        return Response(response)

    def delete(self, request):
        """
        Delete the Zoom meeting for this event.
        """
        event = get_object_or_404(Event, id=request.query_params.get("event"))

        if (
            not request.user.has_perm("clubs.manage_club")
            and not event.club.membership_set.filter(
                person=request.user, role__lte=Membership.ROLE_OFFICER
            ).exists()
        ):
            return Response(
                {
                    "success": False,
                    "detail": "You do not have permission to perform this action.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if event.url:
            match = re.search(r"(\d+)", urlparse(event.url).path)
            if "zoom.us" in event.url and match is not None:
                zoom_id = int(match[1])
                zoom_api_call(
                    request.user, "DELETE", f"https://api.zoom.us/v2/meetings/{zoom_id}"
                )

            event.url = None
            event.save()
            return Response(
                {
                    "success": True,
                    "detail": "The Zoom meeting has been unlinked and deleted.",
                }
            )
        else:
            return Response(
                {
                    "success": True,
                    "detail": "There is no Zoom meeting configured for this event.",
                }
            )

    def post(self, request):
        """
        Create a new Zoom meeting for this event
        or try to fix the existing zoom meeting.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                detail:
                                    type: string
        ---
        """
        try:
            event = Event.objects.get(id=request.query_params.get("event"))
        except Event.DoesNotExist as e:
            raise DRFValidationError(
                "The event you are trying to modify does not exist."
            ) from e

        eastern = pytz.timezone("America/New_York")

        # ensure user can do this
        if not request.user.has_perm(
            "clubs.manage_club"
        ) and not event.club.membership_set.filter(
            role__lte=Membership.ROLE_OFFICER, person=request.user
        ):
            return Response(
                {
                    "success": False,
                    "detail": "You are not allowed to perform this action!",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # add all other officers as alternative hosts
        alt_hosts = []
        for mship in event.club.membership_set.filter(
            role__lte=Membership.ROLE_OFFICER
        ):
            social = mship.person.social_auth.filter(provider="zoom-oauth2").first()
            if social is not None:
                alt_hosts.append(social.extra_data["email"])

        # recommended zoom meeting settings
        recommended_settings = {
            "audio": "both",
            "join_before_host": True,
            "mute_upon_entry": True,
            "waiting_room": False,
            "meeting_authentication": True,
            "authentication_domains": "upenn.edu,*.upenn.edu",
        }

        if alt_hosts:
            recommended_settings["alternative_hosts"] = ",".join(alt_hosts)

        if not event.url:
            password = generate_zoom_password()
            body = {
                "topic": f"Virtual Activities Fair - {event.club.name}",
                "type": 2,
                "start_time": event.start_time.astimezone(eastern)
                .replace(tzinfo=None, microsecond=0, second=0)
                .isoformat(),
                "duration": (event.end_time - event.start_time)
                / datetime.timedelta(minutes=1),
                "timezone": "America/New_York",
                "agenda": f"Virtual Activities Fair Booth for {event.club.name}",
                "password": password,
                "settings": recommended_settings,
            }
            data = zoom_api_call(
                request.user,
                "POST",
                "https://api.zoom.us/v2/users/{uid}/meetings",
                json=body,
            )
            out = data.json()
            event.url = out.get("join_url", "")
            event.save(update_fields=["url"])
            return Response(
                {
                    "success": True,
                    "detail": "Your Zoom meeting has been created! "
                    "The following Zoom accounts have been made hosts:"
                    f" {', '.join(alt_hosts)}",
                }
            )
        else:
            parsed_url = urlparse(event.url)

            if "zoom.us" not in parsed_url.netloc:
                return Response(
                    {
                        "success": False,
                        "detail": "The current meeting link is not a Zoom link. "
                        "If you would like to have your Zoom link automatically "
                        "generated, please clear the URL field and try again.",
                    }
                )

            if "upenn.zoom.us" not in parsed_url.netloc:
                return Response(
                    {
                        "success": False,
                        "detail": "The current meeting link is not a Penn Zoom link. "
                        "If you would like to have your Penn Zoom link automatically "
                        "generated, login with your Penn Zoom account, clear the URL "
                        "from your event, and try this process again.",
                    }
                )

            match = re.search(r"(\d+)", parsed_url.path)
            if match is None:
                return Response(
                    {
                        "success": False,
                        "detail": "Failed to parse your URL, "
                        "are you sure this is a valid Zoom link?",
                    }
                )

            zoom_id = int(match[1])

            data = zoom_api_call(
                request.user, "GET", f"https://api.zoom.us/v2/meetings/{zoom_id}"
            )
            out = data.json()
            event.url = out.get("join_url", event.url)
            event.save(update_fields=["url"])

            start_time = (
                event.start_time.astimezone(eastern)
                .replace(tzinfo=None, microsecond=0, second=0)
                .isoformat()
            )

            body = {
                "start_time": start_time,
                "duration": (event.end_time - event.start_time)
                / datetime.timedelta(minutes=1),
                "timezone": "America/New_York",
                "settings": recommended_settings,
            }

            out = zoom_api_call(
                request.user,
                "PATCH",
                f"https://api.zoom.us/v2/meetings/{zoom_id}",
                json=body,
            )

            return Response(
                {
                    "success": out.ok,
                    "detail": "Your Zoom meeting has been updated. "
                    "The following accounts have been made hosts:"
                    f" {', '.join(alt_hosts)}"
                    if out.ok
                    else "Your Zoom meeting has not been updated. "
                    "Are you the owner of the meeting?",
                }
            )


class UserZoomAPIView(APIView):
    """
    get: Return information about the Zoom account associated with the logged in user.

    post: Update the Zoom account settings to be the recommended Penn Clubs settings.
    """

    def get(self, request):
        """
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                settings:
                                    type: object
                                    additionalProperties:
                                        type: string
                                email:
                                    type: string
        ---
        """
        refresh = request.query_params.get("refresh", "false").lower() == "true"
        no_cache = request.query_params.get("noCache", "false").lower() == "true"

        if request.user.is_authenticated:
            key = f"zoom:user:{request.user.username}"
            res = cache.get(key)
            if res is not None:
                if not refresh:
                    if res.get("success") is True:
                        return Response(res)
                    else:
                        cache.delete(key)
                if no_cache:
                    cache.delete(key)

        try:
            response = zoom_api_call(
                request.user, "GET", "https://api.zoom.us/v2/users/{uid}/settings",
            )
        except requests.exceptions.HTTPError as e:
            raise DRFValidationError(
                "An error occured while fetching user information. "
                "Your authentication with the Zoom API might have expired. "
                "Try reconnecting your account."
            ) from e

        social = request.user.social_auth.filter(provider="zoom-oauth2").first()
        if social is None:
            email = None
        else:
            email = social.extra_data.get("email")

        settings = response.json()
        res = {
            "success": settings.get("code") is None,
            "settings": settings,
            "email": email,
        }

        if res["success"]:
            cache.set(key, res, 900)
        return Response(res)

    def post(self, request):
        """
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                success:
                                    type: boolean
                                detail:
                                    type: string
        ---
        """
        if request.user.is_authenticated:
            key = f"zoom:user:{request.user.username}"
            cache.delete(key)

        response = zoom_api_call(
            request.user,
            "PATCH",
            "https://api.zoom.us/v2/users/{uid}/settings",
            json={
                "in_meeting": {
                    "breakout_room": True,
                    "waiting_room": False,
                    "co_host": True,
                    "screen_sharing": True,
                }
            },
        )

        return Response(
            {
                "success": response.ok,
                "detail": "Your user settings have been updated on Zoom."
                if response.ok
                else "Failed to update Zoom user settings.",
            }
        )


class UserUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    get: Return information about the logged in user, including bookmarks,
    subscriptions, memberships, and school/major/graduation year information.

    put: Update information about the logged in user.
    All fields are required.

    patch: Update information about the logged in user.
    Only updates fields that are passed to the server.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        """
        Cache the settings endpoint for 5 minutes or until user data is updated.
        """
        key = f"user:settings:{request.user.username}"
        val = cache.get(key)
        if val:
            return Response(val)
        resp = super().get(request, *args, **kwargs)
        cache.set(key, resp.data, 5 * 60)
        return resp

    def put(self, request, *args, **kwargs):
        """
        Clear the cache when putting user settings.
        """
        key = f"user:settings:{request.user.username}"
        cache.delete(key)
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Clear the cache when patching user settings.
        """
        key = f"user:settings:{request.user.username}"
        cache.delete(key)
        return super().patch(request, *args, **kwargs)

    def get_operation_id(self, **kwargs):
        if kwargs["action"] == "get":
            return "Retrieve Self User"
        return None

    def get_object(self):
        user = self.request.user
        prefetch_related_objects(
            [user], "profile__school", "profile__major",
        )
        return user


class MemberInviteViewSet(viewsets.ModelViewSet):
    """
    update:
    Accept a membership invite.

    partial_update:
    Accept a membership invite.

    destroy:
    Rescind a membership invite.
    """

    permission_classes = [InvitePermission | IsSuperuser]
    serializer_class = MembershipInviteSerializer
    http_method_names = ["get", "put", "patch", "delete"]

    def get_operation_id(self, **kwargs):
        if kwargs["action"] == "resend":
            return f"{kwargs['operId']} ({kwargs['method']})"
        return None

    @action(detail=True, methods=["put", "patch"])
    def resend(self, request, *args, **kwargs):
        """
        Resend an email invitation that has already been issued.
        ---
        requestBody: {}
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                detail:
                                    type: string
                                    description: A success or error message.
        ---
        """
        invite = self.get_object()
        invite.send_mail(request)
        invite.updated_at = timezone.now()
        invite.save(update_fields=["updated_at"])

        return Response(
            {"detail": "Resent email invitation to {}!".format(invite.email)}
        )

    def destroy(self, request, *args, **kwargs):
        invite = self.get_object()

        if request.user.is_authenticated:
            membership = find_membership_helper(request.user, invite.club)
            is_officer = (
                membership is not None and membership.role <= Membership.ROLE_OFFICER
            )
        else:
            is_officer = False

        # if we're not an officer and haven't specified the token
        # don't let us delete this invite
        if (
            not request.data.get("token") == invite.token
            and not is_officer
            and not request.user.has_perm("clubs.manage_club")
        ):
            return Response(
                {"detail": "Invalid or missing token in request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        return MembershipInvite.objects.filter(
            club__code=self.kwargs["club_code"], active=True
        )


class ExternalMemberListViewSet(viewsets.ModelViewSet):
    """
    get: Retrieve members' nonsensitive information per club
    """

    http_method_names = ["get"]
    serializer_class = ExternalMemberListSerializer

    def get_queryset(self):
        return (
            Membership.objects.all()
            .select_related("person", "club")
            .filter(club__code=self.kwargs["code"])
        )


class UserViewSet(viewsets.ModelViewSet):
    """
    list: Retrieve a list of users.

    get: Retrieve the profile information for given user.
    """

    queryset = get_user_model().objects.all().select_related("profile")
    permission_classes = [ProfilePermission | IsSuperuser]
    filter_backends = [filters.SearchFilter]
    http_method_names = ["get"]

    search_fields = [
        "email",
        "first_name",
        "last_name",
        "username",
    ]
    lookup_field = "username"

    def get_serializer_class(self):
        if self.action in {"list"}:
            return MinimalUserProfileSerializer
        return UserProfileSerializer


class ClubApplicationViewSet(viewsets.ModelViewSet):
    """
    create: Create an application for the club.

    list: Retrieve a list of applications of the club.

    get: Retrieve the details for a given application.
    """

    permission_classes = [ClubItemPermission | IsSuperuser]
    serializer_class = ClubApplicationSerializer
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return WritableClubApplicationSerializer
        return ClubApplicationSerializer

    def get_queryset(self):
        now = timezone.now()

        return ClubApplication.objects.filter(
            club__code=self.kwargs["club_code"], result_release_time__gte=now
        ).order_by("application_end_time")


class MassInviteAPIView(APIView):
    """
    Send out invites and add invite objects
    given a list of comma or newline separated emails.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        club = get_object_or_404(Club, code=kwargs["club_code"])

        mem = Membership.objects.filter(club=club, person=request.user).first()

        if not request.user.has_perm("clubs.manage_club") and (
            not mem or not mem.role <= Membership.ROLE_OFFICER
        ):
            return Response(
                {
                    "detail": "You do not have permission to invite new members!",
                    "success": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        role = request.data.get("role", Membership.ROLE_MEMBER)
        title = request.data.get("title")

        if not title:
            return Response(
                {
                    "detail": "You must enter a title for the members "
                    "that you are inviting.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if mem and mem.role > role and not request.user.is_superuser:
            return Response(
                {
                    "detail": "You cannot send invites "
                    "for a role higher than your own!",
                    "success": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        emails = [x.strip() for x in re.split(r"\n|,", request.data.get("emails", ""))]
        emails = [x for x in emails if x]

        original_count = len(emails)

        # remove users that are already in the club
        exist = Membership.objects.filter(
            club=club, person__email__in=emails
        ).values_list("person__email", flat=True)
        emails = list(set(emails) - set(exist))

        # remove users that have already been invited
        exist = MembershipInvite.objects.filter(
            club=club, email__in=emails, active=True
        ).values_list("email", flat=True)
        emails = list(set(emails) - set(exist))

        # ensure all emails are valid
        try:
            for email in emails:
                validate_email(email)
        except ValidationError:
            return Response(
                {
                    "detail": "The email address '{}' is not valid!".format(email),
                    "success": False,
                }
            )

        # send invites to all emails
        for email in emails:
            invite = MembershipInvite.objects.create(
                email=email, club=club, creator=request.user, role=role, title=title
            )
            if role <= Membership.ROLE_OWNER and not mem:
                invite.send_owner_invite(request)
            else:
                invite.send_mail(request)

        sent_emails = len(emails)
        skipped_emails = original_count - len(emails)

        return Response(
            {
                "detail": "Sent invite{} to {} email{}! {} email{} skipped.".format(
                    "" if sent_emails == 1 else "s",
                    sent_emails,
                    "" if sent_emails == 1 else "s",
                    skipped_emails,
                    "" if skipped_emails == 1 else "s",
                ),
                "sent": sent_emails,
                "skipped": skipped_emails,
                "success": True,
            }
        )


class EmailInvitesAPIView(generics.ListAPIView):
    """
    get: Return the club code, invite id and token of
    the email invitations for the current user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserMembershipInviteSerializer

    def get_operation_id(self, **kwargs):
        return "List Email Invitations for Self"

    def get_queryset(self):
        return MembershipInvite.objects.filter(
            email=self.request.user.email, active=True, club__archived=False
        ).order_by("-created_at")


class OptionListView(APIView):
    def get(self, request):
        """
        Return a list of options, with some options dynamically generated.
        This response is intended for site-wide global variables.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            additionalProperties:
                                type: string
        ---
        """
        # compute base django options
        options = {
            k: v
            for k, v in Option.objects.filter(public=True).values_list("key", "value")
        }

        # add in activities fair information
        now = timezone.now()

        fairs = ClubFair.objects.filter(
            Q(start_time__lte=now + datetime.timedelta(weeks=1))
            | Q(registration_start_time__lte=now),
            end_time__gte=now - datetime.timedelta(minutes=15),
        ).order_by("start_time")

        fair = fairs.first()
        if fair:
            happening = fair.start_time <= now - datetime.timedelta(minutes=3)
            close = fair.start_time >= now - datetime.timedelta(weeks=1)
            options["FAIR_NAME"] = fair.name
            options["FAIR_ID"] = fair.id
            options["FAIR_OPEN"] = happening
            options["PRE_FAIR"] = not happening and close
        else:
            options["FAIR_OPEN"] = False
            options["PRE_FAIR"] = False

        return Response(options)


class LoggingArgumentParser(argparse.ArgumentParser):
    """
    An argument parser that logs added arguments.
    """

    def __init__(self, *args, **kwargs):
        self._arguments = {}
        self._pos_count = 0
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        super().add_argument(*args, **kwargs)

        if kwargs.get("default") == "==SUPPRESS==":
            return

        name = kwargs.get("dest", args[0].strip(" -").replace("-", "_"))
        default = kwargs.get("default")
        typ = kwargs.get(
            "type",
            bool
            if kwargs.get("action") == "store_true"
            else type(default)
            if default is not None
            else str,
        )
        pos = -1
        if not args[0].startswith("-"):
            pos = self._pos_count
            self._pos_count += 1
        self._arguments[name] = {
            "position": pos,
            "type": typ.__name__ if typ is not None else typ,
            "help": re.sub(r"\s+", " ", kwargs.get("help", "")) or None,
            "default": default,
            "choices": kwargs.get("choices"),
        }

    def set_defaults(self, *args, **kwargs):
        super().set_defaults(*args, **kwargs)
        for arg, value in kwargs.items():
            if arg in self._arguments:
                self._arguments[arg]["default"] = value

    def get_arguments(self):
        return self._arguments


@functools.lru_cache(maxsize=None)
def get_scripts():
    """
    Return a list of Django management commands and some associated metadata.
    """
    commands = get_commands()
    scripts = []
    for name, path in commands.items():
        cls = load_command_class(path, name)
        parser = LoggingArgumentParser()
        cls.add_arguments(parser)
        scripts.append(
            {
                "name": name,
                "path": path,
                "description": re.sub(r"\s+", " ", cls.help),
                "execute": hasattr(cls, "web_execute") and cls.web_execute,
                "arguments": parser.get_arguments(),
            }
        )
    scripts.sort(key=lambda s: (not s["execute"], s["name"]))
    return scripts


def parse_script_parameters(script, parameters):
    """
    Turn a list of user specified parameters into a set of args and kwargs that can
    be passed to call_command(), given the corresponding script.

    Use the script that is returned from get_scripts().
    """
    args = []
    kwargs = {}
    for arg, details in script["arguments"].items():
        if parameters.get(arg) is not None:
            value = {"str": str, "bool": bool, "int": int}.get(details["type"], str)(
                parameters[arg]
            )
            if details["position"] == -1:
                kwargs[arg] = value
            else:
                args.append((details["position"], value))
    args = [arg[1] for arg in sorted(args)]
    return args, kwargs


class ScriptExecutionView(APIView):
    """
    View and execute Django management scripts using these endpoints.
    """

    permission_classes = [DjangoPermission("clubs.manage_club") | IsSuperuser]

    def get(self, request):
        """
        Return a list of valid management scripts to execute.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: object
                                properties:
                                    name:
                                        type: string
                                    path:
                                        type: string
                                    description:
                                        type: string
                                    execute:
                                        type: boolean
                                    arguments:
                                        type: object
                                        additionalProperties:
                                            type: object
                                            properties:
                                                type:
                                                    type: string
                                                help:
                                                    type: string
                                                position:
                                                    type: integer
                                                default:
                                                    type: string
                                                choices:
                                                    type: array
                                                    items:
                                                        type: string
                                                    nullable: true
        ---
        """
        scripts = get_scripts()
        return Response(scripts)

    def post(self, request):
        """
        Execute a management script.
        ---
        responses:
            "200":
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                output:
                                    type: string
        ---
        """
        action = request.data.get("action")
        parameters = request.data.get("parameters", {})
        scripts = get_scripts()
        script = next((s for s in scripts if s["name"] == action), None)

        # check for validity and permission
        if script is None:
            return Response({"output": f"'{action}' is not a valid script to execute."})
        if not script["execute"]:
            return Response(
                {
                    "output": "You are not allowed to "
                    f"execute '{action}' from the web interface."
                }
            )

        args, kwargs = parse_script_parameters(script, parameters)

        # execute command and return output
        with io.StringIO() as output:
            call_command(action, *args, **kwargs, stdout=output, stderr=output)
            return Response({"output": output.getvalue()})


def get_initial_context_from_types(types):
    """
    Generate a sample context given the specified types.
    """
    # handle edge case where user explicitly says there are no types
    if isinstance(types, str) and types == "None":
        return {}

    # this allows for tuples to work properly
    context = collections.OrderedDict()

    for name, value in types.items():
        is_array = value["type"] == "array"
        if is_array:
            value = value["items"]

        if value["type"] == "string":
            context[name] = value.get("default", f"[{name}]")
        elif value["type"] == "number":
            context[name] = int(value.get("default", 0))
        elif value["type"] == "boolean":
            context[name] = bool(value.get("default", False))
        elif value["type"] == "object":
            context[name] = get_initial_context_from_types(value["properties"])
        elif value["type"] == "tuple":
            context[name] = tuple(
                get_initial_context_from_types(value["properties"]).values()
            )
        else:
            raise ValueError(f"Unknown email variable type '{value['type']}'!")

        # if is array, duplicate value three times as a sample
        if is_array:
            context[name] = [context[name]] * 3

    return context


def email_preview(request):
    """
    Debug endpoint used for previewing how email templates will look.
    """
    prefix = "fyh_emails" if settings.BRANDING == "fyh" else "emails"
    email_templates = os.listdir(os.path.join(settings.BASE_DIR, "templates", prefix))
    email_templates = [
        e.rsplit(".", 1)[0] for e in email_templates if e.endswith(".html")
    ]

    email = None
    text_email = None
    initial_context = {}

    if "email" in request.GET:
        email_path = os.path.basename(request.GET.get("email"))

        # initial values
        types = get_mail_type_annotation(email_path)
        if types is not None:
            initial_context = get_initial_context_from_types(types)

        # set specified values
        variables = request.GET.get("variables")
        if variables is not None:
            initial_context.update(json.loads(variables))

        email = render_to_string(f"{prefix}/{email_path}.html", initial_context)
        text_email = html_to_text(email)

    return render(
        request,
        "preview.html",
        {
            "templates": email_templates,
            "email": email,
            "text_email": text_email,
            "variables": json.dumps(initial_context, indent=4),
        },
    )
