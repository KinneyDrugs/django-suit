from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
from django.forms import Textarea, TextInput, ClearableFileInput
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class AutosizedTextarea(Textarea):
    """
    AutoSized TextArea - TextArea height dynamically grows based on user input
    """

    def __init__(self, attrs=None):
        new_attrs = _make_attrs(attrs, {"rows": 2}, "autosize form-control")
        super(AutosizedTextarea, self).__init__(new_attrs)

    @property
    def media(self):
        return forms.Media(js=("suit/js/autosize.min.js",))

    def render(self, name, value, attrs=None, renderer=None):
        output = super(AutosizedTextarea, self).render(name, value, attrs, renderer)
        output += mark_safe(
            "<script type=\"text/javascript\">"
            "django.jQuery(function () { autosize(document.getElementById('id_{}')); });"
            "</script>".format(name)
        )
        return output


class CharacterCountTextarea(AutosizedTextarea):
    """
    TextArea with character count. Supports also twitter specific count.
    """

    def render(self, name, value, attrs=None, renderer=None):
        output = super(CharacterCountTextarea, self).render(name, value, attrs, renderer)
        output += mark_safe(
            '<script type="text/javascript">'
            "django.jQuery(function () { django.jQuery('#id_{}').suitCharactersCount(); });"
            "</script>".format(name)
        )
        return output


class ImageWidget(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        html = super(ImageWidget, self).render(name, value, attrs, renderer)
        if not value or not hasattr(value, "url") or not value.url:
            return html
        html = (
            '<div class="ImageWidget"><div class="float-xs-left">'
            '<a href="{}" target="_blank"><img src="{}" width="75"></a>'
            "</div>{}</div>".format(value.url, value.url, html)
        )
        return mark_safe(html)


class EnclosedInput(TextInput):
    """
    Widget for bootstrap appended/prepended inputs
    """

    def __init__(self, attrs=None, prepend=None, append=None, prepend_class="addon", append_class="addon"):
        """
        :param prepend_class|append_class: CSS class applied to wrapper element. Values: addon or btn
        """
        self.prepend = prepend
        self.prepend_class = prepend_class
        self.append = append
        self.append_class = append_class
        super(EnclosedInput, self).__init__(attrs=attrs)

    def enclose_value(self, value, wrapper_class):
        if value.startswith("fa-"):
            value = '<i class="fa {}"></i>'.format(value)
        return '<span class="input-group-{}">{}</span>'.format(wrapper_class, value)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(EnclosedInput, self).render(name, value, attrs, renderer)
        div_classes = set()
        if self.prepend:
            div_classes.add("input-group")
            self.prepend = self.enclose_value(self.prepend, self.prepend_class)
            output = "".join((self.prepend, output))
        if self.append:
            div_classes.add("input-group")
            self.append = self.enclose_value(self.append, self.append_class)
            output = "".join((output, self.append))

        return mark_safe('<div class="{}">{}</div>'.format(" ".join(div_classes), output))


class NumberInput(TextInput):
    """
    HTML5 Number input
    Left for backwards compatibility
    """

    input_type = "number"


#
# Original date widgets with addition html
#
class SuitDateWidget(AdminDateWidget):
    def __init__(self, attrs=None, format=None):
        defaults = {"placeholder": _("Date:")[:-1]}
        new_attrs = _make_attrs(attrs, defaults, "vDateField input-small")
        super(SuitDateWidget, self).__init__(attrs=new_attrs, format=format)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(SuitDateWidget, self).render(name, value, attrs, renderer)
        return mark_safe(
            '<div class="input-append suit-date">{}<span '
            'class="add-on"><i class="icon-calendar"></i></span></div>'.format(output)
        )


class SuitTimeWidget(AdminTimeWidget):
    def __init__(self, attrs=None, format=None):
        defaults = {"placeholder": _("Time:")[:-1]}
        new_attrs = _make_attrs(attrs, defaults, "vTimeField input-small")
        super(SuitTimeWidget, self).__init__(attrs=new_attrs, format=format)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(SuitTimeWidget, self).render(name, value, attrs, renderer)
        return mark_safe(
            '<div class="input-append suit-date suit-time">{}<span '
            'class="add-on"><i class="icon-time"></i></span></div>'.format(output)
        )


class SuitSplitDateTimeWidget(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """

    def __init__(self, attrs=None):
        widgets = [SuitDateWidget, SuitTimeWidget]
        forms.MultiWidget.__init__(self, widgets, attrs)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(SuitSplitDateTimeWidget, self).render(name, value, attrs, renderer)
        return mark_safe('<div class="datetime">{}</div>'.format(output))


def _make_attrs(attrs, defaults=None, classes=None):
    result = defaults.copy() if defaults else {}
    if attrs:
        result.update(attrs)
    if classes:
        result["class"] = " ".join((classes, result.get("class", "")))
    return result
