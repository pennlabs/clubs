import datetime
import io
import json
import os
from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from clubs.models import (
    Badge,
    Club,
    Event,
    Favorite,
    Membership,
    MembershipInvite,
    QuestionAnswer,
    School,
    Tag,
    Testimonial,
)
from clubs.views import DEFAULT_PAGE_SIZE


class SearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Club.objects.bulk_create(
            [
                Club(code=f"club-{i}", name=f"Club #{i}", active=True, approved=True)
                for i in range(0, 100)
            ]
        )

    def setUp(self):
        self.client = Client()

    def test_random_listing(self):
        self.perform_random_fetch(DEFAULT_PAGE_SIZE)

    def test_random_listing_odd_page(self):
        self.perform_random_fetch(17)

    def perform_random_fetch(self, page_size):
        # fetch clubs using random ordering
        resp = self.client.get(
            reverse("clubs-list"),
            {"ordering": "random", "page": "1", "page_size": str(page_size)},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)
        data = resp.json()

        clubs = []
        pages = []

        while data["next"] is not None:
            self.assertLessEqual(len(data["results"]), page_size)
            self.assertGreater(len(data["results"]), 0, pages)

            clubs.extend(data["results"])

            pages.append(sorted([club["code"] for club in data["results"]]))

            resp = self.client.get(data["next"], content_type="application/json")
            self.assertIn(resp.status_code, [200, 201], resp.content)
            data = resp.json()

        clubs = sorted([club["code"] for club in clubs])

        # calculate the base truth
        truth = sorted(Club.objects.values_list("code", flat=True))
        truth_counter = Counter(truth)
        clubs_counter = Counter(clubs)
        missing = truth_counter - clubs_counter
        extra = clubs_counter - truth_counter

        # ensure all clubs existing in the complete listing
        self.assertEqual(
            clubs,
            truth,
            "\nMissing from results: {}\nExtra in results: {}\n\n{}".format(
                list(missing.elements()),
                list(sorted(extra.elements())),
                "\n".join(str(page) for page in pages),
            ),
        )


class ClubTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = get_user_model().objects.create_user(
            "bfranklin", "bfranklin@seas.upenn.edu", "test"
        )
        cls.user1.first_name = "Benjamin"
        cls.user1.last_name = "Franklin"
        cls.user1.save()

        cls.user2 = get_user_model().objects.create_user(
            "tjefferson", "tjefferson@seas.upenn.edu", "test"
        )
        cls.user2.first_name = "Thomas"
        cls.user2.last_name = "Jefferson"
        cls.user2.save()

        cls.user3 = get_user_model().objects.create_user(
            "gwashington", "gwashington@wharton.upenn.edu", "test"
        )
        cls.user3.first_name = "George"
        cls.user3.last_name = "Washington"
        cls.user3.save()

        cls.user4 = get_user_model().objects.create_user(
            "barnold", "barnold@wharton.upenn.edu", "test"
        )
        cls.user4.first_name = "Benedict"
        cls.user4.last_name = "Arnold"
        cls.user4.save()

        cls.user5 = get_user_model().objects.create_user("jadams", "jadams@sas.upenn.edu", "test")
        cls.user5.first_name = "John"
        cls.user5.last_name = "Adams"
        cls.user5.is_staff = True
        cls.user5.is_superuser = True
        cls.user5.save()

        Tag.objects.create(name="Graduate")
        Tag.objects.create(name="Undergraduate")

    def setUp(self):
        self.client = Client()

        self.club1 = Club.objects.create(
            code="test-club", name="Test Club", approved=True, email="example@example.com"
        )

        self.event1 = Event.objects.create(
            code="test-event",
            club=self.club1,
            name="Test Event",
            start_time=timezone.now() + timezone.timedelta(days=2),
            end_time=timezone.now() + timezone.timedelta(days=3),
        )

        self.question1 = QuestionAnswer.objects.create(
            club=self.club1,
            question="What is your name?",
            answer=None,
            approved=False,
            author=self.user1,
        )

        self.question2 = QuestionAnswer.objects.create(
            club=self.club1,
            question="What is your favorite color?",
            answer="Blue",
            approved=True,
            author=self.user2,
            responder=self.user1,
        )

    def test_club_upload(self):
        """
        Test uploading a club logo.
        """
        self.client.login(username=self.user5.username, password="test")

        # empty image throws an error
        resp = self.client.post(reverse("clubs-upload", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # successful image upload
        resp = self.client.post(
            reverse("clubs-upload", args=(self.club1.code,)), {"file": io.BytesIO(b"")}
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure image url is set
        resp = self.client.get(reverse("clubs-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 204], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data["image_url"])

        # ensure cleanup doesn't throw error
        self.club1.delete()

    def test_club_qr(self):
        """
        Test generating a club fair QR code image.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.get(reverse("clubs-qr", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 201], resp.content)

    def test_club_subscription(self):
        """
        Test retrieving the list of club subscribers.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.get(reverse("clubs-subscription", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 201], resp.content)

    def test_clubs_notes_about(self):
        """
        Test retrieving the list of notes about a club.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.get(reverse("clubs-notes-about", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 201], resp.content)

    def test_event_upload(self):
        """
        Test uploading an event image.
        """
        self.client.login(username=self.user5.username, password="test")

        # successful image upload
        resp = self.client.post(
            reverse("club-events-upload", args=(self.club1.code, self.event1.id)),
            {"file": io.BytesIO(b"")},
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure cleanup doesn't throw error
        self.event1.delete()

    def test_user_views(self):
        """
        Test retrieving and updating user settings.
        """
        self.client.login(username=self.user5.username, password="test")

        # add a membership
        Membership.objects.create(person=self.user5, club=self.club1)

        # add a favorite
        Favorite.objects.create(person=self.user5, club=self.club1)

        # add some schools
        School.objects.create(name="Wharton")
        School.objects.create(name="Engineering")

        # retrieve user
        resp = self.client.get(reverse("users-detail"))
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # update user
        resp = self.client.patch(reverse("users-detail"))
        self.assertIn(resp.status_code, [200, 201], resp.content)
        data = json.loads(resp.content.decode("utf-8"))

        for field in ["username", "email"]:
            self.assertIn(field, data)

        # update user with fields
        # user field should not be updated
        resp = self.client.patch(
            reverse("users-detail"),
            {
                "user": self.user1.id,
                "graduation_year": 3000,
                "school": [{"name": "Wharton"}, {"name": "Engineering"}],
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure fields have been updated
        resp = self.client.get(reverse("users-detail"))
        self.assertIn(resp.status_code, [200, 201], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data["graduation_year"], 3000)
        self.assertEqual(set([s["name"] for s in data["school"]]), {"Wharton", "Engineering"})

    def test_superuser_views(self):
        """
        Test performing club/membership operations as a superuser.
        """
        self.client.login(username=self.user5.username, password="test")

        # create club as superuser
        resp = self.client.post(
            reverse("clubs-list"),
            {"name": "Penn Labs", "description": "We code stuff.", "tags": [{"name": "Graduate"}]},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # add member as superuser
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("club-members-list", args=("penn-labs",)),
            {"person": self.user2.pk, "role": Membership.ROLE_OFFICER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # remove member as superuser
        resp = self.client.delete(
            reverse("club-members-detail", args=("penn-labs", self.user2.username))
        )
        self.assertIn(resp.status_code, [200, 204], resp.content)

        # delete club as superuser
        resp = self.client.delete(reverse("clubs-detail", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_subscribe_views(self):
        """
        Test listing/adding/deleting subscriptions.
        """
        self.client.login(username=self.user1.username, password="test")

        # add subscription
        resp = self.client.post(reverse("subscribes-list"), {"club": self.club1.code})
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # attempt to add existing subscription
        resp = self.client.post(reverse("subscribes-list"), {"club": self.club1.code})
        self.assertIn(resp.status_code, [400], resp.content)

        # list subscriptions
        resp = self.client.get(reverse("subscribes-list"))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data)

        # delete subscription
        resp = self.client.delete(reverse("subscribes-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_favorite_views(self):
        """
        Test listing/adding/deleting favorites.
        """
        self.client.login(username=self.user1.username, password="test")

        # add favorite
        resp = self.client.post(reverse("favorites-list"), {"club": self.club1.code})
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # attempt to add existing favorite
        resp = self.client.post(reverse("favorites-list"), {"club": self.club1.code})
        self.assertIn(resp.status_code, [400], resp.content)

        # list favorites
        resp = self.client.get(reverse("favorites-list"))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data)

        # other people shouldn't see your favorites
        self.client.login(username=self.user4.username, password="test")
        resp = self.client.get(reverse("favorites-list"))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertFalse(data)

        # delete favorite
        self.client.login(username=self.user1.username, password="test")
        resp = self.client.delete(reverse("favorites-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_event_list(self):
        """
        Test listing club events.
        """
        self.client.login(username=self.user5.username, password="test")

        e2 = Event.objects.create(
            code="test-event-2",
            club=self.club1,
            name="Past Test Event 2",
            start_time=timezone.now() - timezone.timedelta(days=3),
            end_time=timezone.now() - timezone.timedelta(days=2),
        )
        e3 = Event.objects.create(
            code="test-event-3",
            club=self.club1,
            name="Present Test Event 3",
            start_time=timezone.now() - timezone.timedelta(days=3),
            end_time=timezone.now() + timezone.timedelta(days=2),
        )

        # list events without a club to namespace.
        resp = self.client.get(reverse("events-list"), content_type="application/json",)
        self.assertIn(resp.status_code, [200], resp.content)
        self.assertEquals(2, len(resp.data), resp.data)

        # list events currently happening.
        resp = self.client.get(
            reverse("club-events-live", args=(self.club1.code,)), content_type="application/json",
        )
        self.assertIn(resp.status_code, [200], resp.content)
        self.assertEquals(1, len(resp.data), resp.data)
        self.assertEquals(e3.id, resp.data[0]["id"], resp.data)

        # upcoming events.
        resp = self.client.get(
            reverse("club-events-upcoming", args=(self.club1.code,)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200], resp.content)
        self.assertEquals(1, len(resp.data), resp.data)
        self.assertEquals(self.event1.id, resp.data[0]["id"], resp.data)

        # events that have ended.
        resp = self.client.get(
            reverse("club-events-ended", args=(self.club1.code,)), content_type="application/json",
        )
        self.assertIn(resp.status_code, [200], resp.content)
        self.assertEquals(1, len(resp.data), resp.data)
        self.assertEquals(e2.id, resp.data[0]["id"], resp.data)

    def test_event_create_delete(self):
        """
        Test creating and deleting a club event.
        """
        self.client.login(username=self.user5.username, password="test")

        start_date = datetime.datetime.now() - datetime.timedelta(days=3)
        end_date = start_date + datetime.timedelta(hours=2)

        # add event
        resp = self.client.post(
            reverse("club-events-list", args=(self.club1.code,)),
            {
                "name": "Interest Meeting",
                "description": "Interest Meeting on Friday!",
                "location": "JMHH G06",
                "start_time": start_date.isoformat(),
                "end_time": end_date.isoformat(),
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)
        id = json.loads(resp.content)["id"]

        # ensure event exists
        self.assertEqual(Event.objects.filter(name="Interest Meeting").count(), 1)
        self.assertEqual(Event.objects.get(name="Interest Meeting").creator, self.user5)

        # delete event
        resp = self.client.delete(reverse("club-events-detail", args=(self.club1.code, id)))
        self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_testimonials(self):
        """
        Test creating, listing, and deleting testimonials.
        """
        self.client.login(username=self.user5.username, password="test")

        # add some testimonials
        for i in range(3):
            resp = self.client.post(
                reverse("club-testimonials-list", args=(self.club1.code,)),
                {"text": f"This is testimonial #{i}!"},
                content_type="application/json",
            )
            self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure testimonials exist
        testimonials = Testimonial.objects.filter(club__code=self.club1.code)
        self.assertEqual(testimonials.count(), 3)

        # list testimonials
        resp = self.client.get(reverse("club-testimonials-list", args=(self.club1.code,)))
        self.assertEqual(resp.status_code, 200, resp.content)

        # delete testimonials
        for testimonial in testimonials:
            resp = self.client.delete(
                reverse("club-testimonials-detail", args=(self.club1.code, testimonial.id))
            )
            self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_member_views(self):
        """
        Test listing, adding, and removing members.
        """
        self.client.login(username=self.user5.username, password="test")

        # create club
        resp = self.client.post(
            reverse("clubs-list"),
            {"name": "Penn Labs", "description": "We code stuff.", "tags": [{"name": "Graduate"}]},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # list members
        resp = self.client.get(reverse("club-members-list", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data[0]["name"], self.user5.get_full_name())

        # add member should fail with insufficient permissions
        self.client.logout()

        resp = self.client.post(
            reverse("club-members-list", args=("penn-labs",)),
            {"person": self.user2.pk, "role": Membership.ROLE_OWNER},
            content_type="application/json",
        )

        self.assertIn(resp.status_code, [400, 403], resp.content)

        # add member
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("club-members-list", args=("penn-labs",)),
            {"person": self.user2.pk, "role": Membership.ROLE_OFFICER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        resp = self.client.post(
            reverse("club-members-list", args=("penn-labs",)),
            {"person": self.user3.pk, "role": Membership.ROLE_MEMBER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        self.assertEqual(Club.objects.get(code="penn-labs").members.count(), 3)
        self.assertEqual(
            Membership.objects.get(person=self.user2, club__code="penn-labs").role,
            Membership.ROLE_OFFICER,
        )

        # list member
        resp = self.client.get(reverse("club-members-list", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        for item in data:
            self.assertIn("name", item)
            self.assertIn("email", item)
            self.assertIn("role", item)

        # list member as outsider
        self.client.logout()
        resp = self.client.get(reverse("club-members-list", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        for item in data:
            self.assertNotIn("email", item)

        # delete member should fail with insufficient permissions
        self.client.login(username=self.user2.username, password="test")

        resp = self.client.delete(
            reverse("club-members-detail", args=("penn-labs", self.user5.username)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # delete member should fail for people not in club
        self.client.login(username=self.user4.username, password="test")
        resp = self.client.delete(
            reverse("club-members-detail", args=("penn-labs", self.user5.username)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # cannot add self to a club that you're not in
        resp = self.client.post(
            reverse("club-members-list", args=("penn-labs",)),
            {"person": self.user4.pk, "role": Membership.ROLE_MEMBER},
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # modify self to higher role should fail with insufficient permissions
        self.client.login(username=self.user2.username, password="test")
        resp = self.client.patch(
            reverse("club-members-detail", args=("penn-labs", self.user2.username)),
            {"role": Membership.ROLE_OWNER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # promote member
        resp = self.client.patch(
            reverse("club-members-detail", args=("penn-labs", self.user3.username)),
            {"title": "Treasurer", "role": Membership.ROLE_OFFICER},
            content_type="application/json",
        )

        self.assertEqual(
            Membership.objects.get(person=self.user3, club__code="penn-labs").title, "Treasurer",
        )

        # delete member
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.delete(
            reverse("club-members-detail", args=("penn-labs", self.user2.username)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 204], resp.content)

        # ensure cannot demote self if only owner and not superuser
        self.user5.is_superuser = False
        self.user5.save()

        resp = self.client.patch(
            reverse("club-members-detail", args=("penn-labs", self.user5.username)),
            {"role": Membership.ROLE_OFFICER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

        # ensure cannot delete self if only owner
        resp = self.client.delete(
            reverse("club-members-detail", args=("penn-labs", self.user5.username)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_membership_auth(self):
        Membership.objects.create(club=self.club1, person=self.user1)
        self.client.login(username=self.user1.username, password="test")
        bad_tries = [{"title": "Supreme Leader"}, {"role": Membership.ROLE_OFFICER}]
        for bad in bad_tries:
            resp = self.client.patch(
                reverse("club-members-detail", args=(self.club1.code, self.user1.username)),
                bad,
                content_type="application/json",
            )
            self.assertIn(resp.status_code, [400, 403], resp.content)

        good_tries = [
            {"active": True},
            {"active": False},
        ]
        for good in good_tries:
            resp = self.client.patch(
                reverse("club-members-detail", args=(self.club1.code, self.user1.username)),
                good,
                content_type="application/json",
            )
            self.assertIn(resp.status_code, [200, 201], resp.content)

        resp = self.client.delete(
            reverse("club-members-detail", args=(self.club1.code, self.user1.username))
        )
        self.assertIn(resp.status_code, [200, 204], resp.content)

    def test_tag_views(self):
        # everyone can view the list of tags
        resp = self.client.get(reverse("tags-list"))
        self.assertIn(resp.status_code, [200], resp.content)

        # ensure that unauthenticated users cannot create tags
        resp = self.client.post(reverse("tags-list"), {"name": "Some Tag"})
        self.assertIn(resp.status_code, [400, 403, 405], resp.content)

        # ensure that unauthenticated users cannot delete tags
        resp = self.client.delete(reverse("tags-detail", args=(1,)))
        self.assertIn(resp.status_code, [400, 403, 405], resp.content)

    def test_club_create_empty(self):
        """
        Test creating a club with empty fields.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("clubs-list"),
            {
                "code": "penn-labs",
                "name": "Penn Labs",
                "description": "",
                "tags": [{"name": "Graduate"}],
                "facebook": "",
                "twitter": "",
                "instagram": "",
                "website": "",
                "linkedin": "",
                "github": "",
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

    def test_club_approve(self):
        """
        Test approving an existing unapproved club.
        """
        self.client.login(username=self.user5.username, password="test")

        # mark club as unapproved
        self.club1.approved = None
        self.club1.save(update_fields=["approved"])

        # approve club
        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"approved": True},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure database correctly updated
        self.club1.refresh_from_db()
        self.assertTrue(self.club1.approved)
        self.assertIsNotNone(self.club1.approved_on)
        self.assertIsNotNone(self.club1.approved_by)

    def test_club_create_url_sanitize(self):
        """
        Test creating clubs with malicious URLs.
        """
        self.client.login(username=self.user5.username, password="test")

        exploit_string = "javascript:alert(1)"

        resp = self.client.post(
            reverse("clubs-list"),
            {
                "name": "Bad Club",
                "tags": [],
                "facebook": exploit_string,
                "twitter": exploit_string,
                "instagram": exploit_string,
                "website": exploit_string,
                "linkedin": exploit_string,
                "github": exploit_string,
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_create_description_sanitize_good(self):
        """
        Ensure that descriptions are properly sanitized.
        """
        test_good_string = """<p>Here\'s some <b>bold</b>, <i>italic</i>, <u>underline</u>,
        and a <a href=\"http://example.com\">link</a>.<br></p>
<ul>
    <li>One</li>
    <li>Two</li>
    <li>Three</li>
</ul>
<ol>
    <li>One</li>
    <li>Two</li>
    <li>Three</li>
</ol>
<img src=\"/test.png\">"""

        self.client.login(username=self.user5.username, password="test")
        resp = self.client.post(
            reverse("clubs-list"),
            {
                "name": "Penn Labs",
                "tags": [{"name": "Undergraduate"}],
                "description": test_good_string,
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        resp = self.client.get(reverse("clubs-detail", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)

        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data["description"], test_good_string)

    def test_club_create_description_sanitize_bad(self):
        """
        Ensure that descriptions are properly sanitized.
        """
        test_bad_string = '<script>alert(1);</script><img src="javascript:alert(1)">'

        self.client.login(username=self.user5.username, password="test")
        resp = self.client.post(
            reverse("clubs-list"),
            {"name": "Penn Labs", "tags": [{"name": "Graduate"}], "description": test_bad_string},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        resp = self.client.get(reverse("clubs-detail", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)

        data = json.loads(resp.content.decode("utf-8"))
        self.assertNotIn("<script>", data["description"])
        self.assertNotIn("javascript:", data["description"])

    def test_club_create_no_input(self):
        """
        Passing in no data should result in a bad request.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(reverse("clubs-list"), {}, content_type="application/json")
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_create_nonexistent_tag(self):
        """
        Creating a club with nonexistent tags should throw an error.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("clubs-list"),
            {
                "name": "Penn Labs",
                "description": "We code stuff.",
                "email": "contact@pennlabs.org",
                "tags": [{"name": "totally definitely nonexistent tag"}],
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 404], resp.content)

    def test_club_create_no_auth(self):
        """
        Creating a club without authentication should result in an error.
        """
        resp = self.client.post(
            reverse("clubs-list"),
            {
                "name": "Penn Labs",
                "description": "We code stuff.",
                "email": "contact@pennlabs.org",
                "tags": [],
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_create(self):
        """
        Test properly creating a club.
        """
        tag1 = Tag.objects.create(name="Wharton")
        tag2 = Tag.objects.create(name="Engineering")

        badge1 = Badge.objects.create(label="SAC Funded")
        school1 = School.objects.create(name="Engineering")

        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("clubs-list"),
            {
                "name": "Penn Labs",
                "description": "We code stuff.",
                "badges": [{"label": "SAC Funded"}],
                "tags": [{"name": tag1.name}, {"name": tag2.name}, {"name": "Graduate"}],
                "target_schools": [{"name": school1.name}],
                "facebook": "https://www.facebook.com/groups/966590693376781/"
                + "?ref=nf_target&fref=nf",
                "twitter": "https://twitter.com/Penn",
                "instagram": "https://www.instagram.com/uofpenn/?hl=en",
                "website": "https://pennlabs.org",
                "linkedin": "https://www.linkedin.com/school/university-of-pennsylvania/",
                "youtube": "https://youtu.be/dQw4w9WgXcQ",
                "github": "https://github.com/pennlabs",
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure club was actually created
        club_obj = Club.objects.filter(name="Penn Labs").first()
        self.assertTrue(club_obj)
        self.assertEqual(Membership.objects.filter(club=club_obj).count(), 1)
        self.assertEqual(club_obj.members.count(), 1)
        self.assertEqual(club_obj.target_schools.count(), 1)

        # ensure lookup returns the correct information
        resp = self.client.get(reverse("clubs-detail", args=("penn-labs",)))
        self.assertIn(resp.status_code, [200], resp.content)

        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data["code"], "penn-labs")
        self.assertEqual(data["name"], "Penn Labs")
        self.assertEqual(data["description"], "We code stuff.")
        self.assertTrue(data["tags"], data)
        self.assertEqual(data["members"][0]["name"], self.user5.get_full_name())

        for link in [
            "facebook",
            "twitter",
            "instagram",
            "website",
            "github",
            "youtube",
        ]:
            self.assertIn(link, data)

        self.assertEqual(club_obj.badges.count(), 1)
        self.assertEqual(club_obj.badges.all()[0].label, badge1.label)

    def test_club_create_duplicate(self):
        """
        Creating a duplicate club should result in an 400 error.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("clubs-list"),
            {"name": "Test Club", "tags": []},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_list_search(self):
        """
        Test simple club filtering.
        """
        resp = self.client.get(reverse("clubs-list") + "?search=test")
        self.assertIn(resp.status_code, [200], resp.content)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data)

    def test_club_list_filter(self):
        """
        Test complex club filtering.
        """
        with open(os.devnull, "w") as f:
            call_command("populate", stdout=f)

        prof_tag_id = Tag.objects.filter(name="Professional").first().id
        athl_tag_id = Tag.objects.filter(name="Athletics").first().id

        # query will be in the format /clubs/?format=json&<query>
        # output should be an exact match in terms of clubs returned
        queries = [
            {"query": "tags=Professional,Athletics", "results": ["pppjo"]},
            {"query": f"tags={prof_tag_id},{athl_tag_id}", "results": ["pppjo"]},
            {
                "query": "tags__or=Professional,Athletics",
                "results": ["harvard-rejects", "empty-club", "pppjo"],
            },
            {"query": "founded__lt=2000", "results": ["pppjo"]},
            {"query": "tags=Professional&founded__lt=2000", "results": ["pppjo"]},
            {"query": "accepting_members=true", "results": ["pppjo"]},
            {
                "query": f"size__or={Club.SIZE_MEDIUM},{Club.SIZE_LARGE}",
                "results": ["pppjo", "lorem-ipsum"],
            },
            {
                "query": f"application_required={Club.APPLICATION_REQUIRED_SOME}",
                "results": ["pppjo"],
            },
        ]

        for query in queries:
            resp = self.client.get(f"{reverse('clubs-list')}?format=json&{query['query']}")
            self.assertIn(resp.status_code, [200], resp.content)
            data = json.loads(resp.content.decode("utf-8"))
            codes = [club["code"] for club in data]
            self.assertEqual(set(codes), set(query["results"]), (query, resp.content))

    def test_club_modify_wrong_auth(self):
        """
        Outsiders should not be able to modify a club.
        """
        self.client.login(username=self.user4.username, password="test")
        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"description": "We do stuff.", "tags": []},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_modify_insufficient_auth(self):
        """
        Ordinary members should not be able to modify the club.
        """
        Membership.objects.create(club=Club.objects.get(code=self.club1.code), person=self.user2)
        self.client.login(username=self.user2.username, password="test")
        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"description": "We do stuff.", "tags": []},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_retrieve(self):
        """
        Ordinary members should be able to retrieve the club.
        """
        Membership.objects.create(club=Club.objects.get(code=self.club1.code), person=self.user2)
        self.client.login(username=self.user2.username, password="test")
        resp = self.client.get(reverse("clubs-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200], resp.content)

    def test_club_children(self):
        """
        Any user should be able to view clubs children tree.
        """
        self.client.login(username=self.user3.username, password="test")
        resp = self.client.get(reverse("clubs-children", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200], resp.content)

    def test_club_modify(self):
        """
        Owners and officers should be able to modify the club.
        """
        tag3 = Tag.objects.create(name="College")

        self.client.login(username=self.user5.username, password="test")
        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"description": "We do stuff.", "tags": [{"name": tag3.name}, {"name": "Graduate"}]},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure that changes were made
        resp = self.client.get(reverse("clubs-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200], resp.content)

        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data["description"], "We do stuff.")
        self.assertEqual(len(data["tags"]), 2)

    def test_club_delete_no_auth(self):
        """
        Unauthenticated users should not be able to delete a club.
        """
        resp = self.client.delete(reverse("clubs-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_delete(self):
        """
        Owners should be able to delete the club.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.delete(reverse("clubs-detail", args=(self.club1.code,)))
        self.assertIn(resp.status_code, [200, 204], resp.content)

        # ensure club was deleted
        self.assertFalse(Club.objects.filter(name="Test Club").exists())

    def test_club_deactivate(self):
        """
        Owners should be able to deactivate the club.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"active": False},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 204], resp.content)

        # ensure club was deactivated
        self.assertFalse(Club.objects.get(name="Test Club").active)

    def test_club_deactivate_insufficient_auth(self):
        """
        Officers should not be able to deactivate the club.
        """
        Membership.objects.create(club=self.club1, person=self.user2, role=Membership.ROLE_MEMBER)
        self.client.login(username=self.user2.username, password="test")
        resp = self.client.patch(
            reverse("clubs-detail", args=(self.club1.code,)),
            {"active": False},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_invite(self):
        """
        Test the email invitation feature.
        """
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("club-invite", args=(self.club1.code,)),
            {
                "emails": "one@pennlabs.org, two@pennlabs.org, three@pennlabs.org",
                "role": Membership.ROLE_OFFICER,
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)
        data = json.loads(resp.content.decode("utf-8"))

        # ensure membership invite was created
        invites = MembershipInvite.objects.filter(club__code=self.club1.code)
        self.assertEqual(invites.count(), 3, data)
        self.assertEqual(
            list(invites.values_list("role", flat=True)), [Membership.ROLE_OFFICER] * 3, data,
        )
        self.assertEqual(len(mail.outbox), 3, mail.outbox)

        # ensure we can get all memberships
        ids_and_tokens = MembershipInvite.objects.filter(club__code=self.club1.code).values_list(
            "id", "token"
        )
        for id, token in ids_and_tokens:
            resp = self.client.get(reverse("club-invites-detail", args=(self.club1.code, id)))
            self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure invite can be redeemed
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.patch(
            reverse("club-invites-detail", args=(self.club1.code, ids_and_tokens[0][0])),
            {"token": ids_and_tokens[0][1], "public": True},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        flt = Membership.objects.filter(club=self.club1, person=self.user5)
        self.assertTrue(flt.exists())
        self.assertTrue(flt.first().public)

        # ensure invite cannot be reclaimed
        resp = self.client.patch(
            reverse("club-invites-detail", args=(self.club1.code, ids_and_tokens[0][0])),
            {"token": ids_and_tokens[0][1]},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403, 404], resp.content)

        # ensure invite can be deleted
        self.client.login(username=self.user5.username, password="test")
        resp = self.client.delete(
            reverse("club-invites-detail", args=(self.club1.code, ids_and_tokens[1][0]))
        )
        self.assertIn(resp.status_code, [200, 204], resp.content)

        # ensure a second invite can be claimed without toggling on public status
        self.client.login(username=self.user4.username, password="test")

        resp = self.client.patch(
            reverse("club-invites-detail", args=(self.club1.code, ids_and_tokens[2][0])),
            {"token": ids_and_tokens[2][1], "public": False},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        flt = Membership.objects.filter(club=self.club1, person=self.user4)
        self.assertTrue(flt.exists())
        self.assertFalse(flt.first().public)

    def test_club_invite_email_check(self):
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("club-invite", args=(self.club1.code,)),
            {"emails": "test@example.upenn.edu", "role": Membership.ROLE_OFFICER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        invite = MembershipInvite.objects.filter(club__code=self.club1.code).first()

        self.client.login(username=self.user1.username, password="test")

        resp = self.client.patch(
            reverse("club-invites-detail", args=(self.club1.code, invite.id)),
            {"token": invite.token},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        self.assertTrue(len(mail.outbox), 2)

    def test_club_invite_email_resend(self):
        self.client.login(username=self.user5.username, password="test")

        resp = self.client.post(
            reverse("club-invite", args=(self.club1.code,)),
            {"emails": "test@example.upenn.edu", "role": Membership.ROLE_MEMBER},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        invite = MembershipInvite.objects.filter(club__code=self.club1.code).first()

        resp = self.client.put(
            reverse("club-invites-resend", args=(self.club1.code, invite.id)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

    def test_club_invite_insufficient_auth(self):
        self.client.login(username=self.user2.username, password="test")
        Membership.objects.create(person=self.user2, club=self.club1)

        resp = self.client.post(
            reverse("club-invite", args=(self.club1.code,)),
            {"emails": "one@pennlabs.org, two@pennlabs.org, three@pennlabs.org"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_invite_insufficient_permissions(self):
        self.client.login(username=self.user2.username, password="test")
        Membership.objects.create(person=self.user2, club=self.club1, role=Membership.ROLE_OFFICER)

        resp = self.client.post(
            reverse("club-invite", args=(self.club1.code,)),
            {
                "emails": "one@pennlabs.org, two@pennlabs.org, three@pennlabs.org",
                "role": Membership.ROLE_OWNER,
                "title": "Supreme Leader",
            },
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_has_badges(self):
        badge = Badge(label="SAC Funded", description="")
        badge.save()
        self.club1.badges.add(badge)
        resp = self.client.get(reverse("clubs-detail", args=(self.club1.code,)))
        club = json.loads(resp.content)
        badge_json = club["badges"][0]
        self.assertEqual(badge.label, badge_json["label"])

    def test_create_note(self):
        self.client.login(username=self.user2.username, password="test")

        # Try to create note without permissions
        resp = self.client.post(
            reverse("clubs-detail", args=(self.club1.code,)) + "notes/",
            {
                "creator": self.user2.username,
                "creating_club": self.club1.code,
                "subject_club": self.club1.code,
                "title": "Note1",
                "content": "Content",
                "creating_club_permission": 20,
                "outside_club_permission": 0,
            },
            content_type="application/json",
        )

        self.assertIn(resp.status_code, [400, 403], resp.content)

        Membership.objects.create(person=self.user2, club=self.club1, role=Membership.ROLE_OFFICER)

        # Creating note after given permissions
        resp = self.client.post(
            reverse("clubs-detail", args=(self.club1.code,)) + "notes/",
            {
                "creator": self.user2.username,
                "creating_club": self.club1.code,
                "subject_club": self.club1.code,
                "title": "Note1",
                "content": "Content",
                "creating_club_permission": 20,
                "outside_club_permission": 0,
            },
            content_type="application/json",
        )

        self.assertIn(resp.status_code, [200, 201], resp.content)

        # Still cannot create note above permission level
        resp = self.client.post(
            reverse("clubs-detail", args=(self.club1.code,)) + "notes/",
            {
                "creator": self.user2.username,
                "creating_club": self.club1.code,
                "subject_club": self.club1.code,
                "title": "Note1",
                "content": "Content",
                "creating_club_permission": 0,
                "outside_club_permission": 0,
            },
            content_type="application/json",
        )

        self.assertIn(resp.status_code, [400, 403], resp.content)

    def test_club_report_selects_one_field(self):
        res = self.client.get(reverse("clubs-list"), {"format": "xlsx", "fields": "name"})
        self.assertEqual(200, res.status_code)
        self.assertEqual(1, len(res.data))
        self.assertTrue(isinstance(res.data[0], dict))
        self.assertEqual(1, len(res.data[0]))

    def test_club_report_selects_few_fields(self):
        res = self.client.get(reverse("clubs-list"), {"format": "xlsx", "fields": "name,code"})
        self.assertEqual(200, res.status_code)
        self.assertEqual(1, len(res.data))
        self.assertTrue(isinstance(res.data[0], dict))
        self.assertEqual(2, len(res.data[0]))

    def test_club_report_selects_all_fields(self):
        res = self.client.get(reverse("clubs-list"), {"format": "xlsx"})
        self.assertEqual(200, res.status_code)
        self.assertEqual(1, len(res.data))
        self.assertTrue(isinstance(res.data[0], dict))
        self.assertTrue(len(res.data[0]) > 2)

    def test_club_members_report(self):
        # login for extended member information
        self.client.login(username=self.user5.username, password="test")

        # add a membership
        Membership.objects.create(person=self.user5, club=self.club1)

        # generate the report
        resp = self.client.get(
            reverse("club-members-list", args=("test-club",)), {"format": "xlsx"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(resp.data))

    def test_club_subscriptions_report(self):
        resp = self.client.get(
            reverse("clubs-subscription", args=("test-club",)), {"format": "xlsx"}
        )
        self.assertEqual(200, resp.status_code)

    def test_club_questions(self):
        resp = self.client.get(reverse("club-questions-list", args=("test-club",)))
        self.assertEqual(200, resp.status_code)

        # ensure only approved questions are shown
        self.assertEqual(1, len(resp.data))

    def test_club_question_answer(self):
        # add officer to club
        Membership.objects.create(person=self.user5, club=self.club1, role=Membership.ROLE_OFFICER)

        # login to an account
        self.client.login(username=self.user4.username, password="test")

        # fetch question list from server
        resp = self.client.get(reverse("club-questions-list", args=("test-club",)))
        self.assertEqual(200, resp.status_code)
        old_count = len(resp.data)

        # generate a question
        resp = self.client.post(
            reverse("club-questions-list", args=("test-club",)),
            {"question": "Is this club cool?", "is_anonymous": False},
        )
        self.assertIn(resp.status_code, [200, 201])

        # fetch question list from server
        resp = self.client.get(reverse("club-questions-list", args=("test-club",)))
        self.assertEqual(200, resp.status_code)

        # ensure question appears in response
        self.assertEqual(len(resp.data), old_count + 1, resp.data)

        # ensure email was sent out notifying officer of question
        self.assertEqual(len(mail.outbox), 1, mail.outbox)

    def test_club_sensitive_field_renew(self):
        """
        When editing sensitive fields like the name, description, and club image, require
        the club to be reapproved.
        """
        club = self.club1

        # ensure club is approved
        self.assertTrue(club.approved)

        # add officer to club
        Membership.objects.create(person=self.user4, club=club, role=Membership.ROLE_OFFICER)

        # login to officer user
        self.client.login(username=self.user4.username, password="test")

        for field in {"name", "description"}:
            # edit sensitive field
            resp = self.client.patch(
                reverse("clubs-detail", args=(club.code,)),
                {field: "New Club Name/Description"},
                content_type="application/json",
            )
            self.assertIn(resp.status_code, [200, 201], resp.content)

            # ensure club is marked as not approved
            club.refresh_from_db()
            self.assertFalse(club.approved)

            # reset to approved
            club.approved = True
            club.save(update_fields=["approved"])

    def test_club_detail_endpoints_unauth(self):
        """
        Ensure that club based endpoints are not usable by unauthenticated users.
        """
        club = self.club1

        # subscription endpoint should fail
        resp = self.client.get(
            reverse("clubs-subscription", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # membership requests should fail
        resp = self.client.get(
            reverse("club-membership-requests-list", args=(club.code,)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # uploading image should fail
        resp = self.client.post(
            reverse("clubs-upload", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # uploading file should fail
        resp = self.client.post(
            reverse("clubs-upload-file", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

    def test_club_detail_endpoints_insufficient_auth(self):
        """
        Ensure that the club based endpoints are not usable by users with insufficient auth.
        """
        # login to account
        self.client.login(username=self.user4.username, password="test")

        club = self.club1

        # ensure account is not a member
        self.assertFalse(club.membership_set.filter(person=self.user4).exists())

        # subscription endpoint should fail
        resp = self.client.get(
            reverse("clubs-subscription", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # membership requests should fail
        resp = self.client.get(
            reverse("club-membership-requests-list", args=(club.code,)),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # uploading image should fail
        resp = self.client.post(
            reverse("clubs-upload", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

        # uploading file should fail
        resp = self.client.post(
            reverse("clubs-upload-file", args=(club.code,)), content_type="application/json"
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)

    def test_club_renew(self):
        # run deactivate script
        with open(os.devnull, "w") as f:
            call_command("deactivate", "all", "--force", stdout=f)

        # count already sent emails
        mail_count = len(mail.outbox)

        # choose a club
        club = self.club1

        # add a badge to the club
        badge = Badge.objects.create(label="Test Badge", description="This is a test badge!")
        club.badges.add(badge)

        # add officer to club
        Membership.objects.create(person=self.user4, club=club, role=Membership.ROLE_OFFICER)

        # login to officer account
        self.client.login(username=self.user4.username, password="test")

        # mark the club as active (student side renewal)
        resp = self.client.patch(
            reverse("clubs-detail", args=(club.code,)),
            {"active": True},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # add approve privileges to account
        content_type = ContentType.objects.get_for_model(Club)
        self.user3.user_permissions.add(
            Permission.objects.get(codename="approve_club", content_type=content_type)
        )
        self.user3.user_permissions.add(
            Permission.objects.get(codename="see_pending_clubs", content_type=content_type)
        )

        # ensure user is not superuser
        self.assertFalse(self.user3.is_superuser)

        # login to account with approve club privilege
        self.client.login(username=self.user3.username, password="test")

        # approve the club
        resp = self.client.patch(
            reverse("clubs-detail", args=(club.code,)),
            {"approved": True, "approved_comment": "This is a great club!"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure email is sent out to let club know
        self.assertEqual(len(mail.outbox), mail_count + 1, mail.outbox)

        # update mail count
        mail_count = len(mail.outbox)

        # mark club has unapproved
        club.approved = None
        club.save(update_fields=["approved"])

        # reject the club
        resp = self.client.patch(
            reverse("clubs-detail", args=(club.code,)),
            {"approved": False, "approved_comment": "This is a bad club!"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure email is sent out to let club know
        self.assertEqual(len(mail.outbox), mail_count + 1, mail.outbox)

        # approve the club without comment
        club.approved = None
        club.save(update_fields=["approved"])

        resp = self.client.patch(
            reverse("clubs-detail", args=(club.code,)),
            {"approved": True, "approved_comment": ""},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201], resp.content)

        # ensure badge still exists
        self.assertTrue(club.badges.filter(pk=badge.pk).count(), 1)

        # mark club as unapproved
        club.approved = None
        club.save(update_fields=["approved"])

        # login as user without approve permissions
        self.assertFalse(self.user2.has_perm("clubs.approve_club"))
        Membership.objects.create(person=self.user2, club=club, role=Membership.ROLE_OFFICER)

        self.client.login(username=self.user2.username, password="test")

        # try approving the club
        resp = self.client.patch(
            reverse("clubs-detail", args=(club.code,)),
            {"approved": True, "approved_comment": "I'm approving my own club!"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [401, 403], resp.content)
