import uuid
from datetime import timedelta

from accounts.models import AccessToken, RefreshToken
from accounts.settings import accounts_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import RemoteUserBackend
from django.utils import timezone


class LabsUserBackend(RemoteUserBackend):
    def authenticate(self, request, remote_user, tokens=True):
        """
        Authenticate a user given a dictionary of user information from
        platform.
        TEMPORARY CUSTOM BACKEND TO HANDLE MIGRATION TO PENNIDS
        """
        if not remote_user:
            return
        User = get_user_model()
        pennkey_user_query = User.objects.filter(username=remote_user["username"])
        if len(pennkey_user_query) == 0:
            # User hasn't logged into Clubs before
            user, created = User.objects.get_or_create(
                id=remote_user["pennid"], defaults={"username": remote_user["username"]}
            )
        else:
            pennkey_user = pennkey_user_query[0]
            # Create new user with correct id
            if pennkey_user.id != remote_user["pennid"]:
                pennkey_user.username = uuid.uuid4()
                pennkey_user.save()
                user, created = (
                    User.objects.create(id=remote_user["pennid"], username=remote_user["username"]),
                    True,
                )

                # Update all many-to-many relationships
                for favorite in pennkey_user.favorite_set.all():
                    favorite.person = user
                    favorite.save()

                for membership in pennkey_user.membership_set.all():
                    membership.person = user
                    membership.save()

                for membership_invite in pennkey_user.membershipinvite_set.all():
                    membership_invite.creator = user
                    membership_invite.save()

                # delete old user.
                pennkey_user.delete()

            # Updated user already exists
            else:
                user, created = pennkey_user, False

        if created:
            user.set_unusable_password()
            user.save()
            try:
                user = self.configure_user(request, user)
            except TypeError:
                user = self.configure_user(user)

        # Update user fields if changed
        for field in ["first_name", "last_name", "username", "email"]:
            if getattr(user, field) is not remote_user[field]:
                setattr(user, field, remote_user[field])

        #  Update Access and Refresh Token if desired
        if tokens:
            AccessToken.objects.update_or_create(
                user=user,
                defaults={
                    "expires_at": timezone.now()
                    + timedelta(seconds=remote_user["token"]["expires_in"]),
                    "token": remote_user["token"]["access_token"],
                },
            )
            RefreshToken.objects.update_or_create(
                user=user, defaults={"token": remote_user["token"]["refresh_token"]}
            )

        # Set or remove admin permissions
        if accounts_settings.ADMIN_PERMISSION in remote_user["product_permission"]:
            if not user.is_staff:
                user.is_staff = True
                user.is_superuser = True
        else:
            if user.is_staff:
                user.is_staff = False
                user.is_superuser = False

        user.save()
        self.post_authenticate(user, created, remote_user)
        return user if self.user_can_authenticate(user) else None

    def post_authenticate(self, user, created, dictionary):
        """
        Post Authentication method that is run after logging in a user.
        This allows products to add custom configuration by subclassing
        LabsUserBackend and modifying this method.
        By default this does nothing.
        """
        pass
