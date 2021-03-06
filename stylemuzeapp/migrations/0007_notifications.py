# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-04-17 20:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stylemuzeapp', '0006_auto_20160417_2351'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notifications',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_read', models.BooleanField()),
                ('notification_type', models.IntegerField(choices=[(1, 'BFF request'), (2, 'Start following'), (3, 'Post like'), (4, 'Post comment'), (5, 'Post vote'), (6, 'Bff uploaded post')])),
                ('date_created', models.DateTimeField(verbose_name='date published')),
                ('date_readed', models.DateTimeField(null=True, verbose_name='date readed')),
                ('bff_post_object', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.PhotoItem')),
                ('bff_req_object', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.Bff')),
                ('comment_object', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.Comment')),
                ('follow_object', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.Follow')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications_from_user', to='stylemuzeapp.User')),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications_to_user', to='stylemuzeapp.User')),
                ('vote_object', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stylemuzeapp.Vote')),
            ],
        ),
    ]
