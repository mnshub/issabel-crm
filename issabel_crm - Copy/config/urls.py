"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from crm import views
from django.conf.urls.static import static

urlpatterns = [
    # Core Admin Dashboard Access Node
    path('admin/', admin.site.urls),
    
    # Core Operational Decoupled Media & Dialing Endpoints
    path('call/play/<int:log_id>/', views.play_recording, name='play_recording'),
    path('call/dial/<str:phone_number>/', views.click_to_dial, name='click_to_dial'),
    
    # CRM Master Record Lookup Mutation Endpoints
    path('call/customer/lookup/<str:phone_number>/', views.customer_lookup, name='customer_lookup'),
    path('call/customer/save/', views.save_customer, name='save_customer'),
    
    # React Decoupled SPA Feed Sync Pipelines
    path('api/dashboard/data/', views.api_dashboard_data, name='api_dashboard_data'),
    
    # Secure Stateless API Session Authentication Enforcers
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),
    path('api/auth/status/', views.api_auth_status, name='api_auth_status'),


    path('api/call/wrapup/save/', views.save_wrapup, name='save_wrapup'),
]

# Development Environment Media Cache Shards Mount
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)