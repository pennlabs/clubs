from rest_framework import permissions

from clubs.models import Membership


class ReadOnly(permissions.BasePermission):
    """
    Only allow read access. Deny write access to everyone.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return False


class ClubPermission(permissions.BasePermission):
    """
    Only club owners should be able to delete.
    Club owners and officers should be able to update.
    Anyone with permission should be able to create.
    """

    def has_object_permission(self, request, view, obj):
        if view.action in ["retrieve", "children"]:
            return True

        if not request.user.is_authenticated:
            return False

        # club approvers can update the club
        if view.action in ["update", "partial_update"] and request.user.has_perm(
            "clubs.approve_club"
        ):
            return True

        # user must be in club to perform non-view actions
        membership = Membership.objects.filter(person=request.user, club=obj).first()
        if membership is None:
            return False

        # user has to be an owner to delete a club, an officer to edit it
        if view.action in ["destroy"]:
            return membership.role <= Membership.ROLE_OWNER
        else:
            return membership.role <= Membership.ROLE_OFFICER

    def has_permission(self, request, view):
        if view.action in [
            "children",
            "destroy",
            "partial_update",
            "update",
            "upload",
            "upload_file",
        ]:
            return request.user.is_authenticated
        elif view.action in ["create"]:
            return request.user.is_authenticated
        else:
            return True


class EventPermission(permissions.BasePermission):
    """
    Officers and above can create/update/delete events.
    Everyone else can view and list events.
    """

    def has_permission(self, request, view):
        if view.action in ["create", "update", "partial_update", "destroy"]:
            if "club_code" not in view.kwargs:
                return False
            if not request.user.is_authenticated:
                return False
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()
            return membership is not None and membership.role <= Membership.ROLE_OFFICER
        else:
            return True


class ClubItemPermission(permissions.BasePermission):
    """
    Officers and above can create/update/delete events or testimonials.
    Everyone else can view and list events or testimonials.
    """

    def has_permission(self, request, view):
        if view.action in ["create", "update", "partial_update", "destroy"]:
            if "club_code" not in view.kwargs:
                return False
            if not request.user.is_authenticated:
                return False
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()
            return membership is not None and membership.role <= Membership.ROLE_OFFICER
        else:
            return True


class IsSuperuser(permissions.BasePermission):
    """
    Grants permission if the current user is a superuser.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.is_superuser

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class MemberPermission(permissions.BasePermission):
    """
    Members of a higher role can update/delete members of equal or lower roles, except ordinary
    members.
    Members can edit themselves, with additional restrictions on the serializer level.
    Officers and above can add new members.
    Anyone can view membership.
    """

    def has_object_permission(self, request, view, obj):
        membership = Membership.objects.filter(
            person=request.user, club__code=view.kwargs["club_code"]
        ).first()
        if membership is None:
            return False

        # any member can retrieve a membership
        if view.action in ["retrieve"]:
            return membership.role <= Membership.ROLE_MEMBER

        # can modify own membership, with restrictions
        if obj == membership and view.action in ["update", "partial_update", "destroy"]:
            # owners cannot delete themselves without passing on ownership
            if view.action in ["destroy"] and membership.role <= Membership.ROLE_OWNER:
                return False
            return True

        # only officers and above can edit other users
        if membership.role >= Membership.ROLE_MEMBER:
            return False

        # users can edit other users with same authority or lower
        return membership.role <= obj.role

    def has_permission(self, request, view):
        if view.action in ["update", "partial_update", "destroy"]:
            return request.user.is_authenticated
        elif view.action in ["create"]:
            if not request.user.is_authenticated:
                return False
            if "club_code" not in view.kwargs:
                return False
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()
            return membership is not None and membership.role <= Membership.ROLE_OFFICER
        else:
            return True


class MembershipRequestPermission(permissions.BasePermission):
    """
    Only officers and above can view and modify membership requests.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if "club_code" not in view.kwargs:
            return False

        membership = Membership.objects.filter(
            person=request.user, club__code=view.kwargs["club_code"]
        ).first()
        return membership is not None and membership.role <= Membership.ROLE_OFFICER


class InvitePermission(permissions.BasePermission):
    """
    Officers and higher can list/delete invitations.
    Anyone authenticated can redeem invitations.
    """

    def has_permission(self, request, view):
        if view.action in ["retrieve", "update", "partial_update"]:
            return request.user.is_authenticated
        else:
            if not request.user.is_authenticated:
                return False
            if "club_code" not in view.kwargs:
                return False
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()
            return membership is not None and membership.role <= Membership.ROLE_OFFICER


class AssetPermission(permissions.BasePermission):
    """
    Officers and higher can upload assets for a club.
    Anyone authenticated can view assets.
    """

    def has_permission(self, request, view):
        if view.action in ["list", "retrieve"]:
            return request.user.is_authenticated
        else:
            if not request.user.is_authenticated:
                return False
            if "club_code" not in view.kwargs:
                return False
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()
            return membership is not None and membership.role <= Membership.ROLE_OFFICER


class QuestionAnswerPermission(permissions.BasePermission):
    """
    Controls permissions for viewing, editing, and removing club questions and answers.
    """

    def has_object_permission(self, request, view, obj):
        if view.action in ["update", "partial_update", "destroy"]:
            # must be logged in to modify questions and answers
            if not request.user.is_authenticated:
                return False

            # only allow original user to edit and delete if the question has not been answered
            if obj.author == request.user and obj.answer is None:
                return True

            # otherwise, allow club officers to edit and delete comments
            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()

            return membership is not None and membership.role <= Membership.ROLE_OFFICER

        return True

    def has_permission(self, request, view):
        if view.action in ["list", "retrieve"]:
            return True

        return request.user.is_authenticated


class NotePermission(permissions.BasePermission):
    """
    There are two permission classes for notes

    creating_club_permission (Creating Club Owner,
                              Creating Club Officers,
                              Creating Club Members):
    This keeps track of who within the club is allowed to view or modify a
    particular note.

    outside_club_permission (None,
                             Subject Club Owner,
                             Subject Club Officer,
                             Subject Club Member,
                             Public):
    This keeps track of who outside of the creating club is allowed to view a
    note. No one outside of the creating club is allowed to modify the note.
    """

    def has_permission(self, request, view):
        # Only users who are in clubs can creating notes for those clubs
        # and they cannot create notes that are above their permission level
        if view.action in ["list", "retrieve"]:
            return request.user.is_authenticated
        elif view.action in ["create"]:
            creating_club_permission = request.data.get("creating_club_permission")

            # Running create without actually passing any data
            # causes problems
            if creating_club_permission is None:
                return False

            membership = Membership.objects.filter(
                person=request.user, club__code=view.kwargs["club_code"]
            ).first()

            if membership is None or membership.role > creating_club_permission:
                return False

            return True
        else:
            return request.user.is_authenticated
