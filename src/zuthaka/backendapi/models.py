from django.db import models
from django.contrib.auth.models import User
import datetime
import uuid


class C2Type(models.Model):
    documentation = models.CharField(max_length=250, blank=True)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250,  blank=True)
    module_name = models.CharField(max_length=250)
    module_path = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class C2TypeOption(models.Model):
    c2_type = models.ForeignKey(
        C2Type, related_name='options', on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    example = models.CharField(max_length=250, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    field_type = models.CharField(max_length=250)
    required = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class C2(models.Model):
    c2_type = models.ForeignKey(C2Type, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return 'C2 type:{}'.format(self.c2_type)


class C2Option(models.Model):
    name = models.CharField(max_length=60)
    value = models.CharField(max_length=60)
    c2 = models.ForeignKey(C2, related_name='options',
                           on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class ListenerType(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250,  blank=True, null=True)
    c2_type = models.ForeignKey(C2Type, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class ListenerTypeOption(models.Model):
    listener_type = models.ForeignKey(
        ListenerType, related_name='options', on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    example = models.CharField(max_length=250, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    field_type = models.CharField(max_length=250)
    required = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class Listener(models.Model):
    listener_type = models.ForeignKey(ListenerType, on_delete=models.CASCADE)
    listener_internal_id = models.CharField(max_length=250, blank=True, null=True)
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    c2 = models.ForeignKey(C2, on_delete=models.CASCADE)

    def __str__(self):
        return "instance of {}".format(self.listener_type)


class ListenerOption(models.Model):
    name = models.CharField(max_length=60)
    value = models.CharField(max_length=60)
    listener = models.ForeignKey(
        Listener, related_name='options', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LauncherType(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250,  blank=True, null=True)
    c2_type = models.ForeignKey(C2Type, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LauncherTypeOption(models.Model):
    launcher_type = models.ForeignKey(
        LauncherType, related_name='options', on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    example = models.CharField(max_length=250, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    field_type = models.CharField(max_length=250)
    required = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class Launcher(models.Model):
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    listener = models.ForeignKey(Listener, on_delete=models.CASCADE)
    launcher_type = models.ForeignKey(LauncherType, on_delete=models.CASCADE)
    launcher_internal_id = models.CharField(max_length=250, blank=True, null=True)
    launcher_file = models.FileField(
        upload_to='payloads')

    def __str__(self):
        return 'pk: {}'.format(self.pk)


class LauncherOption(models.Model):
    name = models.CharField(max_length=60)
    value = models.CharField(max_length=60)
    launcher = models.ForeignKey(
        Launcher, related_name='options', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Agent(models.Model):
    c2 = models.ForeignKey(C2, on_delete=models.CASCADE)
    listener = models.ForeignKey(Listener, on_delete=models.CASCADE)
    first_conection = models.DateTimeField(default=datetime.datetime.now)
    last_conection = models.DateTimeField(default=datetime.datetime.now)
    username = models.CharField(max_length=250, blank=True, null=True)
    hostname = models.CharField(max_length=250, blank=True, null=True)
    internal_id = models.CharField(max_length=250, blank=True, null=True)
    shell_type = models.CharField(max_length=250, blank=True, null=True)
    active = models.BooleanField(default=False)


class AgentTask(models.Model):
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    command_ref = models.CharField(
        max_length=100, blank=True, unique=True, default=uuid.uuid4)
    completed = models.BooleanField(default=False)
    upload = models.BooleanField(default=False)
    transition_file = models.FileField(blank=True, null=True)


class AgentTaskEvent(models.Model):
    task = models.ForeignKey(AgentTask, related_name='events', on_delete=models.CASCADE)
    interaction_date = models.DateTimeField(default=datetime.datetime.now)
    content = models.JSONField(blank=True, null=True)
    transition_file = models.FileField(blank=True, null=True)

class Project(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250,  blank=True, null=True)
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    update_date = models.DateTimeField(default=datetime.datetime.now)
    documentation = models.CharField(
        max_length=250, blank=True, null=True)  # This may need to be a file
    admins = models.ManyToManyField(User, related_name='admins')
    operators = models.ManyToManyField(User, related_name='operators')
    viewers = models.ManyToManyField(User, related_name='viewers')

    def __str__(self):
        return self.name
