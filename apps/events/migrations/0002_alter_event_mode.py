from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="mode",
            field=models.CharField(
                choices=[
                    ("In-person", "Presencial"),
                    ("Online", "En línea"),
                    ("Virtual", "Virtual"),
                    ("Hybrid", "Híbrido"),
                ],
                max_length=20,
                verbose_name="modalidad",
            ),
        ),
    ]
