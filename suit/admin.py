import copy

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes import admin as ct_admin
from django.db import models
from django.forms import ModelForm
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

"""
Adapted by using following examples:
https://djangosnippets.org/snippets/2887/
http://stackoverflow.com/a/7192721/641263
"""

link_to_prefix = "link_to_"


def get_admin_url(instance, admin_prefix="admin", current_app=None):
    if not instance.pk:
        return
    return reverse_lazy(
        "%s:%s_%s_change" % (admin_prefix, instance._meta.app_label, instance._meta.model_name),
        args=(instance.pk,),
        current_app=current_app,
    )


def get_related_field(name, short_description=None, admin_order_field=None, admin_prefix="admin"):
    """
    Create a function that can be attached to a ModelAdmin to use as a list_display field, e.g:
    client__name = get_related_field('client__name', short_description='Client')
    """
    as_link = name.startswith(link_to_prefix)
    if as_link:
        name = name[len(link_to_prefix) :]
    related_names = name.split("__")

    def getter(self, obj):
        for related_name in related_names:
            if not obj:
                continue
            obj = getattr(obj, related_name)
        if obj and as_link:
            obj = mark_safe(
                u'<a href="%s" class="link-with-icon">%s<i class="fa fa-caret-right"></i></a>'
                % (get_admin_url(obj, admin_prefix, current_app=self.admin_site.name), obj)
            )
        return obj

    getter.admin_order_field = admin_order_field or name
    getter.short_description = short_description or related_names[-1].title().replace("_", " ")
    if as_link:
        getter.allow_tags = True
    return getter


class RelatedFieldAdminMetaclass(type(admin.ModelAdmin)):
    related_field_admin_prefix = "admin"

    def __new__(cls, name, bases, attrs):
        new_class = super(RelatedFieldAdminMetaclass, cls).__new__(cls, name, bases, attrs)

        for field in new_class.list_display:
            if "__" in field or field.startswith(link_to_prefix):
                if not hasattr(new_class, field):
                    setattr(new_class, field, get_related_field(field, admin_prefix=cls.related_field_admin_prefix))

        return new_class


class RelatedFieldAdmin(admin.ModelAdmin):
    """
    Version of ModelAdmin that can use linked and related fields in list_display, e.g.:
    list_display = ('link_to_user', 'address__city', 'link_to_address__city', 'address__country__country_code')
    """

    __metaclass__ = RelatedFieldAdminMetaclass

    def get_queryset(self, request):
        qs = super(RelatedFieldAdmin, self).get_queryset(request)

        # Include all related fields in queryset
        select_related = []
        for field in self.list_display:
            if "__" in field:
                if field.startswith(link_to_prefix):
                    field = field[len(link_to_prefix) :]
                select_related.append(field.rsplit("__", 1)[0])

        # Include all foreign key fields in queryset.
        # This is based on ChangeList.get_query_set().
        # We have to duplicate it here because select_related() only works once.
        # Can't just use list_select_related because we might have multiple__depth__fields it won't follow.
        model = qs.model
        for field_name in self.list_display:
            try:
                field = model._meta.get_field(field_name)
            except models.FieldDoesNotExist:
                continue

            if isinstance(field.remote_field, models.ManyToOneRel):
                select_related.append(field_name)

        return qs.select_related(*select_related)


from suit.widgets import NumberInput, SuitSplitDateTimeWidget


class SortableModelAdminBase(object):
    """
    Base class for SortableTabularInline and SortableModelAdmin
    """

    sortable = "order"

    class Media:
        js = ("suit/js/sortables.js",)


class SortableListForm(ModelForm):
    """
    Just Meta holder class
    """

    class Meta:
        widgets = {"order": NumberInput(attrs={"class": "hide input-mini suit-sortable"})}


class SortableChangeList(ChangeList):
    """
    Class that forces ordering by sortable param only
    """

    def get_ordering(self, request, queryset):
        return [self.model_admin.sortable, "-" + self.model._meta.pk.name]


class SortableTabularInlineBase(SortableModelAdminBase):
    """
    Sortable tabular inline
    """

    def __init__(self, *args, **kwargs):
        super(SortableTabularInlineBase, self).__init__(*args, **kwargs)

        self.ordering = (self.sortable,)
        self.fields = self.fields or []
        if self.fields and self.sortable not in self.fields:
            self.fields = list(self.fields) + [self.sortable]

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == self.sortable:
            kwargs["widget"] = SortableListForm.Meta.widgets["order"]
        return super(SortableTabularInlineBase, self).formfield_for_dbfield(db_field, **kwargs)


class SortableTabularInline(SortableTabularInlineBase, admin.TabularInline):
    pass


class SortableGenericTabularInline(SortableTabularInlineBase, ct_admin.GenericTabularInline):
    pass


class SortableStackedInlineBase(SortableModelAdminBase):
    """
    Sortable stacked inline
    """

    def __init__(self, *args, **kwargs):
        super(SortableStackedInlineBase, self).__init__(*args, **kwargs)
        self.ordering = (self.sortable,)

    def get_fieldsets(self, *args, **kwargs):
        """
        Iterate all fieldsets and make sure sortable is in the first fieldset
        Remove sortable from every other fieldset, if by some reason someone
        has added it
        """
        fieldsets = super(SortableStackedInlineBase, self).get_fieldsets(*args, **kwargs)

        sortable_added = False
        for fieldset in fieldsets:
            for line in fieldset:
                if not line or not isinstance(line, dict):
                    continue

                fields = line.get("fields")

                # Some use tuples for fields however they are immutable
                if isinstance(fields, tuple):
                    raise AssertionError(
                        "The fields attribute of your Inline is a tuple. "
                        "This must be list as we may need to modify it and "
                        "tuples are immutable."
                    )

                if self.sortable in fields:
                    fields.remove(self.sortable)

                # Add sortable field always as first
                if not sortable_added:
                    fields.insert(0, self.sortable)
                    sortable_added = True
                    break

        return fieldsets

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == self.sortable:
            kwargs["widget"] = copy.deepcopy(SortableListForm.Meta.widgets["order"])
            kwargs["widget"].attrs["class"] += " suit-sortable-stacked"
            kwargs["widget"].attrs["rowclass"] = " suit-sortable-stacked-row"
        return super(SortableStackedInlineBase, self).formfield_for_dbfield(db_field, **kwargs)


class SortableStackedInline(SortableStackedInlineBase, admin.StackedInline):
    pass


class SortableGenericStackedInline(SortableStackedInlineBase, ct_admin.GenericStackedInline):
    pass


class SortableModelAdmin(SortableModelAdminBase, ModelAdmin):
    """
    Sortable tabular inline
    """

    list_per_page = 500

    def __init__(self, *args, **kwargs):
        super(SortableModelAdmin, self).__init__(*args, **kwargs)

        self.ordering = (self.sortable,)
        if self.list_display and self.sortable not in self.list_display:
            self.list_display = list(self.list_display) + [self.sortable]

        self.list_editable = self.list_editable or []
        if self.sortable not in self.list_editable:
            self.list_editable = list(self.list_editable) + [self.sortable]

        self.exclude = self.exclude or []
        if self.sortable not in self.exclude:
            self.exclude = list(self.exclude) + [self.sortable]

    def merge_form_meta(self, form):
        """
        Prepare Meta class with order field widget
        """
        if not getattr(form, "Meta", None):
            form.Meta = SortableListForm.Meta
        if not getattr(form.Meta, "widgets", None):
            form.Meta.widgets = {}
        form.Meta.widgets[self.sortable] = SortableListForm.Meta.widgets["order"]

    def get_changelist_form(self, request, **kwargs):
        form = super(SortableModelAdmin, self).get_changelist_form(request, **kwargs)
        self.merge_form_meta(form)
        return form

    def get_changelist(self, request, **kwargs):
        return SortableChangeList

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            max_order = obj.__class__.objects.aggregate(models.Max(self.sortable))
            try:
                next_order = max_order["%s__max" % self.sortable] + 1
            except TypeError:
                next_order = 1
            setattr(obj, self.sortable, next_order)
        super(SortableModelAdmin, self).save_model(request, obj, form, change)


# Quite aggressive detection and intrusion into Django CMS
# Didn't found any other solutions though
if "cms" in settings.INSTALLED_APPS:
    try:
        from cms.admin.forms import PageForm

        PageForm.Meta.widgets = {
            "publication_date": SuitSplitDateTimeWidget,
            "publication_end_date": SuitSplitDateTimeWidget,
        }
    except ImportError:
        pass
