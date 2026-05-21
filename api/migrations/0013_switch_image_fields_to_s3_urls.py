# Generated migration: CloudinaryField -> CharField for S3 URL storage

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_remove_car_car_image_url_remove_hotel_image_url_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotel',
            name='image',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='room',
            name='room_image',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='car',
            name='car_image',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='package',
            name='hotel_image',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
