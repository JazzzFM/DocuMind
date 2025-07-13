from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    DocumentProcessView, 
    DocumentSearchView, 
    DocumentBatchProcessView,
    SystemStatusView,
    DocumentTypesView,
    StatisticsView
)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('documents/process/', DocumentProcessView.as_view(), name='document_process'),
    path('documents/search/', DocumentSearchView.as_view(), name='document_search'),
    path('documents/batch/', DocumentBatchProcessView.as_view(), name='document_batch_process'),
    path('system/status/', SystemStatusView.as_view(), name='system_status'),
    path('system/document-types/', DocumentTypesView.as_view(), name='document_types'),
    path('system/statistics/', StatisticsView.as_view(), name='statistics'),
]
