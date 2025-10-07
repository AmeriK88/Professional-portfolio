from .models import Message 


def inbox_unread(request):
    if not request.user.is_authenticated:
        return {}

    count = Message.objects.filter(
        thread__user=request.user,
        is_read=False,
    ).exclude(sender_type="user").count()
    return {"inbox_unread_count": count}
