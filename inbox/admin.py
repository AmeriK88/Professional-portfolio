from django.contrib import admin
from .models import Thread, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender_type", "sender_user", "body", "is_read", "created_at")
    can_delete = False

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "subject", "last_message_at", "updated_at")
    search_fields = ("order__number", "user__username", "user__email", "subject")
    readonly_fields = ("created_at", "updated_at", "last_message_at")
    inlines = [MessageInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender_type", "sender_user", "is_read", "created_at")
    list_filter = ("sender_type", "is_read")
    search_fields = ("thread__order__number", "body")
    readonly_fields = ("created_at",)
