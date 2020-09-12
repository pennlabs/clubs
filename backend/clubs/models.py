import datetime
import os
import uuid

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import models
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords

from clubs.utils import get_django_minified_image, get_domain, html_to_text


def send_mail_helper(name, subject, emails, context):
    """
    A helper to send out an email given the template name, subject, to emails, and context.
    """
    if not all(isinstance(email, str) for email in emails):
        raise ValueError("The to email argument must be a list of strings!")

    html_content = render_to_string("emails/{}.html".format(name), context)
    text_content = html_to_text(html_content)

    msg = EmailMultiAlternatives(subject, text_content, settings.FROM_EMAIL, list(set(emails)))

    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


def get_asset_file_name(instance, fname):
    return os.path.join("assets", uuid.uuid4().hex, fname)


def get_club_file_name(instance, fname):
    return os.path.join("clubs", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


def get_club_small_file_name(instance, fname):
    return os.path.join("clubs_small", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


def get_event_file_name(instance, fname):
    return os.path.join("events", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


def get_user_file_name(instance, fname):
    return os.path.join("users", "{}.{}".format(uuid.uuid4().hex, fname.rsplit(".", 1)[-1]))


class Report(models.Model):
    """
    Represents a report generated by the reporting feature.
    """

    name = models.TextField()
    creator = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    parameters = models.TextField(blank=True)
    public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        permissions = [
            ("generate_reports", "Can generate reports"),
        ]


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
    APPLICATION_CHOICES = (
        (APPLICATION_REQUIRED_NONE, "No Application Required"),
        (APPLICATION_REQUIRED_SOME, "Application Required For Some Positions"),
        (APPLICATION_REQUIRED_ALL, "Application Required For All Positions"),
    )

    approved = models.BooleanField(null=True, default=None)
    approved_by = models.ForeignKey(
        get_user_model(),
        null=True,
        on_delete=models.SET_NULL,
        related_name="approved_clubs",
        blank=True,
    )
    approved_comment = models.TextField(null=True, blank=True)
    approved_on = models.DateTimeField(null=True, blank=True)

    # indicates whether or not the club has expressed interest in this year's SAC fair
    fair = models.BooleanField(default=False)
    fair_on = models.DateTimeField(null=True, blank=True)

    code = models.SlugField(max_length=255, unique=True, db_index=True)
    active = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    subtitle = models.CharField(blank=True, max_length=255)
    description = models.TextField(blank=True)
    founded = models.DateField(blank=True, null=True)
    size = models.IntegerField(choices=SIZE_CHOICES, default=SIZE_SMALL)
    email = models.EmailField(blank=True, null=True)
    email_public = models.BooleanField(default=True)
    facebook = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    how_to_get_involved = models.TextField(blank=True)
    application_required = models.IntegerField(
        choices=APPLICATION_CHOICES, default=APPLICATION_REQUIRED_ALL
    )
    accepting_members = models.BooleanField(default=False)
    listserv = models.CharField(blank=True, max_length=255)
    image = models.ImageField(upload_to=get_club_file_name, null=True, blank=True)
    image_small = models.ImageField(upload_to=get_club_small_file_name, null=True, blank=True)
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

    rank = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ghost = models.BooleanField(default=False)
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.name

    def create_thumbnail(self, request=None):
        if not self.image:
            return False
        image_url = self.image.url
        if not image_url.startswith("http"):
            if request is not None:
                image_url = request.build_absolute_uri(image_url)
            else:
                return False
        try:
            self.image_small = get_django_minified_image(image_url, height=200)
            self.skip_history_when_saving = True
            self.save(update_fields=["image_small"])
        except requests.exceptions.RequestException:
            return False
        return True

    def send_virtual_fair_email(self, request=None, email="setup"):
        """
        Send the virtual fair email to all club officers
        about setting up their club for the virtual fair.
        """
        domain = get_domain(request)

        now = timezone.now()
        event = (
            self.events.filter(start_time__gte=now, type=Event.FAIR).order_by("start_time").first()
        )

        prefix = (
            "ACTION REQUIRED"
            if event is None or not event.url or "zoom.us" not in event.url
            else "REMINDER"
        )
        if email in {"urgent", "zoom"}:
            prefix = "URGENT"

        emails = self.get_officer_emails()
        subj = "SAC Fair Setup and Information"
        if email in {"urgent", "zoom"}:
            subj = "SAC Fair Setup"
        elif email in {"post"}:
            subj = "Post SAC Fair Information"
            prefix = "REMINDER"

        context = {
            "name": self.name,
            "prefix": prefix,
            "guide_url": f"https://{domain}/sacfairguide",
            "zoom_url": f"https://{domain}/zoom",
            "fair_url": f"https://{domain}/fair",
            "subscriptions_url": f"https://{domain}/club/{self.code}/edit#recruitment",
            "num_subscriptions": self.subscribe_set.count(),
        }

        if emails:
            send_mail_helper(
                name={
                    "setup": "fair_info",
                    "urgent": "fair_reminder",
                    "zoom": "zoom_reminder",
                    "post": "fair_feedback_officers",
                }[email],
                subject=f"[{prefix}] {subj}",
                emails=emails,
                context=context,
            )

    def send_renewal_email(self, request=None):
        """
        Send an email notifying all club officers about renewing their approval with the
        Office of Student Affairs and registering for the SAC fair.
        """
        domain = get_domain(request)

        context = {
            "name": self.name,
            "url": settings.RENEWAL_URL.format(domain=domain, club=self.code),
        }

        emails = self.get_officer_emails()

        if emails:
            send_mail_helper(
                name="renew",
                subject="[ACTION REQUIRED] Renew {} and SAC Fair Registration".format(self.name),
                emails=emails,
                context=context,
            )

    def send_renewal_reminder_email(self, request=None):
        """
        Send a reminder email to clubs about renewing their approval with the Office of Student
        Affairs and registering for the SAC fair.
        """
        domain = get_domain(request)

        context = {
            "name": self.name,
            "url": settings.RENEWAL_URL.format(domain=domain, club=self.code),
            "year": timezone.now().year,
        }

        emails = self.get_officer_emails()

        if emails:
            send_mail_helper(
                name="renewal_reminder",
                subject="[ACTION REQUIRED] Renew {} and SAC Fair Registration".format(self.name),
                emails=emails,
                context=context,
            )

    def get_officer_emails(self):
        """
        Return a list of club officer emails, including the contact email for the club.
        """
        emails = []

        # add club contact email if valid
        try:
            validate_email(self.email)
            emails.append(self.email)
        except ValidationError:
            pass

        # add email for all officers and above
        for user in self.membership_set.filter(role__lte=Membership.ROLE_OFFICER):
            emails.append(user.person.email)

        # remove empty emails
        emails = [email.strip() for email in emails]
        emails = [email for email in emails if email]

        # remove duplicate emails
        emails = list(sorted(set(emails)))

        return emails

    def send_approval_email(self, request=None, change=False):
        domain = get_domain(request)

        context = {
            "name": self.name,
            "year": datetime.datetime.now().year,
            "approved": self.approved,
            "approved_comment": self.approved_comment,
            "view_url": settings.VIEW_URL.format(domain=domain, club=self.code),
            "edit_url": settings.EDIT_URL.format(domain=domain, club=self.code),
            "change": change,
        }

        emails = self.get_officer_emails()

        if emails:
            send_mail_helper(
                name="approval_status",
                subject="{}{} {} on Penn Clubs".format(
                    "Changes to " if change else "",
                    self.name,
                    "accepted" if self.approved else "not approved",
                ),
                emails=emails,
                context=context,
            )

    class Meta:
        ordering = ["name"]
        permissions = [
            ("approve_club", "Can approve pending clubs"),
            ("see_pending_clubs", "View pending clubs that are not one's own"),
            ("see_fair_status", "See whether or not a club has registered for the SAC fair",),
        ]


class QuestionAnswer(models.Model):
    """
    Represents a question asked by a prospective member to a club
    and the club's corresponding answer.
    """

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="questions")
    author = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, related_name="questions"
    )
    responder = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, related_name="answers"
    )

    approved = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)

    question = models.TextField()
    answer = models.TextField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}: {}".format(self.club.name, self.question)

    def send_question_mail(self, request=None):
        domain = get_domain(request)

        owner_emails = list(
            self.club.membership_set.filter(role__lte=Membership.ROLE_OFFICER).values_list(
                "person__email", flat=True
            )
        )

        context = {
            "name": self.club.name,
            "question": self.question,
            "url": settings.QUESTION_URL.format(domain=domain, club=self.club.code),
        }

        if owner_emails:
            send_mail_helper(
                name="question",
                subject="Question for {}".format(self.club.name),
                emails=owner_emails,
                context=context,
            )


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

    code = models.SlugField(max_length=255, db_index=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="events")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    image = models.ImageField(upload_to=get_event_file_name, null=True, blank=True)
    description = models.TextField(blank=True)

    RECRUITMENT = 1
    GBM = 2
    SPEAKER = 3
    OTHER = 0
    FAIR = 4
    TYPES = (
        (RECRUITMENT, "Recruitment"),
        (GBM, "GBM"),
        (SPEAKER, "Speaker"),
        (OTHER, "Other"),
        (FAIR, "Activities Fair"),
    )

    type = models.IntegerField(choices=TYPES, default=RECRUITMENT)

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
        return "<Favorite: {} for {}>".format(self.person.username, self.club.code)

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
            self.person.username, self.club.code, self.person.email
        )

    class Meta:
        unique_together = (("person", "club"),)


class ClubVisit(models.Model):
    """
    Stores user visits to club pages to be used later in analytics
    """

    person = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<Visit: {} visited {}>".format(self.person.username, self.club.code)


class MembershipRequest(models.Model):
    """
    Used when users are not in the club but request membership from the owner
    """

    person = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)

    withdrew = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "<MembershipRequest: {} for {}, with email {}>".format(
            self.person.username, self.club.code, self.person.email
        )

    def send_request(self, request=None):
        domain = get_domain(request)

        context = {
            "club_name": self.club.name,
            "edit_url": "{}#member".format(
                settings.EDIT_URL.format(domain=domain, club=self.club.code)
            ),
            "full_name": self.person.get_full_name(),
        }

        owner_emails = list(
            self.club.membership_set.filter(role__lte=Membership.ROLE_OFFICER).values_list(
                "person__email", flat=True
            )
        )

        send_mail_helper(
            name="request",
            subject="Membership Request from {} for {}".format(
                self.person.get_full_name(), self.club.name
            ),
            emails=owner_emails,
            context=context,
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
        choices=CREATING_CLUB_PERMISSION_CHOICES, default=PERMISSION_CREATING_CLUB_MEMBER,
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
    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_OFFICER, "Officer"),
        (ROLE_MEMBER, "Member"),
    )

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
            person=user, club=self.club, defaults={"role": self.role, "title": self.title},
        )

        return obj

    def send_mail(self, request=None):
        """
        Send the email associated with this invitation to the user.
        """
        domain = get_domain(request)

        context = {
            "token": self.token,
            "name": self.club.name,
            "id": self.id,
            "club_id": self.club.code,
            "sender": request.user
            if request is not None
            else {"username": "Penn Clubs", "email": "contact@pennclubs.com"},
            "role": self.role,
            "title": self.title,
            "url": settings.INVITE_URL.format(
                domain=domain, id=self.id, token=self.token, club=self.club.code
            ),
        }

        send_mail_helper(
            name="invite",
            subject="Invitation to {}".format(self.club.name),
            emails=[self.email],
            context=context,
        )

    def send_owner_invite(self, request=None):
        """
        Send the initial email invitation to owner(s) of the club.
        """
        if self.role > Membership.ROLE_OWNER:
            raise ValueError(
                "This invite should grant owner permissions if sending out the owner email!"
            )

        domain = get_domain(request)

        context = {
            "name": self.club.name,
            "view_url": settings.VIEW_URL.format(domain=domain, club=self.club.code),
            "url": settings.INVITE_URL.format(
                domain=domain, id=self.id, token=self.token, club=self.club.code
            ),
        }

        send_mail_helper(
            name="owner", subject="Welcome to Penn Clubs!", emails=[self.email], context=context,
        )


class Tag(models.Model):
    """
    Represents general categories that clubs fit into.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Badge(models.Model):
    label = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
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
    share_bookmarks = models.BooleanField(default=False)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    school = models.ManyToManyField(School, blank=True)
    major = models.ManyToManyField(Major, blank=True)

    def __str__(self):
        return self.user.username


@receiver(models.signals.pre_delete, sender=Asset)
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
