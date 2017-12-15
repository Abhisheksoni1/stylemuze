# define cron job which check expiration of feedback post of user
# if That feedback post is expired then just delete that from db also
# python manage.py crontab add to start your job
# python manage.py crontab show to show your job
# python manage.py crontab remove


from stylemuzeapp.models import PhotoItem, RetensionPolicy
from django.utils import timezone


def delete_expire_post():
    feedback_posts = PhotoItem.objects.filter(type="FeedBack")
    for feedback_post in feedback_posts:
        if(timezone.now()-feedback_post.time_created).days > feedback_post.days_to_delete:
            feedback_post.delete()
