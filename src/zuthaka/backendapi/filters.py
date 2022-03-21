from django_filters import rest_framework as filters
from .models import C2
from .models import Listener
from .models import Launcher


class C2Filter(filters.FilterSet):
    created_since = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="gte"
    )
    created_until = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="lte"
    )

    class Meta:
        model = C2
        fields = ["created_since", "created_until"]


class ListenerFilter(filters.FilterSet):
    created_since = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="gte"
    )
    created_until = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="lte"
    )
    c2_id = filters.NumberFilter(field_name="c2", lookup_expr="exact")

    class Meta:
        model = Listener
        fields = ["c2_id", "listener_type", "created_since", "created_until"]


class LauncherFilter(filters.FilterSet):
    created_since = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="gte"
    )
    created_until = filters.IsoDateTimeFilter(
        field_name="creation_date", lookup_expr="lte"
    )
    listener_id = filters.NumberFilter(field_name="listener", lookup_expr="exact")
    # launcher_type = filters.NumberFilter(field_name='launcher_typed', lookup_expr='exact')

    class Meta:
        model = Launcher
        fields = ["listener_id", "launcher_type", "created_since", "created_until"]
