from django.contrib import admin
from django.urls import path
from myapp1 import views

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('', views.upload_file,name='upload_file'), 
   # path('upload/', views.upload_file, name='upload_file'),
    path('display_data/', views.display_data, name='display_data'),
    path('send_messages/', views.send_messages, name='send_messages'),
    path('download_report/', views.download_report, name='download_report'),
    path('download_not_on_whatsapp_file/', views.download_not_on_whatsapp_file, name='download_not_on_whatsapp_file'),
]
