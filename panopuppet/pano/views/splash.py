import pytz

from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render

from panopuppet.pano.models import LdapGroupPermissions
from panopuppet.pano.puppetdb.puppetdb import set_server
from panopuppet.pano.settings import AVAILABLE_SOURCES, AUTH_METHOD, ENABLE_PERMISSIONS

__author__ = 'etaklar'


def splash(request):
    context = {'timezones': pytz.common_timezones,
               'SOURCES': AVAILABLE_SOURCES}
    if request.method == 'GET':
        if 'source' in request.GET:
            source = request.GET.get('source')
            set_server(request, source)
    if request.method == 'POST':
        if 'timezone' in request.POST:
            request.session['django_timezone'] = request.POST['timezone']
            return redirect(request.POST['url'])
        elif 'username' in request.POST and 'password' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username, password=password)
            next_url = False
            if 'nexturl' in request.POST:
                next_url = request.POST['nexturl']
            if user is not None:
                if user.is_active:
                    login(request, user)
                    # Work out the permissions for this user based on ldap groups
                    if AUTH_METHOD == 'ldap' and user.backend == 'django_auth_ldap.backend.LDAPBackend' and ENABLE_PERMISSIONS:
                        ldap_user = user.ldap_user
                        ldap_user_groups = ldap_user.group_dns
                        base_query = ['["and",["or"']
                        for group in ldap_user_groups:
                            results = LdapGroupPermissions.objects.filter(ldap_group_name=group)
                            if results.exists():
                                value = results.values()
                                value = value[0]['puppetdb_query']
                                base_query.append(value)
                        if len(base_query) == 1:
                            if user.is_staff or user.is_superuser:
                                request.session['permission_filter'] = False
                            else:
                                request.session['permission_filter'] = None
                        else:
                            if user.is_staff or user.is_superuser:
                                request.session['permission_filter'] = False
                            else:
                                request.session['permission_filter'] = ','.join(base_query) + ']]'

                    if next_url:
                        return redirect(next_url)
                    else:
                        return redirect('dashboard')
                else:
                    context['login_error'] = "Account is disabled."
                    context['nexturl'] = next_url
                    return render(request, 'pano/splash.html', context)
            else:
                # Return an 'invalid login' error message.
                context['login_error'] = "Invalid credentials"
                context['nexturl'] = next_url
                return render(request, 'pano/splash.html', context)
        return redirect('dashboard')

    user = request.user.username
    context['username'] = user
    return render(request, 'pano/splash.html', context)
