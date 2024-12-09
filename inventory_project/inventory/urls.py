from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
#     path('signup/', views.signup, name='signup'),
    path('products/', views.product_list, name='product_list'),
    # Add more URL patterns as needed

    # Product URLs
    path('products/create/', views.product_create, name='product_create'),
    path('products/<str:pk>/', views.product_detail, name='product_detail'),
    path('products/<str:pk>/edit/', views.product_update, name='product_update'),
    path('products/<str:pk>/delete/', views.product_delete, name='product_delete'),


    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),

    # Reports
    path('reports/stock/', views.stock_report, name='stock_report'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<str:pk>/update/',
         views.category_update, name='category_update'),
    path('categories/<str:pk>/delete/',
         views.category_delete, name='category_delete'),

    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<str:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<str:pk>/update/',
         views.supplier_update, name='supplier_update'),
    path('suppliers/<str:pk>/delete/',
         views.supplier_delete, name='supplier_delete'), 
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
