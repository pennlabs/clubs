import collections
import datetime
import traceback

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from clubs.models import Club, ClubApplication, Membership, send_mail_helper


class Command(BaseCommand):
    help = (
        "This script runs each morning to send out relevant notification emails."
        "To avoid duplicate emails, this script should be executed at most once a day."
    )
    web_execute = True

    def handle(self, *args, **kwargs):
        try:
            self.send_approval_queue_reminder()
        except Exception:
            self.stderr.write(traceback.format_exc())

        try:
            self.send_application_notifications()
        except Exception:
            self.stderr.write(traceback.format_exc())

    def send_application_notifications(self):
        """
        Send notifications about application deadlines three days before the deadline,
        for students that have subscribed to those organizations.

        Ignore students that have already graduated and students that are already in
        the club.
        """
        now = timezone.now() + datetime.timedelta(days=3)
        apps = ClubApplication.objects.filter(
            Q(
                club__subscribe__person__profile__graduation_year__gte=now.year
                + (now.month >= 6)
            )
            | Q(club__subscribe__person__profile__graduation_year__isnull=True),
            application_end_time__date=now.date(),
        ).values_list(
            "club__code",
            "club__name",
            "club__subscribe__person__email",
            "club__subscribe__person__pk",
        )

        # compute users already in clubs
        already_in_club = set(
            Membership.objects.filter(
                club__code__in=[x[0] for x in apps], person__pk__in=[x[3] for x in apps]
            ).values_list("club__code", "person__pk")
        )

        # group clubs by user
        emails = collections.defaultdict(list)
        for code, name, email, user_pk in apps:
            if (code, user_pk) not in already_in_club:
                emails[email].append(
                    (name, settings.APPLY_URL.format(domain=settings.DOMAIN, club=code))
                )

        # send out one email per user
        for email, data in emails.items():
            context = {"clubs": data}
            send_mail_helper(
                "application_deadline_reminder",
                f"{len(data)} club(s) have application deadlines approaching",
                [email],
                context,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent application deadline reminder to {len(emails)} user(s)"
            )
        )

    def send_approval_queue_reminder(self):
        """
        Send notification to approval authority for clubs awaiting approval.
        """
        now = timezone.now()
        group_name = "Approvers"

        # only send notifications if it is currently a weekday
        if now.isoweekday() not in range(1, 6):
            return False

        # get users in group to send notification to
        group = Group.objects.filter(name=group_name).first()
        if group is None:
            self.stdout.write(
                self.style.WARNING(
                    f"There is no Django admin group named '{group_name}' in the "
                    "database. Cannot send out approval queue notification emails!"
                )
            )
            return False

        emails = [e for e in group.user_set.all().values_list("email", flat=True) if e]

        if not emails:
            self.stdout.write(
                self.style.WARNING(
                    f"There are no users or no associated emails in the '{group_name}' "
                    "group. No emails will be sent out."
                )
            )
            return False

        # get clubs that need approval
        queued_clubs = Club.objects.filter(
            active=True, approved__isnull=True, archived=False
        )
        if queued_clubs.exists():
            context = {
                "num_clubs": queued_clubs.count(),
                "url": f"https://{settings.DOMAIN}/admin/queue",
                "clubs": list(
                    queued_clubs.order_by("name").values_list("name", flat=True)
                ),
            }
            count = queued_clubs.count()
            send_mail_helper(
                "approval_queue_reminder",
                "{} clubs awaiting review on {}".format(
                    count, settings.BRANDING_SITE_NAME
                ),
                emails,
                context,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Sent approval queue reminder for "
                    f"{count} clubs to {', '.join(emails)}"
                )
            )

        return True
