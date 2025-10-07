from __future__ import annotations

from typing import Any
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from .models import Thread, Message


@login_required
def thread_list(request: HttpRequest) -> HttpResponse:
    threads = (
        Thread.objects
        .filter(user=request.user)
        .select_related("order")
        .order_by("-last_message_at", "-updated_at", "-id")
    )
    return render(request, "inbox/thread_list.html", {"threads": threads})


@login_required
@require_http_methods(["GET", "POST"])
def thread_detail(request: HttpRequest, thread_id: int) -> HttpResponse:
    thread = get_object_or_404(
        Thread.objects.select_related("order"),
        pk=thread_id,
        user=request.user,
    )

    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(
                thread=thread,
                sender_type=Message.SENDER_USER,
                sender_user=request.user,
                body=body,
            )
            thread.touch()

        return redirect("inbox:thread_detail", thread_id=thread.pk)

    # GET: marcar como leídos (mensajes no del propio usuario)
    Message.objects.filter(
        thread=thread
    ).exclude(
        sender_type=Message.SENDER_USER
    ).filter(
        is_read=False
    ).update(is_read=True)

    messages_qs = (
        Message.objects
        .filter(thread=thread)
        .select_related("sender_user")
        .order_by("created_at")
    )

    return render(request, "inbox/thread_detail.html", {
        "thread": thread,
        "thread_messages": messages_qs,
    })
