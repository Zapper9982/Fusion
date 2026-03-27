# Generated manually for menu poll workflow support.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('academic_information', '0001_initial'),
        ('central_mess', '0002_auto_20260315_0000'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuPoll',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('mess_option', models.CharField(choices=[('mess1', 'Veg_mess'), ('mess2', 'Non_veg_mess')], max_length=20)),
                ('meal_time', models.CharField(blank=True, choices=[('MB', 'Monday Breakfast'), ('ML', 'Monday Lunch'), ('MD', 'Monday Dinner'), ('TB', 'Tuesday Breakfast'), ('TL', 'Tuesday Lunch'), ('TD', 'Tuesday Dinner'), ('WB', 'Wednesday Breakfast'), ('WL', 'Wednesday Lunch'), ('WD', 'Wednesday Dinner'), ('THB', 'Thursday Breakfast'), ('THL', 'Thursday Lunch'), ('THD', 'Thursday Dinner'), ('FB', 'Friday Breakfast'), ('FL', 'Friday Lunch'), ('FD', 'Friday Dinner'), ('SB', 'Saturday Breakfast'), ('SL', 'Saturday Lunch'), ('SD', 'Saturday Dinner'), ('SUB', 'Sunday Breakfast'), ('SUL', 'Sunday Lunch'), ('SUD', 'Sunday Dinner')], max_length=20, null=True)),
                ('poll_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='menu_polls_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='MenuPollOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_text', models.CharField(max_length=200)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='central_mess.menupoll')),
            ],
            options={
                'ordering': ('display_order', 'id'),
                'unique_together': {('poll', 'option_text')},
            },
        ),
        migrations.CreateModel(
            name='MenuPollVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='central_mess.menupolloption')),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='central_mess.menupoll')),
                ('student_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='academic_information.student')),
            ],
            options={
                'unique_together': {('poll', 'student_id')},
            },
        ),
    ]
