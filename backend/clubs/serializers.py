import json
import re
from urllib.parse import parse_qs, urlparse

import bleach
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Prefetch
from django.template.defaultfilters import slugify
from django.utils import timezone
from rest_framework import serializers, validators
from simple_history.utils import update_change_reason

from clubs.mixins import ManyToManySaveMixin
from clubs.models import (
    Advisor,
    ApplicationQuestion,
    ApplicationQuestionResponse,
    Asset,
    Badge,
    Club,
    ClubApplication,
    ClubFair,
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
)
from clubs.utils import clean


ALL_TAGS_SELECTED_ERROR_MESSAGE = (
    (
        "We noticed you selected all of the options "
        "for one or more of the previous tags. "
        "In order to best optimize our sorting algorithm, "
        "you need to select only the few "
        "tags that apply to your resource. "
        "If you feel that all the tags apply, that's great! "
        "In that case you would select 'Yes' to the "
        "question asking if your resource applies to "
        "all undergraduate, graduate, and professional Penn students. "
        "Thanks for doing your part to ensure that Hub@Penn "
        "quickly and efficiently gets resources to our Penn community. "
    )
    if settings.BRANDING == "fyh"
    else (
        "You should not select all of the items in this list. "
        "If all of these items apply, select none of them instead."
    )
)


class ClubRouteMixin(object):
    """
    Mixin for serializers that overrides the save method to
    properly handle the URL parameter for club.
    """

    def save(self):
        self.validated_data["club"] = Club.objects.get(
            code=self.context["view"].kwargs.get("club_code")
        )

        return super().save()


class TagSerializer(serializers.ModelSerializer):
    clubs = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ("id", "name", "clubs")


class BadgeSerializer(serializers.ModelSerializer):
    purpose = serializers.CharField(read_only=True)

    class Meta:
        model = Badge
        fields = ("id", "purpose", "label", "color", "description")


class SchoolSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    is_graduate = serializers.BooleanField(read_only=True)

    class Meta:
        model = School
        fields = ("id", "name", "is_graduate")


class MajorSerializer(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = Major
        fields = ("id", "name")


class TestimonialSerializer(ClubRouteMixin, serializers.ModelSerializer):
    text = serializers.CharField()

    class Meta:
        model = Testimonial
        fields = ("id", "text")


class QuestionAnswerSerializer(ClubRouteMixin, serializers.ModelSerializer):
    author = serializers.SerializerMethodField("get_author_name")
    responder = serializers.SerializerMethodField("get_responder_name")
    is_anonymous = serializers.BooleanField(write_only=True)

    def get_author_name(self, obj):
        user = self.context["request"].user
        if obj.author == user:
            return "{} (Anonymous)".format(obj.author.get_full_name())
        if obj.is_anonymous or obj.author is None:
            return "Anonymous"
        return obj.author.get_full_name()

    def get_responder_name(self, obj):
        if obj.responder is None:
            return obj.club.name
        return obj.responder.get_full_name()

    def validate_question(self, value):
        """
        The club owner is not allowed to edit the user's question.
        Users are not allowed to edit their question after it has
        been responded to.
        """
        if not self.instance:
            return value

        if not value == self.instance.question:
            user = self.context["request"].user
            if not user == self.instance.author:
                raise serializers.ValidationError(
                    "You are not allowed to edit the author's question!"
                )

            if self.instance.answer:
                raise serializers.ValidationError(
                    "You are not allowed to edit the question "
                    "after an answer has been given!"
                )

        return value

    def validate_is_anonymous(self, value):
        """
        Only the author should be able to change the status of their post's anonymity.
        """
        if not self.instance:
            return value

        if not value == self.instance.is_anonymous:
            user = self.context["request"].user
            if not user == self.instance.author:
                raise serializers.ValidationError(
                    "You are not allowed to change the anonymity status of this post!"
                )

        return value

    def validate_answer(self, value):
        """
        Only a club officer may respond to a question.
        An answer may not be set to null after it has been answered.
        """
        if value is None:
            if self.instance and self.instance.answer is not None:
                raise serializers.ValidationError(
                    "You are not allowed to unanswer a question! "
                    + "You can change the answer text instead."
                )
            return value

        value = clean(bleach.linkify(value))

        club = Club.objects.get(code=self.context["view"].kwargs.get("club_code"))
        user = self.context["request"].user

        if user.is_superuser:
            return value

        membership = Membership.objects.filter(person=user, club=club).first()
        if membership is not None and membership.role <= Membership.ROLE_OFFICER:
            return value

        raise serializers.ValidationError(
            "You are not allowed to answer this question!"
        )

    def update(self, instance, validated_data):
        """
        If the question or answer has changed, set the new author appropriately.
        """
        user = self.context["request"].user

        if (
            "question" in validated_data
            and not validated_data["question"] == instance.question
        ):
            validated_data["author"] = user

        if (
            "answer" in validated_data
            and not validated_data["answer"] == instance.answer
        ):
            validated_data["responder"] = user
            validated_data["approved"] = True

        return super().update(instance, validated_data)

    def create(self, validated_data):
        """
        Set the author of the question to the current user.
        Send out an email to officers and above notifying them of this question.
        """
        validated_data["author"] = self.context["request"].user

        obj = super().create(validated_data)

        obj.send_question_mail(self.context["request"])

        return obj

    class Meta:
        model = QuestionAnswer
        fields = (
            "id",
            "question",
            "answer",
            "author",
            "responder",
            "is_anonymous",
            "approved",
        )


class ReportSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField("get_creator")

    def get_creator(self, obj):
        return obj.creator.get_full_name()

    def create(self, validated_data):
        """
        Set the creator of the report to the current user.
        If a report with the same name and creator exists,
        overwrite that report instead.
        """
        return Report.objects.update_or_create(
            name=validated_data.pop("name"),
            creator=self.context["request"].user,
            defaults=validated_data,
        )[0]

    class Meta:
        model = Report
        fields = (
            "id",
            "name",
            "creator",
            "description",
            "parameters",
            "created_at",
            "updated_at",
            "public",
        )


class YearSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    year = serializers.ReadOnlyField()

    class Meta:
        model = Year
        fields = ("id", "name", "year")


class AdvisorSerializer(
    ClubRouteMixin, ManyToManySaveMixin, serializers.ModelSerializer
):
    class Meta:
        model = Advisor
        fields = ("id", "name", "title", "department", "email", "phone", "public")


class ClubEventSerializer(serializers.ModelSerializer):
    """
    Within the context of an existing club, return events that are a part of this club.
    """

    image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_url = serializers.SerializerMethodField("get_image_url")
    large_image_url = serializers.SerializerMethodField("get_large_image_url")
    url = serializers.SerializerMethodField("get_event_url")
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def get_event_url(self, obj):
        # if no url, return that
        if not obj.url:
            return obj.url

        # if is zoom link, hide url unless authenticated
        if "request" in self.context and "zoom.us" in urlparse(obj.url).netloc:
            user = self.context["request"].user
            if user.is_authenticated:
                return obj.url
            return "(Login to view url)"

        return obj.url

    def get_large_image_url(self, obj):
        image = obj.image

        # correct path rendering
        if not image:
            return None
        if image.url.startswith("http"):
            return image.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(image.url)
        else:
            return image.url

    def get_image_url(self, obj):
        # use thumbnail if exists
        image = obj.image_small
        if not image:
            image = obj.image

        # fix image path in development
        if not image:
            return None
        if image.url.startswith("http"):
            return image.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(image.url)
        else:
            return image.url

    def validate_url(self, value):
        """
        Ensure that the URL is valid.
        """
        # convert none to blank
        if value is None:
            value = ""

        # remove surrounding whitespace
        value = value.strip()

        # throw an error if the url is not valid
        if value:
            validate = URLValidator()
            try:
                validate(value)
            except DjangoValidationError:
                raise serializers.ValidationError(
                    "The URL you entered does not appear to be valid. "
                    "Please check your URL and try again."
                )

        # expand links copied from google calendar
        if value:
            parsed = urlparse(value)
            if parsed.netloc.endswith(".google.com") and parsed.path == "/url":
                return parse_qs(parsed.query)["q"][0]

        return value

    def validate_description(self, value):
        """
        Allow the description to have HTML tags that come from a whitelist.
        """
        return clean(bleach.linkify(value))

    def validate(self, data):
        start_time = data.get(
            "start_time",
            self.instance.start_time if self.instance is not None else None,
        )
        end_time = data.get(
            "end_time", self.instance.end_time if self.instance is not None else None
        )
        if start_time is not None and end_time is not None and start_time > end_time:
            raise serializers.ValidationError(
                "Your event start time must be less than the end time!"
            )
        return data

    def update(self, instance, validated_data):
        # ensure user cannot update start time or end time for a fair event
        user = self.context["request"].user
        if not (user.is_authenticated and user.has_perm("clubs.see_fair_status")):
            if instance and instance.type == Event.FAIR:
                unchanged_fields = {"start_time", "end_time"}
                for field in unchanged_fields:
                    if (
                        field in validated_data
                        and not getattr(self.instance, field, None)
                        == validated_data[field]
                    ):
                        raise serializers.ValidationError(
                            "You cannot change the meeting time for a fair event! "
                            "If you would like to, please contact the fair organizers."
                        )

        return super().update(instance, validated_data)

    def save(self):
        if "club" not in self.validated_data:
            self.validated_data["club"] = Club.objects.get(
                code=self.context["view"].kwargs.get("club_code")
            )

        if not self.validated_data.get("code") and self.validated_data.get("name"):
            self.validated_data["code"] = slugify(self.validated_data["name"])

        return super().save()

    class Meta:
        model = Event
        fields = [
            "creator",
            "description",
            "end_time",
            "id",
            "image",
            "image_url",
            "is_ics_event",
            "large_image_url",
            "location",
            "name",
            "start_time",
            "type",
            "url",
        ]


class EventSerializer(ClubEventSerializer):
    """
    A serializer for an event that includes basic associated club information.
    """

    club = serializers.SlugRelatedField(
        queryset=Club.objects.all(), required=False, slug_field="code"
    )
    club_name = serializers.SerializerMethodField()
    badges = BadgeSerializer(source="club.badges", many=True, read_only=True)
    pinned = serializers.BooleanField(read_only=True)

    def get_club_name(self, obj):
        if obj.club is None:
            return None
        return obj.club.name

    class Meta:
        model = Event
        fields = ClubEventSerializer.Meta.fields + [
            "club",
            "club_name",
            "badges",
            "pinned",
        ]


class EventWriteSerializer(EventSerializer):
    """
    A serializer for an event that is used when creating/editing the event.

    Enables URL checking for the url field.
    """

    url = serializers.CharField(
        max_length=2048, required=False, allow_blank=True, allow_null=True
    )

    def update(self, instance, validated_data):
        """
        Enforce only changing the meeting link to Zoom links for activities fair events.
        """
        if instance.type == Event.FAIR and "url" in validated_data:
            old_url = instance.url or ""
            new_url = validated_data.get("url", "")
            # if the two urls are not equal, perform additional checks
            if old_url != new_url:
                parsed_url = urlparse(new_url)

                if ".zoom.us" not in parsed_url.netloc and new_url:
                    raise serializers.ValidationError(
                        {
                            "url": "You should use a Zoom link for the meeting url! "
                            "You can use the Zoom setup page to do this for you."
                        }
                    )

        return super().update(instance, validated_data)


class MembershipInviteSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=8, read_only=True)
    email = serializers.EmailField(read_only=True)
    token = serializers.CharField(max_length=128, write_only=True)
    name = serializers.CharField(source="club.name", read_only=True)
    public = serializers.BooleanField(write_only=True, required=False)

    def create(self, validated_data):
        validated_data.pop("public", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        public = validated_data.pop("public", False)

        if not self.validated_data.get("token") == self.instance.token:
            raise serializers.ValidationError("Missing or invalid token in request!")

        # if there is an owner and the invite is for a upenn email,
        # do strict username checking
        if (
            self.instance.email.endswith((".upenn.edu", "@upenn.edu"))
            and self.instance.club.membership_set.count() > 0
        ):
            # penn medicine emails have multiple aliases
            if not self.instance.email.endswith("@pennmedicine.upenn.edu"):
                invite_username = self.instance.email.rsplit("@", 1)[0]
                if not (
                    invite_username.lower() == user.username.lower()
                    or self.instance.email == user.email
                ):
                    raise serializers.ValidationError(
                        f"This invitation was meant for {invite_username}, "
                        f"but you are logged in as {user.username}!"
                    )

        # claim the invite and set the membership public status
        obj = instance.claim(user)
        obj.public = public
        obj.save()

        # if a membership request exists, delete it
        MembershipRequest.objects.filter(person=user, club=self.instance.club).delete()

        return instance

    class Meta:
        model = MembershipInvite
        fields = [
            "email",
            "id",
            "name",
            "public",
            "role",
            "title",
            "token",
            "updated_at",
        ]


class ExternalMemberListSerializer(serializers.ModelSerializer):
    """
    This serializer is used for listing non-sensitive data
    accessible to the public via CORS
    """

    name = serializers.CharField(source="person.username")
    image = serializers.SerializerMethodField("get_image")

    def get_image(self, obj):
        if not obj.image and not obj.person.profile.image:
            return None
        return obj.image.url if obj.image else obj.person.profile.image.url

    class Meta:
        model = Membership
        fields = ["name", "role", "description", "image"]


class UserMembershipInviteSerializer(MembershipInviteSerializer):
    """
    This serializer is used for listing the email invitations
    that the current user was sent.
    """

    token = serializers.CharField(max_length=128)
    code = serializers.CharField(source="club.code", read_only=True)

    class Meta(MembershipInviteSerializer.Meta):
        fields = MembershipInviteSerializer.Meta.fields + ["code"]


class MembershipSerializer(ClubRouteMixin, serializers.ModelSerializer):
    """
    Used for listing which users are in a club for members who are not in the club.
    """

    email = serializers.SerializerMethodField("get_email")
    username = serializers.SerializerMethodField("get_username")
    name = serializers.SerializerMethodField("get_full_name")
    person = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), write_only=True
    )
    role = serializers.IntegerField(write_only=True, required=False)
    image = serializers.SerializerMethodField("get_image")

    def get_username(self, obj):
        if not obj.public:
            return None
        return obj.person.username

    def get_full_name(self, obj):
        if not obj.public:
            return "Anonymous"
        return obj.person.get_full_name()

    def get_email(self, obj):
        if not obj.public or not obj.person.profile.show_profile:
            return None
        return obj.person.email

    def get_image(self, obj):
        if not obj.public:
            return None
        if not obj.image and not obj.person.profile.image:
            return None
        image_url = obj.image.url if obj.image else obj.person.profile.image.url

        if image_url.startswith("http"):
            return image_url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(image_url)
        else:
            return image_url

    def validate_role(self, value):
        """
        Ensure that users cannot promote themselves to a higher role.
        Also ensure that owners can't demote themselves without leaving another owner.
        """
        user = self.context["request"].user
        mem_user_id = (
            self.instance.person.id if self.instance else self.initial_data["person"]
        )
        club_code = self.context["view"].kwargs.get(
            "club_code", self.context["view"].kwargs.get("code")
        )
        membership = Membership.objects.filter(
            person=user, club__code=club_code
        ).first()
        if user.has_perm("clubs.manage_club"):
            return value
        if membership is None:
            raise serializers.ValidationError(
                "You must be a member of this club to modify roles!"
            )
        if membership.role > value:
            raise serializers.ValidationError(
                "You cannot promote someone above your own level."
            )
        if value > Membership.ROLE_OWNER and user.id == mem_user_id:
            if membership.role <= Membership.ROLE_OWNER:
                if (
                    Membership.objects.filter(
                        club__code=club_code, role__lte=Membership.ROLE_OWNER
                    ).count()
                    <= 1
                ):
                    raise serializers.ValidationError(
                        "You cannot demote yourself if you are the only owner!"
                    )
        return value

    def validate(self, data):
        """
        Normal members can only change a small subset of information.
        """
        user = self.context["request"].user
        club_code = self.context["view"].kwargs.get(
            "club_code", self.context["view"].kwargs.get("code")
        )

        membership = Membership.objects.filter(
            person=user, club__code=club_code
        ).first()

        if not user.is_superuser and (
            membership is None or membership.role > Membership.ROLE_OFFICER
        ):
            for field in data:
                if field not in {"active", "public"}:
                    raise serializers.ValidationError(
                        'Normal members are not allowed to change "{}"!'.format(field)
                    )
        return data

    class Meta:
        model = Membership
        fields = [
            "active",
            "email",
            "image",
            "name",
            "person",
            "public",
            "role",
            "title",
            "username",
            "description",
        ]


class AuthenticatedMembershipSerializer(MembershipSerializer):
    """
    Provides additional information about members, such as email address.
    Should only be available to users in the club.
    """

    role = serializers.IntegerField(required=False)
    email = serializers.EmailField(source="person.email", read_only=True)
    username = serializers.CharField(source="person.username", read_only=True)

    def get_full_name(self, obj):
        return obj.person.get_full_name()

    class Meta(MembershipSerializer.Meta):
        pass


class ClubMinimalSerializer(serializers.ModelSerializer):
    """
    Return only the club name, code, and approval status for a club.
    """

    class Meta:
        model = Club
        fields = ["name", "code", "approved"]


class ClubConstitutionSerializer(ClubMinimalSerializer):
    """
    Return the minimal information, as well as the files that the club has uploaded.
    """

    files = serializers.SerializerMethodField("get_constitution")

    def get_constitution(self, obj):
        user = self.context["request"].user
        perm = user.is_authenticated and user.has_perm("clubs.see_pending_clubs")
        if hasattr(obj, "user_membership_set"):
            has_member = bool(obj.user_membership_set)
        else:
            has_member = False
        if hasattr(obj, "prefetch_asset_set"):
            return [
                {
                    "name": asset.name if perm or has_member else None,
                    "url": asset.file.url if perm or has_member else None,
                }
                for asset in obj.prefetch_asset_set
                if asset.name.endswith((".docx", ".doc", ".pdf"))
                or "constitution" in asset.name.lower()
            ]
        return None

    class Meta(ClubMinimalSerializer.Meta):
        fields = ClubMinimalSerializer.Meta.fields + ["files"]


class ClubListSerializer(serializers.ModelSerializer):
    """
    The club list serializer returns a subset of the information that the full
    serializer returns.
    Optimized for the home page, some fields may be missing if not necessary.
    For example, if the subtitle is set, the description is returned as null.
    This is done for a quicker response.
    """

    tags = TagSerializer(many=True)
    image_url = serializers.SerializerMethodField("get_image_url")
    favorite_count = serializers.IntegerField(read_only=True)
    membership_count = serializers.IntegerField(read_only=True)
    is_favorite = serializers.SerializerMethodField("get_is_favorite")
    is_subscribe = serializers.SerializerMethodField("get_is_subscribe")
    is_member = serializers.SerializerMethodField("get_is_member")

    email = serializers.SerializerMethodField("get_email")
    subtitle = serializers.SerializerMethodField("get_short_description")

    def get_email(self, obj):
        if obj.email_public:
            return obj.email
        return "Hidden"

    def get_short_description(self, obj):
        if obj.subtitle:
            return obj.subtitle

        # return first sentence of description without html tags
        desc = obj.description.lstrip()[:1000]
        cleaned_desc = re.sub(r"<[^>]+>", "", desc)
        return (
            "".join(re.split(r"(\.|\n|!)", cleaned_desc)[:2])
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&ndash;", "-")
            .replace("&mdash;", "-")
            .replace("&nbsp;", " ")
            .strip()
        )

    def get_is_favorite(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        if hasattr(obj, "user_favorite_set"):
            return bool(obj.user_favorite_set)
        return obj.favorite_set.filter(person=user).exists()

    def get_is_subscribe(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        if hasattr(obj, "user_subscribe_set"):
            return bool(obj.user_subscribe_set)
        return obj.subscribe_set.filter(person=user).exists()

    def get_is_member(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        if hasattr(obj, "user_membership_set"):
            mship = next(iter(obj.user_membership_set), None)
        else:
            mship = obj.membership_set.filter(person=user).first()
        if mship is None:
            return False
        return mship.role

    def get_image_url(self, obj):
        # use small version if exists
        image = obj.image_small
        if not image:
            image = obj.image

        # correct path rendering
        if not image:
            return None
        if image.url.startswith("http"):
            return image.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(image.url)
        else:
            return image.url

    def get_fields(self):
        """
        Override the fields that are returned if the "fields" GET parameter
        is specified. Acts as a filter on the returned fields.
        """
        all_fields = super().get_fields()

        # add in additional report fields
        if hasattr(self.__class__, "get_additional_fields"):
            for fields in self.__class__.get_additional_fields().values():
                for field in fields.values():
                    all_fields[field] = ReportClubField(field, read_only=True)

        fields_param = getattr(self.context.get("request", dict()), "GET", {}).get(
            "fields", ""
        )
        if fields_param:
            fields_param = fields_param.split(",")
        else:
            return all_fields

        fields_subset = dict()
        for k in fields_param:
            if k in all_fields:
                fields_subset[k] = all_fields[k]

        return fields_subset if len(fields_subset) > 0 else all_fields

    def to_representation(self, instance):
        """
        Return the previous approved version of a club for users
        that should not see unapproved content.
        """
        if instance.ghost and not instance.approved:
            user = self.context["request"].user

            can_see_pending = user.has_perm("clubs.see_pending_clubs") or user.has_perm(
                "clubs.manage_club"
            )
            is_member = (
                user.is_authenticated
                and instance.membership_set.filter(person=user).exists()
            )
            if not can_see_pending and not is_member:
                historical_club = (
                    instance.history.filter(approved=True)
                    .order_by("-approved_on")
                    .first()
                )
                if historical_club is not None:
                    approved_instance = historical_club.instance
                    approved_instance._is_historical = True
                    return super().to_representation(approved_instance)
        return super().to_representation(instance)

    class Meta:
        model = Club
        fields = [
            "accepting_members",
            "active",
            "address",
            "application_required",
            "appointment_needed",
            "approved",
            "available_virtually",
            "code",
            "email",
            "enables_subscription",
            "favorite_count",
            "founded",
            "image_url",
            "is_favorite",
            "is_member",
            "is_subscribe",
            "membership_count",
            "recruiting_cycle",
            "name",
            "size",
            "subtitle",
            "tags",
        ]
        extra_kwargs = {
            "name": {
                "validators": [validators.UniqueValidator(queryset=Club.objects.all())],
                "help_text": "The name of the club.",
            },
            "code": {
                "required": False,
                "validators": [validators.UniqueValidator(queryset=Club.objects.all())],
                "help_text": "An alphanumeric string shown in the URL "
                "and used to identify this club.",
            },
            "description": {
                "help_text": "A long description for the club. "
                "Certain HTML tags are allowed."
            },
            "email": {"help_text": "The primary contact email for the club."},
            "subtitle": {
                "required": False,
                "help_text": "The text shown to the user in a preview card. "
                "Short description of the club.",
            },
        }


class MembershipClubListSerializer(ClubListSerializer):
    """
    The club list serializer, except return more detailed information about the
    relationship of the club with the authenticated user.

    Used on the user profile page to show additional information.
    """

    membership = serializers.SerializerMethodField("get_membership")

    def get_membership(self, obj):
        mship = obj.profile_membership_set[0]
        return {
            "active": mship.active,
            "title": mship.title,
            "role": mship.role,
        }

    def get_is_member(self, obj):
        """
        Don't return this information to prevent a N+1 SQL efficiency problem.
        """
        return None

    class Meta(ClubListSerializer.Meta):
        fields = ClubListSerializer.Meta.fields + ["membership"]


class StudentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentType
        fields = ("id", "name")


def social_validation_helper(value, domain, prefix="", at_prefix=None):
    """
    Help format and validate social URLs.
    Be lenient on the format and try to correct inputs where possible.
    """
    if not value:
        return value

    value = value.strip()

    parsed = urlparse(value)
    path = parsed.path
    if parsed.path.startswith("@"):
        path = "{}/{}/".format(
            at_prefix if at_prefix is not None else prefix, parsed.path[1:]
        )
    elif not parsed.path.startswith("/"):
        path = "{}/{}/".format(prefix, parsed.path)
    if parsed.query:
        path = "{}?{}".format(path, parsed.query)
    if isinstance(domain, list):
        if parsed.netloc in domain:
            domain = parsed.netloc
        else:
            domain = domain[0]
    return "https://{}{}".format(domain, path)


class TargetYearSerializer(serializers.ModelSerializer):
    """
    Used as a nested serializer by ClubSerializer
    """

    id = serializers.SerializerMethodField("get_id")

    class Meta:
        model = TargetYear
        fields = ("id", "program")

    def get_id(self, obj):
        return obj.target_years.id


class TargetSchoolSerializer(serializers.ModelSerializer):
    """
    Used as a nested serializer by ClubSerializer
    """

    id = serializers.SerializerMethodField("get_id")

    class Meta:
        model = TargetSchool
        fields = ("id", "program")

    def get_id(self, obj):
        return obj.target_schools.id


class TargetMajorSerializer(serializers.ModelSerializer):
    """
    Used as a nested serializer by ClubSerializer
    """

    id = serializers.SerializerMethodField("get_id")

    class Meta:
        model = TargetMajor
        fields = ("id", "program")

    def get_id(self, obj):
        return obj.target_majors.id


class TargetStudentTypeSerializer(serializers.ModelSerializer):
    """
    Used as a nested serializer by ClubSerializer
    """

    id = serializers.SerializerMethodField("get_id")

    class Meta:
        model = TargetMajor
        fields = ("id", "program")

    def get_id(self, obj):
        return obj.target_student_types.id


class ClubSerializer(ManyToManySaveMixin, ClubListSerializer):
    members = MembershipSerializer(many=True, source="membership_set", read_only=True)
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)
    badges = BadgeSerializer(many=True, required=False)
    testimonials = TestimonialSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField("get_events")
    is_request = serializers.SerializerMethodField("get_is_request")
    student_types = serializers.SerializerMethodField("get_target_student_types")
    approved_comment = serializers.CharField(required=False, allow_blank=True)
    approved_by = serializers.SerializerMethodField("get_approved_by")
    advisor_set = serializers.SerializerMethodField("get_advisor_set")

    target_schools = serializers.SerializerMethodField("get_target_schools")
    target_majors = serializers.SerializerMethodField("get_target_majors")
    target_years = serializers.SerializerMethodField("get_target_years")

    subtitle = serializers.CharField(required=False, allow_blank=True, max_length=255)

    is_ghost = serializers.SerializerMethodField("get_is_ghost")

    # don't use url fields so we can allow for more lax inputs
    website = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    facebook = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    instagram = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    twitter = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    linkedin = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    github = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    youtube = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def get_fairs(self, obj):
        return list(obj.clubfair_set.values_list("id", flat=True))

    def get_events(self, obj):
        now = timezone.now()
        return ClubEventSerializer(
            obj.events.filter(end_time__gte=now).order_by("start_time"),
            many=True,
            read_only=True,
            context=self.context,
        ).data

    def get_is_ghost(self, obj):
        if obj.ghost:
            return True
        return hasattr(obj, "_is_historical")

    def get_approved_by(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return None
        if not user.has_perm("clubs.see_pending_clubs"):
            return None
        if obj.approved_by is None:
            return "Unknown"
        return obj.approved_by.get_full_name()

    def get_advisor_set(self, obj):
        return AdvisorSerializer(
            obj.advisor_set.filter(public=True).order_by("name"),
            many=True,
            read_only=True,
            context=self.context,
        ).data

    def get_is_request(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.membershiprequest_set.filter(person=user, withdrew=False).exists()

    def get_target_years(self, obj):
        qset = TargetYear.objects.filter(club=obj)
        return [TargetYearSerializer(m).data for m in qset]

    def get_target_majors(self, obj):
        qset = TargetMajor.objects.filter(club=obj)
        return [TargetMajorSerializer(m).data for m in qset]

    def get_target_schools(self, obj):
        qset = TargetSchool.objects.filter(club=obj)
        return [TargetSchoolSerializer(m).data for m in qset]

    def get_target_student_types(self, obj):
        qset = TargetStudentType.objects.filter(club=obj)
        return [TargetStudentTypeSerializer(m).data for m in qset]

    def create(self, validated_data):
        """
        Ensure new clubs follow certain invariants.
        """
        # New clubs created through the API must always be approved.
        validated_data["approved"] = None

        obj = super().create(validated_data)

        # assign user who created as owner
        Membership.objects.create(
            person=self.context["request"].user, club=obj, role=Membership.ROLE_OWNER
        )

        if not settings.BRANDING == "fyh":
            # send a renewal email prompting the user
            # to apply for approval for their club
            obj.send_renewal_email()

        return obj

    def validate_badges(self, value):
        return value

    def validate_tags(self, value):
        """
        Check for required tags before saving the club.
        """
        if settings.BRANDING == "clubs":
            tag_names = [tag.get("name") for tag in value]
            necessary_tags = {"Undergraduate", "Graduate"}
            if not any(tag in necessary_tags for tag in tag_names):
                if Tag.objects.filter(name__in=list(necessary_tags)).count() >= len(
                    necessary_tags
                ):
                    raise serializers.ValidationError(
                        "You must specify either the {} tag in this list.".format(
                            " or ".join(f"'{tag}'" for tag in necessary_tags)
                        )
                    )
        return value

    def validate_target_years(self, value):
        """
        Ensure that the user does not select all of the target years.
        """
        if len(value) >= Year.objects.count():
            raise serializers.ValidationError(ALL_TAGS_SELECTED_ERROR_MESSAGE)
        return value

    def validate_target_schools(self, value):
        """
        Ensure that the user does not select all of the target schools.
        """
        if len(value) >= School.objects.count():
            raise serializers.ValidationError(ALL_TAGS_SELECTED_ERROR_MESSAGE)
        return value

    def validate_target_majors(self, value):
        """
        Ensure that the user does not select all of the target majors.
        """
        if len(value) >= Major.objects.count():
            raise serializers.ValidationError(ALL_TAGS_SELECTED_ERROR_MESSAGE)
        return value

    def validate_student_types(self, value):
        """
        Ensure that the user does not select all of the student types.
        """
        if len(value) >= StudentType.objects.count():
            raise serializers.ValidationError(ALL_TAGS_SELECTED_ERROR_MESSAGE)
        return value

    def validate_description(self, value):
        """
        Allow the description to have HTML tags that come from a whitelist.
        The description must exist and not be extremely short.
        """
        out = clean(value).strip()
        if len(out) <= 10:
            raise serializers.ValidationError(
                "You must enter a valid description for your organization."
            )
        return out

    def validate_how_to_get_involved(self, value):
        """
        Allow the how to get involved field to have whitelisted HTML tags.
        """
        return clean(bleach.linkify(value))

    def validate_signature_events(self, value):
        """
        Allow the signature events field to have whitelisted HTML tags.
        """
        return clean(bleach.linkify(value))

    def validate_email(self, value):
        """
        You must enter a contact email.
        """
        if not value:
            raise serializers.ValidationError(
                "You must enter a contact email for notification purposes. "
                "You can decide whether or not to display this email to the public. "
                "If you do not have a club email, you can use an officer email."
            )
        return value

    def validate_website(self, value):
        """
        Ensure that the URL is actually a website.
        If no schema is specified, add the https:// schema for them by default.
        """
        # blank is ok
        if not value:
            return value

        value = value.strip()

        # add schema if not exists
        if not re.match(r"^\w+://", value):
            value = f"https://{value}"

        validate = URLValidator()
        try:
            validate(value)
        except DjangoValidationError:
            raise serializers.ValidationError(
                "The URL you entered does not appear to be valid. "
                "Please check your URL and try again."
            )
        return value

    def validate_facebook(self, value):
        """
        Ensure that URL is actually a Facebook link.
        """
        return social_validation_helper(
            value, "facebook.com", prefix="/groups", at_prefix=""
        )

    def validate_twitter(self, value):
        """
        Ensure that URL is actually a Twitter link.
        """
        return social_validation_helper(value, "twitter.com")

    def validate_instagram(self, value):
        """
        Ensure that the URL is actually a instagram link.
        """
        return social_validation_helper(value, "instagram.com")

    def validate_linkedin(self, value):
        """
        Ensure that URL is actually a LinkedIn URL.
        Attempt to convert into correct format with limited information.
        """
        return social_validation_helper(value, "linkedin.com", prefix="/company")

    def validate_github(self, value):
        """
        Ensure that URL is actually a GitHub URL.
        """
        return social_validation_helper(value, "github.com")

    def validate_youtube(self, value):
        """
        Ensure that URL is actually a YouTube URL.
        """
        return social_validation_helper(value, ["youtube.com", "youtu.be"])

    def validate_active(self, value):
        """
        Only officers, owners, and superusers may change the active status of a club.
        """
        user = self.context["request"].user

        # people with approve permissions can also change the active status of the club
        if user.has_perm("clubs.approve_club"):
            return value

        # check if at least an officer
        club_code = self.context["view"].kwargs.get("code")
        club = Club.objects.get(code=club_code)
        membership = Membership.objects.filter(person=user, club=club).first()
        if membership and membership.role <= Membership.ROLE_OFFICER:
            return value

        # otherwise, can't edit this field
        raise serializers.ValidationError(
            "You do not have permissions to change the active status of the club."
        )

    def format_members_for_spreadsheet(self, value):
        """
        Specify the spreadsheet format for the membership ManyToMany field.
        """
        return "\n".join("{} - {}".format(v.get("name"), v.get("email")) for v in value)

    def save(self):
        """
        Override save in order to replace code with slugified name if not specified.
        """
        # remove any spaces from the name
        if "name" in self.validated_data:
            self.validated_data["name"] = self.validated_data["name"].strip()

        # set the code to the name
        if not self.instance:
            if not self.validated_data.get("code") and self.validated_data.get("name"):
                self.validated_data["code"] = slugify(self.validated_data["name"])
        elif "code" in self.validated_data:
            del self.validated_data["code"]

        approval_email_required = False

        # if key fields were edited, require re-approval
        needs_reapproval = False
        if self.instance:
            for field in {"name", "image", "description"}:
                if field in self.validated_data and not self.validated_data[
                    field
                ] == getattr(self.instance, field, None):
                    needs_reapproval = True
                    break

        # if the editing user has approval permissions, skip the approval process
        request = self.context.get("request", None)
        if request and request.user.has_perm("clubs.approve_club"):
            needs_reapproval = False

        has_approved_version = (
            self.instance and self.instance.history.filter(approved=True).exists()
        )

        if needs_reapproval:
            self.validated_data["approved"] = None
            self.validated_data["approved_by"] = None
            self.validated_data["approved_on"] = None
            self.validated_data["ghost"] = has_approved_version

        # if approval was revoked, also reset the other fields
        if (
            "approved" in self.validated_data
            and self.validated_data["approved"] is None
        ):
            self.validated_data["approved"] = None
            self.validated_data["approved_by"] = None
            self.validated_data["approved_on"] = None

        # if approved, update who and when club was approved
        new_approval_status = self.validated_data.get("approved")

        # check if was active before
        was_active = self.instance and self.instance.active

        if (
            self.instance
            and self.instance.approved is None
            and new_approval_status is not None
        ):
            self.validated_data["approved_by"] = self.context["request"].user
            self.validated_data["approved_on"] = timezone.now()

            approval_email_required = True

            if new_approval_status is True:
                self.validated_data["ghost"] = False

        obj = super().save()

        # remove small version if large one is gone
        if not obj.image and obj.image_small:
            obj.image_small.delete()

        # if we queued for approval, send a confirmation email
        if not was_active and obj.active:
            obj.send_confirmation_email()

        # if accepted or rejected, send email with reason
        if approval_email_required:
            obj.send_approval_email(change=has_approved_version)
            update_change_reason(
                obj, "{} club".format("Approve" if obj.approved else "Reject")
            )
        elif needs_reapproval:
            update_change_reason(obj, "Edit club through UI (reapproval required)")
        else:
            update_change_reason(obj, "Edit club through UI")

        # Update target year, target school
        # and target major with specific program names
        if (
            self.context["request"].data.get("target_years", None) is not None
            and self.context["request"].data.get("target_years") is not []
        ):
            target_years = self.context["request"].data["target_years"]
            # Iterate over all Year objects, if a given year's ID does not appear
            # in the request then we need to delete it
            for year in Year.objects.all():
                updated = False
                for target_year in target_years:
                    if year.id == target_year["id"]:
                        TargetYear.objects.filter(club=obj).filter(
                            target_years=year
                        ).update_or_create(
                            club=obj,
                            target_years=year,
                            program=target_year.get("program", ""),
                        )
                        updated = True
                        break
                if not updated:
                    TargetYear.objects.filter(club=obj).filter(
                        target_years=year
                    ).delete()

        if (
            self.context["request"].data.get("target_schools", None) is not None
            and self.context["request"].data.get("target_schools") is not []
        ):
            target_schools = self.context["request"].data["target_schools"]
            # Iterate over all School objects, if a given schools's ID does not appear
            # in the request then we need to delete it
            for school in School.objects.all():
                updated = False
                for target_school in target_schools:
                    if school.id == target_school["id"]:
                        TargetSchool.objects.filter(club=obj).filter(
                            target_schools=school
                        ).update_or_create(
                            club=obj,
                            target_schools=school,
                            program=target_school.get("program", ""),
                        )
                        updated = True
                        break
                if not updated:
                    TargetSchool.objects.filter(club=obj).filter(
                        target_schools=school
                    ).delete()

        if (
            self.context["request"].data.get("target_majors", None) is not None
            and self.context["request"].data.get("target_majors") is not []
        ):
            target_majors = self.context["request"].data["target_majors"]
            # Iterate over all Major objects, if a given major's ID does not appear
            # in the request then we need to delete it
            for major in Major.objects.all():
                updated = False
                for target_major in target_majors:
                    if major.id == target_major["id"]:
                        TargetMajor.objects.filter(club=obj).filter(
                            target_majors=major
                        ).update_or_create(
                            club=obj,
                            target_majors=major,
                            program=target_major.get("program", ""),
                        )
                        updated = True
                        break
                if not updated:
                    TargetMajor.objects.filter(club=obj).filter(
                        target_majors=school
                    ).delete()

        if (
            self.context["request"].data.get("student_types", None) is not None
            and self.context["request"].data.get("student_types") is not []
        ):
            target_student_types = self.context["request"].data["student_types"]
            # Iterate over all Student Type objects, if a given student type's ID
            # does not appear in the request then we need to delete it
            for student_type in StudentType.objects.all():
                updated = False
                for target_student_type in target_student_types:
                    if student_type.id == target_student_type["id"]:
                        TargetStudentType.objects.filter(club=obj).filter(
                            target_student_types=student_type
                        ).update_or_create(
                            club=obj,
                            target_student_types=student_type,
                            program=target_student_type.get("program", ""),
                        )
                        updated = True
                        break
                if not updated:
                    TargetStudentType.objects.filter(club=obj).filter(
                        target_student_types=student_type
                    ).delete()

        return obj

    class Meta(ClubListSerializer.Meta):
        fields = ClubListSerializer.Meta.fields + [
            "advisor_set",
            "approved_by",
            "approved_comment",
            "badges",
            "description",
            "events",
            "facebook",
            "github",
            "how_to_get_involved",
            "image",
            "instagram",
            "is_ghost",
            "is_request",
            "linkedin",
            "listserv",
            "members",
            "recruiting_cycle",
            "signature_events",
            "student_types",
            "target_majors",
            "target_schools",
            "target_years",
            "testimonials",
            "twitter",
            "website",
            "youtube",
        ]
        save_related_fields = [
            "tags",
            "badges",
            "target_schools",
            "student_types",
            "target_majors",
            "target_years",
            "advisor_set",
        ]


class FavoriteSerializer(serializers.ModelSerializer):
    """
    Used by users to get a list of clubs that they have favorited.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = ClubListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("club", "person")


class FavoriteWriteSerializer(FavoriteSerializer):
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")

    class Meta(FavoriteSerializer.Meta):
        pass


class UserMembershipSerializer(serializers.ModelSerializer):
    """
    Used for listing which clubs a user is in.
    """

    club = ClubListSerializer(read_only=True)

    def get_role_display(self, obj):
        return obj.get_role_display()

    class Meta:
        model = Membership
        fields = ("club", "role", "title", "active", "public")


class UserUUIDSerializer(serializers.ModelSerializer):
    """
    Used to get the uuid of a user (for ICS Calendar export)
    """

    url = serializers.SerializerMethodField("get_calendar_url")

    def get_calendar_url(self, obj):
        request = self.context["request"]
        scheme = request.scheme
        domain = request.META.get("HTTP_HOST", settings.DEFAULT_DOMAIN)
        return f"{scheme}://{domain}/api/calendar/{str(obj.profile.uuid_secret)}"

    class Meta:
        model = get_user_model()
        fields = ("url",)


class UserSubscribeSerializer(serializers.ModelSerializer):
    """
    Used by users to get a list of clubs that they have subscribed to.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = ClubListSerializer(read_only=True)

    class Meta:
        model = Subscribe
        fields = ("club", "person")


class UserSubscribeWriteSerializer(UserSubscribeSerializer):
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")

    class Meta(UserSubscribeSerializer.Meta):
        pass


class SubscribeSerializer(serializers.ModelSerializer):
    """
    Used by club owners/officers to see who has subscribed to their club.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")
    name = serializers.SerializerMethodField("get_full_name")
    username = serializers.CharField(source="person.username", read_only=True)
    email = serializers.SerializerMethodField("get_email")

    school = SchoolSerializer(many=True, source="person.profile.school", read_only=True)
    major = MajorSerializer(many=True, source="person.profile.major", read_only=True)
    graduation_year = serializers.IntegerField(
        source="person.profile.graduation_year", read_only=True
    )

    def get_email(self, obj):
        if obj.person.email:
            return obj.person.email
        return f"{obj.person.username}@upenn.edu"

    def get_full_name(self, obj):
        return obj.person.get_full_name()

    class Meta:
        model = Subscribe
        fields = (
            "club",
            "created_at",
            "email",
            "graduation_year",
            "major",
            "name",
            "person",
            "school",
            "username",
        )
        validators = [
            validators.UniqueTogetherValidator(
                queryset=Subscribe.objects.all(), fields=["club", "person"]
            )
        ]


class SubscribeBookmarkSerializer(SubscribeSerializer):
    class Meta:
        model = Favorite
        fields = SubscribeSerializer.Meta.fields
        validators = [
            validators.UniqueTogetherValidator(
                queryset=Favorite.objects.all(), fields=["club", "person"]
            )
        ]


class UserClubVisitSerializer(serializers.ModelSerializer):
    """
    Used by users to get a list of clubs that they have visited.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = ClubListSerializer(read_only=True)

    def save(self):
        self.validated_data["ip"] = self.get_ip()
        return super().save()

    def get_ip(self):
        x_forwarded_for = self.context["request"].META.get("HTTP_X_FORWARDED_FOR", None)
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = self.context["request"].META.get("REMOTE_ADDR", None)
        return ip

    class Meta:
        model = ClubVisit
        fields = ("club", "visit_type", "person")


class UserClubVisitWriteSerializer(UserClubVisitSerializer):
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")

    class Meta(UserClubVisitSerializer.Meta):
        pass


class SearchQuerySerializer(serializers.ModelSerializer):
    """
    Used by users to enter search result into backend.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = SearchQuery
        fields = ("person", "query", "created_at")


class MembershipRequestSerializer(serializers.ModelSerializer):
    """
    Used by club owners/officers to see who has requested to join the club.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")
    name = serializers.SerializerMethodField("get_full_name")
    username = serializers.CharField(source="person.username", read_only=True)
    email = serializers.EmailField(source="person.email", read_only=True)

    school = SchoolSerializer(many=True, source="person.profile.school", read_only=True)
    major = MajorSerializer(many=True, source="person.profile.major", read_only=True)
    graduation_year = serializers.IntegerField(
        source="person.profile.graduation_year", read_only=True
    )

    def get_full_name(self, obj):
        return obj.person.get_full_name()

    class Meta:
        model = MembershipRequest
        fields = (
            "club",
            "created_at",
            "email",
            "graduation_year",
            "major",
            "name",
            "person",
            "school",
            "username",
        )
        validators = [
            validators.UniqueTogetherValidator(
                queryset=MembershipRequest.objects.all(), fields=["club", "person"]
            )
        ]


class UserMembershipRequestSerializer(serializers.ModelSerializer):
    """
    Used by the UserSerializer to return the clubs that the user has sent request to.
    """

    person = serializers.HiddenField(default=serializers.CurrentUserDefault())
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")
    club_name = serializers.CharField(source="club.name", read_only=True)

    def create(self, validated_data):
        """
        Send an email when a membership request is created.
        """
        obj = super().create(validated_data)

        obj.send_request(self.context["request"])

        return obj

    class Meta:
        model = MembershipRequest
        fields = ("club", "club_name", "person")


class MinimalUserProfileSerializer(serializers.ModelSerializer):
    """
    A profile serializer used for the list view of all users.
    """

    name = serializers.SerializerMethodField("get_full_name")

    def get_full_name(self, obj):
        return obj.get_full_name()

    class Meta:
        model = get_user_model()
        fields = ["name", "username", "email"]


class UserProfileSerializer(MinimalUserProfileSerializer):
    """
    A profile serializer used to display user information to other users.
    """

    image_url = serializers.SerializerMethodField("get_image_url")
    clubs = serializers.SerializerMethodField("get_clubs")
    graduation_year = serializers.IntegerField(source="profile.graduation_year")
    public = serializers.BooleanField(source="profile.show_profile", read_only=True)
    school = SchoolSerializer(many=True, source="profile.school")
    major = MajorSerializer(many=True, source="profile.major")

    def get_image_url(self, obj):
        if not obj.profile.image:
            return None
        if obj.profile.image.url.startswith("http"):
            return obj.profile.image.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(obj.profile.image.url)
        else:
            return obj.profile.image.url

    def get_clubs(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            user = None
        queryset = Club.objects.filter(membership__person=obj).prefetch_related(
            "tags",
            Prefetch(
                "favorite_set",
                queryset=Favorite.objects.filter(person=user),
                to_attr="user_favorite_set",
            ),
            Prefetch(
                "subscribe_set",
                queryset=Subscribe.objects.filter(person=user),
                to_attr="user_subscribe_set",
            ),
            Prefetch(
                "membership_set",
                queryset=Membership.objects.filter(person=obj),
                to_attr="profile_membership_set",
            ),
        )

        # filter out archived clubs (user and superuser)
        queryset = queryset.filter(archived=False)

        # hide non public memberships if not superuser
        if user is None or not user.has_perm("clubs.manage_club"):
            queryset = queryset.filter(
                membership__person=obj, membership__public=True, approved=True,
            )

        serializer = MembershipClubListSerializer(
            instance=queryset, many=True, context=self.context
        )
        return serializer.data

    class Meta(MinimalUserProfileSerializer.Meta):
        fields = MinimalUserProfileSerializer.Meta.fields + [
            "clubs",
            "graduation_year",
            "image_url",
            "major",
            "public",
            "school",
        ]


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.SerializerMethodField("get_full_name")
    is_superuser = serializers.BooleanField(read_only=True)
    image = serializers.ImageField(
        source="profile.image", write_only=True, allow_null=True
    )
    image_url = serializers.SerializerMethodField("get_image_url")
    has_been_prompted = serializers.BooleanField(source="profile.has_been_prompted")
    share_bookmarks = serializers.BooleanField(source="profile.share_bookmarks")
    show_profile = serializers.BooleanField(source="profile.show_profile")
    graduation_year = serializers.IntegerField(
        source="profile.graduation_year", allow_null=True
    )
    school = SchoolSerializer(many=True, source="profile.school")
    major = MajorSerializer(many=True, source="profile.major")

    def validate_graduation_year(self, value):
        if not value:
            return None
        current_year = timezone.now().year
        min_year = current_year - 2
        max_year = current_year + 10
        if value < min_year:
            raise serializers.ValidationError(
                "Invalid graduation year, must be greater than or equal to {}.".format(
                    min_year
                )
            )
        elif value > max_year:
            raise serializers.ValidationError(
                "Invalid graduation year, must be less than or equal to {}.".format(
                    max_year
                )
            )
        return value

    def get_image_url(self, obj):
        if not obj.profile.image:
            return None
        if obj.profile.image.url.startswith("http"):
            return obj.profile.image.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(obj.profile.image.url)
        else:
            return obj.profile.image.url

    def get_full_name(self, obj):
        return obj.get_full_name()

    def update(self, instance, validated_data):
        if "profile" in validated_data:
            profile_fields = validated_data.pop("profile")
            profile = instance.profile
            valid_fields = {f.name: f for f in Profile._meta.get_fields()}
            for key, value in profile_fields.items():
                if key in valid_fields:
                    field = valid_fields[key]
                    if isinstance(field, models.ManyToManyField):
                        related_objects = getattr(profile, field.get_attname())
                        related_objects.clear()
                        for item in value:
                            related_objects.add(field.related_model.objects.get(**item))
                    else:
                        setattr(profile, key, value)
            profile.save()

        return super().update(instance, validated_data)

    class Meta:
        model = get_user_model()
        fields = [
            "email",
            "graduation_year",
            "has_been_prompted",
            "image",
            "image_url",
            "is_superuser",
            "major",
            "name",
            "school",
            "share_bookmarks",
            "show_profile",
            "username",
        ]


class AssetSerializer(serializers.ModelSerializer):
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    file_url = serializers.SerializerMethodField("get_file_url")
    file = serializers.FileField(write_only=True)
    club = serializers.SlugRelatedField(queryset=Club.objects.all(), slug_field="code")
    name = serializers.CharField(max_length=255, required=True)

    def get_file_url(self, obj):
        if not obj.file:
            return None
        if obj.file.url.startswith("http"):
            return obj.file.url
        elif "request" in self.context:
            return self.context["request"].build_absolute_uri(obj.file.url)
        else:
            return obj.file.url

    # Cannot exceed maximum upload size
    def validate_file(self, data):
        if data.size <= settings.MAX_FILE_SIZE:
            return data
        else:
            max_file_size_in_gb = round(
                (settings.MAX_FILE_SIZE / settings.FILE_SIZE_ONE_GB), 3
            )
            raise serializers.ValidationError(
                "You cannot upload a file that is more than {} GB of space!".format(
                    max_file_size_in_gb
                )
            )

    class Meta:
        model = Asset
        fields = ("id", "file_url", "file", "creator", "club", "name", "created_at")


class AuthenticatedClubSerializer(ClubSerializer):
    """
    Provides additional information about the club to members in the club.
    """

    members = AuthenticatedMembershipSerializer(
        many=True, source="membership_set", read_only=True
    )
    files = AssetSerializer(many=True, source="asset_set", read_only=True)
    fairs = serializers.SerializerMethodField("get_fairs")
    email = serializers.EmailField()
    email_public = serializers.BooleanField(default=True)
    advisor_set = AdvisorSerializer(many=True, required=False)

    class Meta(ClubSerializer.Meta):
        fields = ClubSerializer.Meta.fields + [
            "email_public",
            "fairs",
            "files",
            "ics_import_url",
            "terms",
        ]


class ReportClubField(serializers.Field):
    """
    A custom field used when generating club reports.
    Used to dynamically generate fields based on model objects.

    To add a new dynamically generated report field, perform the following steps:
    - Add the code to generate the field values below.
    - Add the field in the `get_additional_fields` and `get_xlsx_column_name`
      methods in the serializer.

    The field caches the query result for every club and looks up the value from the
    cache when it is requested. If you do not do this, there will be one SQL query
    for each club and report generation will be extremely slow.
    """

    def __init__(self, field, *args, **kwargs):
        self._actual_field = field
        self._cached_values = {}
        self._default_value = "Unknown"

        # handle activities fair case
        fair_match = re.search(r"^custom_fair_(\d+)_(.*)$", self._actual_field)
        if fair_match:
            fair = ClubFair.objects.filter(id=fair_match.group(1)).first()
            if fair:
                suffix = fair_match.group(2)
                if suffix == "reg_time":
                    self._default_value = None
                    reg = fair.clubfairregistration_set.values_list(
                        "club__code", "created_at"
                    )
                    for code, time in reg:
                        self._cached_values[code] = time.astimezone(
                            timezone.get_current_timezone()
                        ).strftime("%b %d, %Y %I:%M %p %Z")
                elif suffix == "email":
                    self._default_value = None
                    reg = fair.clubfairregistration_set.values_list(
                        "club__code", "registrant__email"
                    )
                    self._cached_values = dict(reg)
                elif suffix.startswith("q_"):
                    index = int(suffix.rsplit("_")[-1])
                    reg = fair.clubfairregistration_set.values_list(
                        "club__code", "answers"
                    )
                    self._default_value = None
                    for code, ans in reg:
                        if ans:
                            try:
                                self._cached_values[code] = json.loads(ans)[index]
                            except IndexError:
                                pass
                else:
                    self._default_value = False
                    self._cached_values = {
                        k: True
                        for k in fair.participating_clubs.values_list("code", flat=True)
                    }

        super().__init__(*args, **kwargs)

    def get_attribute(self, instance):
        """
        Return the club code, which we can use to identify which cell row to return.
        """
        return instance.code

    def to_representation(self, value):
        """
        This is called to get the value for a partcular cell, given the club code.
        The entire field object can be though of as a column in the spreadsheet.
        """
        return self._cached_values.get(value, self._default_value)


class ReportClubSerializer(AuthenticatedClubSerializer):
    """
    Provides additional fields that can be used to generate club reports.
    """

    @staticmethod
    def get_additional_fields():
        fields = {}
        now = timezone.now()
        for fair in ClubFair.objects.filter(end_time__gte=now):
            fields[f"Is participating in {fair.name}"] = f"custom_fair_{fair.id}_reg"
            fields[
                f"Registration time for {fair.name}"
            ] = f"custom_fair_{fair.id}_reg_time"
            fields[f"Contact email for {fair.name}"] = f"custom_fair_{fair.id}_email"
            for i, question in enumerate(json.loads(fair.questions)):
                fields[
                    f"[{fair.name}] {question['label']}"
                ] = f"custom_fair_{fair.id}_q_{i}"
        return {"virtual_fair": fields}

    @staticmethod
    def get_xlsx_column_name(key):
        fair_match = re.search(r"^custom_fair_(\d+)_(.*)$", key)
        if fair_match:
            fair = ClubFair.objects.filter(id=fair_match.group(1)).first()
            if fair:
                suffix = fair_match.group(2)
                if suffix == "reg_time":
                    return f"{fair.name} Registration Time"
                elif suffix == "email":
                    return f"{fair.name} Contact Email"
                elif suffix.startswith("q_"):
                    index = int(suffix.rsplit("_")[-1])
                    label = json.loads(fair.questions)[index]["label"]
                    return f"[{fair.name}] {label}"
                return f"Registered for {fair.name}"

    class Meta(AuthenticatedClubSerializer.Meta):
        pass


class NoteTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteTag
        fields = ("id", "name")


class ApplicationQuestionSerializer(ClubRouteMixin, serializers.ModelSerializer):
    class Meta:
        model = ApplicationQuestion
        fields = (
            "id",
            "question_type",
            "prompt",
        )

    def create(self, validated_data):
        validated_data.pop("club")
        application_pk = self.context["view"].kwargs.get("application_pk")
        validated_data["application"] = ClubApplication.objects.filter(
            pk=application_pk
        ).first()
        obj = super().create(validated_data)
        return obj


class ApplicationQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationQuestionResponse
        fields = (
            "text",
        )


class ClubApplicationSerializer(ClubRouteMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField("get_name")

    def get_name(self, obj):
        if obj.name:
            return obj.name
        return f"{obj.club.name} Application"

    def validate(self, data):
        application_start_time = data["application_start_time"]
        application_end_time = data["application_end_time"]
        result_release_time = data["result_release_time"]

        if application_start_time > application_end_time:
            raise serializers.ValidationError(
                "Your application start time must be less than the end time!"
            )

        if application_end_time > result_release_time:
            raise serializers.ValidationError(
                "Your application end time must be less than the result release time!"
            )

        return data

    class Meta:
        model = ClubApplication
        fields = (
            "id",
            "name",
            "application_start_time",
            "application_end_time",
            "result_release_time",
            "external_url",
        )


class WritableClubApplicationSerializer(ClubApplicationSerializer):
    name = serializers.CharField(required=False, allow_blank=True)

    class Meta(ClubApplicationSerializer.Meta):
        pass


class NoteSerializer(ManyToManySaveMixin, serializers.ModelSerializer):
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    creating_club = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field="code"
    )
    subject_club = serializers.SlugRelatedField(
        queryset=Club.objects.all(), slug_field="code"
    )
    title = serializers.CharField(max_length=255, default="Note")
    content = serializers.CharField(required=False)
    note_tags = NoteTagSerializer(many=True, required=False)

    class Meta:
        model = Note
        fields = (
            "id",
            "creator",
            "creating_club",
            "subject_club",
            "title",
            "content",
            "note_tags",
            "creating_club_permission",
            "outside_club_permission",
        )
        save_related_fields = [{"field": "note_tags", "mode": "create"}]


class ClubFairSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField("get_time")

    def get_time(self, obj):
        if obj.time:
            return obj.time
        return "{} to {}".format(
            obj.start_time.strftime("%b %d, %Y"), obj.end_time.strftime("%b %d, %Y")
        )

    class Meta:
        model = ClubFair
        fields = (
            "contact",
            "end_time",
            "id",
            "information",
            "name",
            "organization",
            "questions",
            "registration_end_time",
            "registration_information",
            "registration_start_time",
            "start_time",
            "time",
        )


class WritableClubFairSerializer(ClubFairSerializer):
    time = serializers.CharField(required=False, allow_blank=True)

    class Meta(ClubFairSerializer.Meta):
        pass
