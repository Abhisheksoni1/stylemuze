# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-03-19 10:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stylemuzeapp', '0002_comment_time_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='full_name',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
