from django import template

from main.dashboard_router import DashboardRouter


register = template.Library()


@register.simple_tag
def shell_route_allowed(user, route_name):
    return DashboardRouter.user_can_access_shell_route(user, route_name)


@register.simple_tag
def shell_route_denied_message(route_name):
    return DashboardRouter.shell_access_denied_message(route_name)
