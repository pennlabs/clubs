from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Exists, OuterRef

from clubs.models import Asset, Club, Event, Favorite, Membership, MembershipInvite, Tag


class HasOwnerListFilter(admin.SimpleListFilter):
    title = 'has owner'
    parameter_name = 'has_owner'

    def lookups(self, request, model_admin):
        return [('true', 'True'), ('false', 'False')]

    def queryset(self, request, queryset):
        return queryset.filter(has_owner=self.value() == 'true')


class ClubAdmin(admin.ModelAdmin):
    search_fields = ('name', 'subtitle', 'email')
    list_display = ('name', 'email', 'has_owner', 'has_invite')
    list_filter = ('size', 'application_required', 'accepting_members', HasOwnerListFilter)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            has_owner=Exists(Membership.objects.filter(club=OuterRef('pk'), role__lte=0)),
            has_invite=Exists(MembershipInvite.objects.filter(club=OuterRef('pk')))
        )

    def has_invite(self, obj):
        return obj.has_invite
    has_invite.boolean = True

    def has_owner(self, obj):
        return obj.has_owner
    has_owner.boolean = True


class EventAdmin(admin.ModelAdmin):
    search_fields = ('name', 'club__name')
    list_filter = ('start_time', 'end_time')


class FavoriteAdmin(admin.ModelAdmin):
    search_fields = ('person__username', 'person__email', 'club__name', 'club__pk')


class MembershipAdmin(admin.ModelAdmin):
    search_fields = ('person__username', 'person__email', 'club__name', 'club__pk', 'title')
    list_filter = ('role',)


class TagAdmin(admin.ModelAdmin):
    def club_count(self, obj):
        return obj.club_set.count()

    search_fields = ('name',)
    list_display = ('name', 'club_count')


admin.site.unregister(Group)


admin.site.register(Asset)
admin.site.register(Club, ClubAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(MembershipInvite)
admin.site.register(Tag, TagAdmin)
