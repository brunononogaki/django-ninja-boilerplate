from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_passwordresettoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='uuiduser',
            name='avatar_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
