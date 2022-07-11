import inspect
import backendapi.services.c2 as c2
from backendapi import models
from backendapi.utils import collect_classes, collect_handlers

def persist_c2_types(handler):
    c2_handlers = collect_classes(handler, c2.C2)
    if len(c2_handlers) > 1:
        raise ValueError('More than one C2 defined in a module')
    c2_handler = c2_handlers[0]
    print('[-] c2_handler  collected:', c2_handler)
    c2_type = models.C2Type()
    c2_type.documentation = c2_handler.documentation
    c2_type.name = c2_handler.name
    c2_type.description = c2_handler.description
    c2_type.module_name = c2_handler.__module__
    c2_type.module_path = inspect.getabsfile(c2_handler)

    c2_type.save()

    for registered_option in c2_handler.registered_options:
        c2_type_option = models.C2TypeOption()
        c2_type_option.c2_type = c2_type
        c2_type_option.name = registered_option.name
        c2_type_option.example = registered_option.example
        c2_type_option.description = registered_option.description
        c2_type_option.field_type = registered_option.field_type
        c2_type_option.required = registered_option.required
        c2_type_option.save()

    return c2_type

def persist_listener_types(handler, c2_type):

    listener_handlers = collect_classes(handler, c2.ListenerType)
    print('[-] Listeners collected:', listener_handlers)
    listener_daos = []
    for listener_handler in listener_handlers:
        listener_type = models.ListenerType()
        listener_type.name = listener_handler.name
        listener_type.description = listener_handler.description
        listener_type.c2_type = c2_type
        listener_type.save()
        listener_daos.append(listener_type)

        for registered_option in listener_handler.registered_options:
            listener_type_option = models.ListenerTypeOption()
            listener_type_option.listener_type = listener_type
            listener_type_option.name = registered_option.name
            listener_type_option.example = registered_option.example
            listener_type_option.description = registered_option.description
            listener_type_option.field_type = registered_option.field_type
            listener_type_option.required = registered_option.required
            listener_type_option.save()

    return listener_daos

def persist_launcher_types(handler, c2_type):

    launcher_handlers = collect_classes(handler, c2.LauncherType)
    print('[-] Launchers collected:', launcher_handlers)
    launcher_daos = []
    for launcher_handler in launcher_handlers:
        launcher_type = models.LauncherType()
        launcher_type.name = launcher_handler.name
        launcher_type.description = launcher_handler.description
        launcher_type.c2_type = c2_type
        launcher_type.save()
        launcher_daos.append(launcher_type)

        for registered_option in launcher_handler.registered_options:
            launcher_type_option = models.LauncherTypeOption()
            launcher_type_option.launcher_type = launcher_type
            launcher_type_option.name = registered_option.name
            launcher_type_option.example = registered_option.example
            launcher_type_option.description = registered_option.description
            launcher_type_option.field_type = registered_option.field_type
            launcher_type_option.required = registered_option.required
            launcher_type_option.save()

    return launcher_daos


def persist_postexploitation_types(handler, c2_type):
    post_exploits = collect_classes(handler, c2.PostExploitationType)
    print('[-] Post-exploitation types collected:', post_exploits)
    post_exploit_daos = []
    for post_exploit in post_exploits:
        post_exploit_type = models.PostExploitationType()
        post_exploit_type.name = post_exploit.name
        post_exploit_type.description = post_exploit.description
        post_exploit_type.c2_type = c2_type
        post_exploit_type.save()
        post_exploit_daos.append(post_exploit_type)

        for registered_option in post_exploit.registered_options:
            post_exploit_type_option = models.PostExploitTypeOption()
            post_exploit_type_option.post_exploit_type = post_exploit
            post_exploit_type_option.name = registered_option.name
            post_exploit_type_option.example = registered_option.example
            post_exploit_type_option.description = registered_option.description
            post_exploit_type_option.field_type = registered_option.field_type
            post_exploit_type_option.required = registered_option.required
            post_exploit_type_option.save()
    return post_exploit_daos


def run():
    handlers_module = collect_handlers()

    print('[*]: handlers_module:', handlers_module)
    for handler in handlers_module:
        print('[*] loading handler: ', handler)
        c2_type = persist_c2_types(handler)
        print('[*] c2 persisted: ', c2_type)
        listeners = persist_listener_types(handler, c2_type)
        print('[*] Listener Persisted: ', listeners)
        launchers = persist_launcher_types(handler, c2_type)
        print('[*] Launchers Persisted: ', launchers)

