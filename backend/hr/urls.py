from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet, PositionViewSet,
    EmployeeViewSet, VacancyViewSet, ApplicationViewSet,
    TimeTrackingViewSet, DocumentViewSet, HRActionLogViewSet,
    PersonnelHistoryViewSet,
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='hr-department')
router.register(r'positions', PositionViewSet, basename='hr-position')
router.register(r'employees', EmployeeViewSet, basename='hr-employee')
router.register(r'vacancies', VacancyViewSet, basename='hr-vacancy')
router.register(r'applications', ApplicationViewSet, basename='hr-application')
router.register(r'time-tracking', TimeTrackingViewSet, basename='hr-timetracking')
router.register(r'documents', DocumentViewSet, basename='hr-document')
router.register(r'personnel-history', PersonnelHistoryViewSet, basename='hr-personnel-history')
router.register(r'logs', HRActionLogViewSet, basename='hr-log')

app_name = 'hr'

urlpatterns = [
    path('', include(router.urls)),
]
