# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-09-25 19:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stylemuzeapp', '0010_user_gcm_reg_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.User')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.PhotoItem')),
            ],
        ),
    ]
