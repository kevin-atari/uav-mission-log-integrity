from datetime import datetime

from django.shortcuts import render

from .utils import list_flight_ids, list_versions
from services.verify_flight import verify_flight_against_chain


def flights_page(request):
    flights = list_flight_ids()
    return render(request, "flights.html", {"flights": flights})


def flight_versions_page(request, flight_id: str):
    key, versions = list_versions(flight_id)

    version_count = len(versions)
    latest_version_time = None
    if versions:
        latest = versions[0]
        latest_version_time = latest.get("last_modified")

    #Verification against chain
    verify_summary = None
    verify_rows = []

    if request.GET.get("verify") == "1":
        verify_summary, verify_rows = verify_flight_against_chain(flight_id)

    context = {
        "flight_id": flight_id,
        "key": key,
        "versions": versions,
        "version_count": version_count,
        "latest_version_time": latest_version_time,
        "verify_summary": verify_summary,
        "verify_rows": verify_rows,
    }
    return render(request, "versions.html", context)


def home(request):
    return render(request, "home.html")
