from __future__ import unicode_literals

from django.db import models


class User(models.Model):
    profile_pic_url = models.CharField(max_length=1000, null=True)
    website = models.CharField(max_length=1000, null=True)
    height = models.IntegerField(null=True)
    email = models.CharField(max_length=1000, null=True)
    gender = models.BooleanField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100, null=True)
    facebook_id = models.CharField(max_length=128)
    date_registered = models.DateTimeField('date registered')
    last_login = models.DateTimeField('last login time')
    gcm_reg_id = models.CharField(max_length=1024, null=True)

    def __str__(self):
        return u"%s %s (%s)" % (self.first_name, self.last_name, self.facebook_id)


class RetensionPolicy(models.Model):
    days_to_delete_post = models.IntegerField()

    def __str__(self):
        return "DAYS CONFIGURATIONS"


class Brand(models.Model):
    logo_pic_url = models.CharField(max_length=1000)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Coupon(models.Model):
    created = models.DateTimeField('date published')
    coupon_photo = models.ImageField()
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True)
    coupon_code = models.CharField(max_length=16)
    validity = models.DateTimeField('valid till')

    def __str__(self):
        return u"%s - %s" % (unicode(self.brand), unicode(self.coupon_code))

    def __unicode__(self):
        return u"%s - %s" % (unicode(self.brand), unicode(self.coupon_code))


class PhotoItem(models.Model):
    is_bff_item = models.BooleanField()
    time_created = models.DateTimeField('date published')
    title = models.CharField(max_length=500)
    photo_url = models.CharField(max_length=1000)
    user_created = models.ForeignKey(User, on_delete=models.CASCADE)
    brand_associated = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True)
    type = models.CharField(max_length=10)
    days_to_delete = models.IntegerField(default=0)

    def __str__(self):
        return u"%s - %s" % (unicode(self.user_created), unicode(self.title))

    def __unicode__(self):
        return u"%s - %s" % (unicode(self.user_created), unicode(self.title))


class Follow(models.Model):
    follower_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_user_requested')
    following_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_user_being_followed')

    def __str__(self):
        return u"%s - %s" % (unicode(self.follower_user), unicode(self.following_user))


class BffState(models.Model):
    STATE_BFF = 1
    STATE_WAITING = 2
    state_name = models.CharField(max_length=10)
    state_num = models.IntegerField()

    def __str__(self):
        return self.state_name


class Bff(models.Model):
    follower_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_user_requested')
    following_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_user_being_bffed')
    state = models.ForeignKey(BffState, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return u"%s - %s" % (unicode(self.follower_user), unicode(self.following_user))


class Like(models.Model):
    item = models.ForeignKey(PhotoItem, on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return u"%s - %s" % (unicode(self.item), unicode(self.from_user))


class Favorite(models.Model):
    item = models.ForeignKey(PhotoItem, on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return u"%s - %s" % (unicode(self.item), unicode(self.from_user))


class Comment(models.Model):
    item = models.ForeignKey(PhotoItem, on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    time_created = models.DateTimeField('date published', null=True)  # null becasue I added this after first migration

    def __str__(self):
        return u"%s - %s" % (unicode(self.item), unicode(self.from_user))


class VoteOption(models.Model):
    VOTE_YES = 1
    VOTE_NO = 2

    vote_name = models.CharField(max_length=10)
    vote_num = models.IntegerField()

    def __str__(self):
        return unicode(self.vote_name)


class Vote(models.Model):
    item = models.ForeignKey(PhotoItem, on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote = models.ForeignKey(VoteOption, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return u"%s - %s" % (unicode(self.item.id), unicode(self.from_user))


class UploadedImage(models.Model):
    name = models.CharField(max_length=500)
    data = models.BinaryField()

    def __str__(self):
        return unicode(self.name)


class NotificationTypes(object):
    TYPE_BFF_REQUEST = 1
    TYPE_FOLLOW_NOTIFY = 2
    TYPE_LIKE = 3
    TYPE_COMMENT = 4
    TYPE_POST_VOTE = 5
    TYPE_BFF_POST = 6
    TYPES = (
        (TYPE_BFF_REQUEST, "BFF request"),
        (TYPE_FOLLOW_NOTIFY, "Start following"),
        (TYPE_LIKE, "Post like"),
        (TYPE_COMMENT, "Post comment"),
        (TYPE_POST_VOTE, "Post vote"),
        (TYPE_BFF_POST, "Bff uploaded post"),
    )


class Notifications(models.Model):
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_to_user')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_from_user')
    from_user_name = models.CharField(max_length=100, null=True)
    is_read = models.BooleanField()
    notification_type = models.IntegerField(choices=NotificationTypes.TYPES)
    date_created = models.DateTimeField('date published')
    date_readed = models.DateTimeField('date readed', null=True, blank=True)
    bff_req_object = models.ForeignKey(Bff, on_delete=models.CASCADE, null=True, blank=True)
    follow_object = models.ForeignKey(Follow, on_delete=models.CASCADE, null=True, blank=True)
    # like_object = models.ForeignKey(Like, on_delete=models.CASCADE, null=True, blank=True)
    comment_object = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    vote_object = models.ForeignKey(Vote, on_delete=models.CASCADE, null=True, blank=True)
    post_object = models.ForeignKey(PhotoItem, on_delete=models.CASCADE, null=True, blank=True)
