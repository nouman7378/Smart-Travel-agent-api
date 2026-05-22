from django.db import migrations, models


def seed_featured_rooms(apps, schema_editor):
    Room = apps.get_model('api', 'Room')
    Hotel = apps.get_model('api', 'Hotel')

    for hotel in Hotel.objects.all():
        if Room.objects.filter(hotel=hotel, is_featured=True).exists():
            continue

        first_room = Room.objects.filter(
            hotel=hotel,
            is_active=True,
            available_rooms__gt=0,
        ).order_by('price_per_night').first()

        if first_room:
            first_room.is_featured = True
            first_room.save(update_fields=['is_featured'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_hotel_is_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='is_featured',
            field=models.BooleanField(default=False, help_text='Is this a featured room?'),
        ),
        migrations.RunPython(seed_featured_rooms, migrations.RunPython.noop),
    ]