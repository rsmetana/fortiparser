
from django.urls import path
from .views import tabs_home, save_policies, save_nat, export_nat_excel

urlpatterns = [
    path("", tabs_home, name="tabs_home"),
    path("save-policies/", save_policies, name="save_policies"),
    path("save-nat/", save_nat, name="save_nat"),
    path("export-nat-excel/", export_nat_excel, name="export_nat_excel"),
]
