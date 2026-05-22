from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_switch_image_fields_to_s3_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotel',
            name='is_featured',
            field=models.BooleanField(default=False, help_text='Is this a featured hotel?'),
        ),
    ]
