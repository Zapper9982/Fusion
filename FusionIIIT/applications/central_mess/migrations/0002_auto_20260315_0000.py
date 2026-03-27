# Generated manually for mess workflow completion.

import applications.central_mess.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic_information', '0001_initial'),
        ('central_mess', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeregistrationRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('end_date', models.DateField()),
                ('deregistration_remark', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accept', 'Accepted'), ('reject', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='academic_information.student')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='PaymentUpdateRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_date', models.DateField()),
                ('amount', models.PositiveIntegerField(default=0)),
                ('Txn_no', models.CharField(max_length=100)),
                ('img', models.FileField(blank=True, null=True, upload_to='central_mess/payment_updates/')),
                ('update_remark', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accept', 'Accepted'), ('reject', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='academic_information.student')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='RegistrationRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mess_option', models.CharField(choices=[('mess1', 'Veg_mess'), ('mess2', 'Non_veg_mess')], max_length=20)),
                ('start_date', models.DateField()),
                ('payment_date', models.DateField()),
                ('amount', models.PositiveIntegerField(default=0)),
                ('Txn_no', models.CharField(max_length=100)),
                ('img', models.FileField(blank=True, null=True, upload_to='central_mess/registration_receipts/')),
                ('registration_remark', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accept', 'Accepted'), ('reject', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='academic_information.student')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddField(
            model_name='feedback',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='payments',
            name='Txn_no',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='payments',
            name='payment_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payments',
            name='payment_month',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='payments',
            name='payment_year',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payments',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accept', 'Accepted'), ('reject', 'Rejected'), ('cancelled', 'Cancelled')], default='accept', max_length=20),
        ),
        migrations.AddField(
            model_name='rebate',
            name='rebate_remark',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='special_request',
            name='special_request_remark',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='feedback_type',
            field=models.CharField(choices=[('maintenance', 'Maintenance'), ('food', 'Food'), ('cleanliness', 'Cleanliness & Hygiene'), ('others', 'Others')], max_length=20),
        ),
        migrations.AlterField(
            model_name='payments',
            name='year',
            field=models.IntegerField(default=applications.central_mess.models.current_year),
        ),
    ]
