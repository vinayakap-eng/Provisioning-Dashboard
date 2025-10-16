"""
URL configuration for iot_dashboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from multi_devices.views import (
    dashboard_view,
    testcases_view,
    scan_devices_view,
    provisioning_request_view,
    run_tests_view,  # ✅ add this
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('provisioning/tests/', testcases_view, name='testcases'),
    path('provisioning/scan/', scan_devices_view, name='scan_devices'),
    path('provisioning/request/', provisioning_request_view, name='provisioning_request'),
    path('run-tests/', run_tests_view, name='run_tests'),  # ✅ fixed here
]
