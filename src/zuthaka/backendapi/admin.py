from django.contrib import admin
from .models import C2Type, C2TypeOption, C2, C2Option, AgentTask, AgentTaskEvent

admin.site.register(C2Type)
admin.site.register(C2TypeOption)
admin.site.register(C2)
admin.site.register(C2Option)
admin.site.register(AgentTask)
admin.site.register(AgentTaskEvent)
