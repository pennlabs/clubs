import datetime
import os
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import models
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField


def get_asset_file_name(instance, fname):
    return os.path.join("assets", uuid.uuid4().hex, fname)


def get_club_file_name(instance, fname):
    return os.path.join("clubs", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


def get_event_file_name(instance, fname):
    return os.path.join("events", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


def get_user_file_name(instance, fname):
    return os.path.join("users", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


class Club(models.Model):
    """
    Represents a club at the University of Pennsylvania.
    """

    SIZE_SMALL = 1
    SIZE_MEDIUM = 2
    SIZE_LARGE = 3
    SIZE_VERY_LARGE = 4
    SIZE_CHOICES = (
        (SIZE_SMALL, "1-20"),
        (SIZE_MEDIUM, "21-50"),
        (SIZE_LARGE, "51-100"),
        (SIZE_VERY_LARGE, "101+"),
    )
    APPLICATION_REQUIRED_NONE = 1
    APPLICATION_REQUIRED_SOME = 2
    APPLICATION_REQUIRED_ALL = 3
    APPLCIATION_CHOICES = (
        (APPLICATION_REQUIRED_NONE, "No Application Required"),
        (APPLICATION_REQUIRED_SOME, "Application Required For Some Positions"),
        (APPLICATION_REQUIRED_ALL, "Application Required For All Positions"),
    )
    code = models.SlugField(max_length=255, unique=True, db_index=True)
    active = models.BooleanField(default=True)
    approved = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    subtitle = models.CharField(blank=True, max_length=255)
    description = models.TextField(blank=True)
    founded = models.DateField(blank=True, null=True)
    size = models.IntegerField(choices=SIZE_CHOICES, default=SIZE_SMALL)
    email = models.EmailField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    how_to_get_involved = models.TextField(blank=True)
    application_required = models.IntegerField(
        choices=APPLCIATION_CHOICES, default=APPLICATION_REQUIRED_ALL
    )
    accepting_members = models.BooleanField(default=False)
    listserv = models.CharField(blank=True, max_length=255)
    image = models.ImageField(upload_to=get_club_file_name, null=True, blank=True)
    tags = models.ManyToManyField("Tag")
    members = models.ManyToManyField(get_user_model(), through="Membership")
    # Represents which organizations this club is directly under in the organizational structure.
    # For example, SAC is a parent of PAC, which is a parent of TAC-E which is a parent of
    # Penn Players.
    parent_orgs = models.ManyToManyField("Club", related_name="children_orgs", blank=True)
    badges = models.ManyToManyField("Badge", blank=True)

    target_years = models.ManyToManyField("Year", blank=True)
    target_schools = models.ManyToManyField("School", blank=True)
    target_majors = models.ManyToManyField("Major", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Testimonial(models.Model):
    """
    Represents a testimonial for a club.
    """

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="testimonials")
    text = models.TextField()

    def __str__(self):
        return self.text


class Event(models.Model):
    """
    Represents an event hosted by a club.
    """

    code = models.SlugField(max_length=255, unique=True, db_index=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="events")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    image = models.ImageField(upload_to=get_event_file_name, null=True, blank=True)
    description = models.TextField()

    RECRUITMENT = 1
    TYPES = (
        (RECRUITMENT, "Recruitment"),
    )

    type = models.IntegerField(
        choices=TYPES, default=RECRUITMENT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Favorite(models.Model):
    """
    Used when people favorite a club to keep track of which clubs were favorited.
    """

    person = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<Favorite: {} for {}>".format(self.person.username, self.club.pk)

    class Meta:
        unique_together = (("person", "club"),)


class Subscribe(models.Model):
    """
    Used when people subscribe to a club and clubs will be able to see the users' email addresses
    """

    person = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<Subscribe: {} for {}, with email {}>".format(
            self.person.username, self.club.pk, self.person.email
        )

    class Meta:
        unique_together = (("person", "club"),)


class Advisor(models.Model):
    """
    Represents the faculty advisor of a club
    """

    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_email])
    phone = PhoneNumberField(null=False, blank=False, unique=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Note(models.Model):
    """
    Represents a note created by a parent about a
    constituient club
    """

    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    creating_club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="note_by_club")
    subject_club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="note_of_club")
    note_tags = models.ManyToManyField("NoteTag")
    title = models.CharField(max_length=255, default="Note")
    content = models.TextField(blank=True)

    PERMISSION_CREATING_CLUB_OWNER = 0
    PERMISSION_CREATING_CLUB_OFFICER = 10
    PERMISSION_CREATING_CLUB_MEMBER = 20

    PERMISSION_NONE = -1
    PERMISSION_SUBJECT_CLUB_OWNER = 0
    PERMISSION_SUBJECT_CLUB_OFFICER = 10
    PERMISSION_SUBJECT_CLUB_MEMBER = 20
    PERMISSION_PUBLIC = 100

    CREATING_CLUB_PERMISSION_CHOICES = (
        (PERMISSION_CREATING_CLUB_OWNER, "Creating Club Owner"),
        (PERMISSION_CREATING_CLUB_OFFICER, "Creating Club Officers"),
        (PERMISSION_CREATING_CLUB_MEMBER, "Creating Club Members"),
    )

    OUTSIDE_CLUB_PERMISSION_CHOICES = (
        (PERMISSION_NONE, "None"),
        (PERMISSION_SUBJECT_CLUB_OWNER, "Subject Club Owner"),
        (PERMISSION_SUBJECT_CLUB_OFFICER, "Subject Club Officers"),
        (PERMISSION_SUBJECT_CLUB_MEMBER, "Subject Club Members"),
        (PERMISSION_PUBLIC, "Public"),
    )

    creating_club_permission = models.IntegerField(
        choices=CREATING_CLUB_PERMISSION_CHOICES, default=PERMISSION_CREATING_CLUB_MEMBER
    )
    outside_club_permission = models.IntegerField(
        choices=OUTSIDE_CLUB_PERMISSION_CHOICES, default=PERMISSION_SUBJECT_CLUB_MEMBER
    )
    created_at = models.DateTimeField(auto_now_add=True)


class NoteTag(models.Model):
    """
    Represents primary reason for creating a note about a club.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Membership(models.Model):
    """
    Represents the relationship between a member and a club.
    """

    ROLE_OWNER = 0
    ROLE_OFFICER = 10
    ROLE_MEMBER = 20
    ROLE_CHOICES = ((ROLE_OWNER, "Owner"), (ROLE_OFFICER, "Officer"), (ROLE_MEMBER, "Member"))

    active = models.BooleanField(default=True)
    public = models.BooleanField(default=True)

    person = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Member")
    role = models.IntegerField(choices=ROLE_CHOICES, default=ROLE_MEMBER)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<Membership: {} in {} ({})>".format(
            self.person.username, self.club.code, self.get_role_display()
        )

    class Meta:
        unique_together = (("club", "person"),)


def get_token():
    """
    Generate a secure token for membership invites.
    Is a custom function because Django can't serialize lambdas.
    """
    return get_random_string(length=128)


def get_invite_id():
    """
    Generate a secure ID for membership invites.
    """
    return get_random_string(length=8)


class MembershipInvite(models.Model):
    """
    Represents an invitation to a club.
    """

    id = models.CharField(max_length=8, primary_key=True, default=get_invite_id)
    active = models.BooleanField(default=True)
    auto = models.BooleanField(default=False)
    creator = models.ForeignKey(get_user_model(), null=True, on_delete=models.SET_NULL)

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=128, default=get_token)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=255, default="Member")
    role = models.IntegerField(default=Membership.ROLE_MEMBER)

    def __str__(self):
        return "<MembershipInvite: {} for {}>".format(self.club.code, self.email)

    def claim(self, user):
        """
        Claim an invitation using a user.
        """
        self.active = False
        self.save()

        obj, _ = Membership.objects.get_or_create(
            person=user, club=self.club, defaults={"role": self.role, "title": self.title}
        )

        return obj

    def send_mail(self, request=None):
        """
        Send the email associated with this invitation to the user.
        """
        # make the beta/testing sites work
        domain = settings.DEFAULT_DOMAIN
        if request is not None:
            referer = request.META.get("HTTP_REFERER")
            if referer:
                host = urlparse(referer).netloc
                if host and host.endswith(domain):
                    domain = host

        context = {
            "token": self.token,
            "name": self.club.name,
            "id": self.id,
            "club_id": self.club.code,
            "sender": request.user,
            "role": self.role,
            "title": self.title,
            "url": settings.INVITE_URL.format(
                domain=domain, id=self.id, token=self.token, club=self.club.code
            ),
        }
        text_content = render_to_string("emails/invite.txt", context)
        html_content = render_to_string("emails/invite.html", context)

        msg = EmailMultiAlternatives(
            "Invitation to {}".format(self.club.name),
            text_content,
            settings.FROM_EMAIL,
            [self.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

    def send_owner_invite(self, request=None):
        """
        Send the initial email invitation to owner(s) of the club.
        """
        if self.role > Membership.ROLE_OWNER:
            raise ValueError(
                "This invite should grant owner permissions if sending out the owner email!"
            )

        domain = settings.DEFAULT_DOMAIN
        if request is not None:
            referer = request.META.get("HTTP_REFERER")
            if referer:
                host = urlparse(referer).netloc
                if host and host.endswith(domain):
                    domain = host

        context = {
            "name": self.club.name,
            "view_url": settings.VIEW_URL.format(domain=domain, club=self.club.code),
            "url": settings.INVITE_URL.format(
                domain=domain, id=self.id, token=self.token, club=self.club.code
            ),
        }
        text_content = render_to_string("emails/owner.txt", context)
        html_content = render_to_string("emails/owner.html", context)

        msg = EmailMultiAlternatives(
            "Welcome to Penn Clubs!", text_content, settings.FROM_EMAIL, [self.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)


class Tag(models.Model):
    """
    Represents general categories that clubs fit into.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Badge(models.Model):
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # The color of the badge to be displayed on the frontend.
    color = models.CharField(max_length=16, default="")

    # The organization that this badge represents (If this is the "SAC Funded" badge,
    # then this would link to SAC)
    org = models.ForeignKey(Club, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.label


class Asset(models.Model):
    """
    Represents an uploaded file object.
    """

    creator = models.ForeignKey(get_user_model(), null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to=get_asset_file_name)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Year(models.Model):
    """
    Represents a graduation class (ex: Freshman, Sophomore, Junior, Senior, Graduate Student).
    """

    name = models.TextField()

    @property
    def year(self):
        """
        Convert from graduation class name to graduation year.
        """
        now = datetime.datetime.now()
        year = now.year
        if now.month > 6:
            year += 1
        offset = {"freshman": 3, "sophomore": 2, "junior": 1, "senior": 0}.get(self.name.lower(), 0)
        return year + offset

    def __str__(self):
        return self.name


class School(models.Model):
    """
    Represents a school (ex: Engineering, Wharton, etc).
    """

    name = models.TextField()

    def __str__(self):
        return self.name


class Major(models.Model):
    """
    Represents a major (ex: Computer Science, BSE).
    """

    name = models.TextField()

    def __str__(self):
        return self.name


class Profile(models.Model):
    """
    Additional information attached to a user account.
    """

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, primary_key=True)
    image = models.ImageField(upload_to=get_user_file_name, null=True, blank=True)

    has_been_prompted = models.BooleanField(default=False)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    school = models.ManyToManyField(School, blank=True)
    major = models.ManyToManyField(Major, blank=True)

    def __str__(self):
        return self.user.username


@receiver(models.signals.post_delete, sender=Asset)
def asset_delete_cleanup(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(models.signals.post_delete, sender=Club)
def club_delete_cleanup(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(models.signals.post_delete, sender=Event)
def event_delete_cleanup(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(models.signals.post_save, sender=get_user_model())
def user_create(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(models.signals.post_delete, sender=Profile)
def profile_delete_cleanup(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(models.signals.post_save, sender=Club)
def club_modify_handler(sender, instance, **kwargs):
    """
    Delete the club list cache when a club is modified.
    """
    cache.delete(settings.CLUB_LIST_CACHE_KEY)
