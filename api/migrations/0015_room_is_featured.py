from django.db import migrations, models


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
    ]