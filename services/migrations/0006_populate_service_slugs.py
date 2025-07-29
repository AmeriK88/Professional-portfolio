from django.db import migrations
from django.utils.text import slugify

def populate_slugs(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    for obj in Service.objects.all():
        if obj.slug:
            continue
        base = slugify(obj.title)[:50] or f"servicio-{obj.id}"
        slug = base
        i = 2
        while Service.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        obj.slug = slug
        obj.save(update_fields=["slug"])

class Migration(migrations.Migration):

    dependencies = [
        ('services', '0005_service_slug'),
    ]

    operations = [
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
    ]
