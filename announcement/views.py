from django.shortcuts import render
from .serializers import AnnouncementSerializer
from .models import Announcement
from rest_framework import viewsets
from user.permission import IsAdminOrReadOnly

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminOrReadOnly]