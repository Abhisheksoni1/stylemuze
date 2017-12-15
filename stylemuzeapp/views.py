import json
from email.mime.text import MIMEText
import requests

from binascii import Error as binasciiError
from datetime import datetime
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.forms.models import model_to_dict
from django.conf import settings

from stylemuze.settings import DAYS_TO_DELETE
from tasks import send_mail
from stylemuzeapp.models import *
from stylemuzeapp.error_codes import ERROR_CODES

POST_FILE_FORMAT = "post_image_{user_id}_{date}"
MAX_POST = 10

def _send_notification(to_user, from_user, from_user_name,
                       notification_type, **kwargs):
    # Adding notification
    notification = Notifications(to_user=to_user,
                                 from_user=from_user,
                                 from_user_name=from_user_name,
                                 is_read=False,
                                 notification_type=notification_type,
                                 date_created=datetime.now(),
                                 **kwargs)
    notification.save()

    if to_user.gcm_reg_id is None or 0 == len(to_user.gcm_reg_id):
        return

    # Sending GCM notification
    unread_count = Notifications.objects.filter(Q(to_user_id=to_user.id) & Q(is_read=False)).count()
    notify_data = {"to": to_user.gcm_reg_id,
                   "data": {
                       "count": unread_count,
                       "name": from_user_name,
                       "type": notification_type
                   }
                   }
    headers = {"Authorization": "key=" + settings.GCM_API_KEY,
               "Content-Type": "application/json"}

    requests.post(settings.GCM_URL, data=json.dumps(notify_data), headers=headers)


def _create_user(user_dict):
    user = User(facebook_id=user_dict["facebook_id"], gender=True, first_name='',
                last_name='', date_registered=timezone.now(), last_login=timezone.now())
    user_fields = [field.name for field in user._meta.fields]
    user_fields.remove('id')
    user_fields.remove('date_registered')
    user_fields.remove('last_login')
    user_fields.remove('facebook_id')
    # filling the given properties
    [setattr(user, field, user_dict[field]) for field in user_dict.keys() if field in user_fields]
    user.full_name = user.first_name + u" " + user.last_name
    user.save()


def __create_json_dict(error_code, **kwargs):
    send_dict = {"error_code": error_code}
    send_dict.update(kwargs)
    return send_dict


def __make_feed_items(items):
    items_dict = [model_to_dict(item) for item in items]
    yes_vote_id = VoteOption.objects.get(vote_num=VoteOption.VOTE_YES).id
    no_vote_id = VoteOption.objects.get(vote_num=VoteOption.VOTE_NO).id
    for item in items_dict:
        if item['is_bff_item']:
            item['yes_users'] = [i.from_user_id for i in
                                 Vote.objects.filter(Q(item_id=item['id']) & Q(vote_id=yes_vote_id))]
            item['no_users'] = [i.from_user_id for i in
                                Vote.objects.filter(Q(item_id=item['id']) & Q(vote_id=no_vote_id))]
            item['user_voted'] = True if Vote.objects.filter(
                Q(item_id=item['id']) & Q(from_user_id=user.id)) else False
        else:
            item['likes'] = [i.from_user_id for i in Like.objects.filter(Q(item_id=item['id']))]
            item['user_liked'] = True if Like.objects.filter(item_id=item['id'],
                                                             from_user_id=user.id).count() > 0 else False
            item['user_favorite'] = True if Favorite.objects.filter(item_id=item['id'],
                                                                    from_user_id=user.id).count() > 0 else False
        item['comments_count'] = Comment.objects.filter(Q(item_id=item['id'])).count()
        item['logo_pic_url'] = Brand.objects.get(id=item['brand_associated']).logo_pic_url
        user = User.objects.get(id=item['user_created'])
        item['user_data'] = {'first_name': user.first_name,
                             'last_name': user.last_name,
                             'profile_pic_url': user.profile_pic_url}
    return items_dict


@csrf_exempt
def login(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(facebook_id=request.POST["facebook_id"])
    except KeyError:
        raise Http404("No facebook ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    response = JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, **model_to_dict(user)))
    user.last_login = timezone.now()
    user.save()
    return response


@csrf_exempt
def register(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user_dict = json.loads(request.body)
        user = User.objects.get(facebook_id=user_dict["facebook_id"])
    except ValueError:
        raise Http404("Not valid JSON")
    except KeyError:
        raise Http404("No facebook ID")
    except User.DoesNotExist:
        _create_user(user_dict)
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_ALREADY_EXISTS))


@csrf_exempt
def get_feed_update(request):
    if request.method == 'POST':
        try:
            user = User.objects.get(facebook_id=request.POST["facebook_id"])
            bff_state = BffState.objects.get(state_num=BffState.STATE_BFF)
            bffs = Bff.objects.filter(Q(follower_user_id=user.id) & Q(state=bff_state))
            following = Follow.objects.filter(Q(follower_user_id=user.id))
            query = Q(user_created_id=user.id)

            for i in bffs:
                query |= Q(user_created_id=i.following_user.id)
            for i in following:
                query |= Q(user_created_id=i.following_user.id)
            #
            items = PhotoItem.objects.filter(query).order_by('-time_created')
            # check that last_post parameter is in request or not
            if not request.POST.get('last_item'):
                raise Http404("Invalid Request type")
            last_post = int(request.POST['last_item'])
            total_item = items.count()
            diff_item = total_item - last_post

            # also check condition if user on single post then it should not add more items
            if total_item > last_post:
                if total_item > last_post + MAX_POST:
                    items = items[last_post: last_post + MAX_POST]
                else:
                    # as to get the latest post when we scroll down newest first
                    items = items[:diff_item]
            else:
                items = []

        except KeyError:
            raise Http404("No facebook ID")
        except User.DoesNotExist:
            return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
        except BffState.DoesNotExist:
            return JsonResponse(__create_json_dict(ERROR_CODES.EC_BFF_STATE_OBJECT_NOT_FOUND))

        items_dict = __make_feed_items(items)
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=items_dict))
    else:
        raise Http404("No Post Request")


@csrf_exempt
def get_feed(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(facebook_id=request.POST["facebook_id"])
        bff_state = BffState.objects.get(state_num=BffState.STATE_BFF)
        bffs = Bff.objects.filter(Q(follower_user_id=user.id) & Q(state=bff_state))
        following = Follow.objects.filter(Q(follower_user_id=user.id))

        query = Q(user_created_id=user.id)

        for i in bffs:
            query |= Q(user_created_id=i.following_user.id)
        for i in following:
            query |= Q(user_created_id=i.following_user.id)
        items = PhotoItem.objects.filter(query).order_by('-time_created')

        # As we need to limit our feed items(As per later aspect)
        if items.count() > MAX_POST:
            items = items[:MAX_POST]

    except KeyError:
        raise Http404("No facebook ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except BffState.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_BFF_STATE_OBJECT_NOT_FOUND))

    items_dict = __make_feed_items(items)
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=items_dict))


@csrf_exempt
def get_single_post(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
        user = User.objects.get(facebook_id=request.POST["facebook_id"])
    except KeyError:
        raise Http404("No facebook ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))
    # We only have one post in our list so we do so !
    item = __make_feed_items(post)[0]
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, **item))


@csrf_exempt
def get_users(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")

        ids = request.POST["user_ids"].split(';')

        query = Q()
        for id in ids:
            query |= Q(pk=id)
        users = User.objects.filter(query)
        from_user = User.objects.get(pk=request.POST["user_id"])
    except KeyError:
        raise Http404("No user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    items = []
    for user in users:
        current_dict = model_to_dict(user)

        bff_status = Bff.objects.filter(Q(follower_user_id=from_user.id) & Q(following_user_id=user.id))
        current_dict["bff_state"] = bff_status[0].state.state_num if bff_status.count() > 0 else 0

        following_status = Follow.objects.filter(Q(follower_user_id=from_user.id) & Q(following_user_id=user.id))
        current_dict["is_following"] = True if following_status.count() > 0 else False

        items.append(current_dict)
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=items))


@csrf_exempt
def get_brands(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")

        ids = request.POST["brands_ids"].split(';')
        query = Q()
        for id in ids:
            query |= Q(pk=id)
        brands = Brand.objects.filter(query)
    except KeyError:
        # return all brands
        brands = Brand.objects.all()
    except Brand.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_BRAND_NOT_FOUND))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(brand) for brand in brands]))


@csrf_exempt
def get_user_posts(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        items = PhotoItem.objects.filter(Q(user_created_id=user.id)).order_by('-time_created')
    except KeyError:
        raise Http404("No user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item) for item in items]))


@csrf_exempt
def get_brand_posts(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        brand = Brand.objects.get(pk=request.POST["brand_id"])
        items = PhotoItem.objects.filter(Q(brand_assosiated_id=brand.id) & Q(is_bff_item=False)).order_by(
            '-time_created')
    except KeyError:
        raise Http404("No brand ID")
    except Brand.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item) for item in items]))


@csrf_exempt
def get_user_favorites(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        items = Favorite.objects.filter(Q(from_user_id=user.id))
    except KeyError:
        raise Http404("No user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item.item) for item in items]))


@csrf_exempt
def get_user_details(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        req_user = User.objects.get(pk=request.POST["req_user_id"])
        bff_state = BffState.objects.get(state_num=BffState.STATE_BFF)
        bffs = Bff.objects.filter(Q(following_user_id=user.id) & Q(state=bff_state))
        followers = Follow.objects.filter(Q(following_user_id=user.id))
        following = Follow.objects.filter(Q(follower_user_id=user.id))
        is_bff = Bff.objects.filter(
            Q(following_user_id=req_user.id) & Q(follower_user_id=user.id) & Q(state=bff_state)).count() > 0
    except KeyError:
        raise Http404("No facebook ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, bffs=[model_to_dict(item) for item in bffs],
                                           followers=[model_to_dict(item) for item in followers],
                                           following=[model_to_dict(item) for item in following],
                                           is_bff=is_bff,
                                           user=model_to_dict(user)))


@csrf_exempt
def vote_yes(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
    except KeyError:
        raise Http404("No user ID or post ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))

    try:
        yes_vote = VoteOption.objects.get(vote_num=VoteOption.VOTE_YES)
        vote = Vote(item=post, from_user=user, vote=yes_vote)
        vote.save()
    except VoteOption.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_ERROR_GETTING_VOTE_OPTION_OBJ))
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_VOTE_OBJ))

    # Adding notification
    _send_notification(post.user_created, user, user.full_name, NotificationTypes.TYPE_POST_VOTE,
                       vote_object=vote, post_object=post)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def vote_no(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
    except KeyError:
        raise Http404("No user ID or post ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))

    try:
        no_vote = VoteOption.objects.get(vote_num=VoteOption.VOTE_NO)
        vote = Vote(item=post, from_user=user, vote=no_vote)
        vote.save()
    except VoteOption.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_ERROR_GETTING_VOTE_OPTION_OBJ))
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_VOTE_OBJ))

    # Adding notification
    _send_notification(post.user_created, user, user.full_name, NotificationTypes.TYPE_POST_VOTE,
                       vote_object=vote, post_object=post)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def get_item_comments(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
    except KeyError:
        raise Http404("No post ID")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))

    comments = Comment.objects.filter(Q(item=post))
    return JsonResponse(
        __create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(comment) for comment in comments]))


@csrf_exempt
def get_item_likes(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
    except KeyError:
        raise Http404("No post ID")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))

    likes = Like.objects.filter(Q(item=post))
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(like) for like in likes]))


def _remove_like(user, post):
    likes = Like.objects.filter(item=post, from_user=user)
    for like in likes:
        like.delete()
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


def _add_like(user, post):
    if Like.objects.filter(item=post, from_user=user).count() > 0:
        # Like already exists
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))
    try:
        like_obj = Like(item=post, from_user=user)
        like_obj.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_LIKE_OBJ))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def change_like(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
        user = User.objects.get(pk=request.POST["user_id"])
        is_add = request.POST["is_add"] == "1"
    except KeyError:
        raise Http404("No post ID or user ID")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    if is_add:
        return _add_like(user, post)
    else:
        return _remove_like(user, post)


def _remove_favorite(user, post):
    favorites = Favorite.objects.filter(item=post, from_user=user)
    for favorite in favorites:
        favorite.delete()
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


def _add_favorite(user, post):
    if Favorite.objects.filter(item=post, from_user=user).count() > 0:
        # Favorite already exists
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))
    try:
        favorite_obj = Favorite(item=post, from_user=user)
        favorite_obj.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_FAVORITE_OBJ))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def change_favorite(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
        user = User.objects.get(pk=request.POST["user_id"])
        is_add = request.POST["is_add"] == "1"
    except KeyError:
        raise Http404("No post ID or user ID")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    if is_add:
        return _add_favorite(user, post)
    else:
        return _remove_favorite(user, post)


@csrf_exempt
def add_comment(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        post = PhotoItem.objects.get(pk=request.POST["post_id"])
        user = User.objects.get(pk=request.POST["user_id"])
        comment = request.POST["comment"]

    except KeyError:
        raise Http404("No post ID, user ID or comment")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    try:
        comment_obj = Comment(item=post, from_user=user,
                              comment=comment, time_created=datetime.now())
        comment_obj.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_COMMENT_OBJ))

    # Adding notification if the post don't belong to the commented user
    if user != post.user_created:
        _send_notification(post.user_created, user, user.full_name, NotificationTypes.TYPE_COMMENT,
                           comment_object=comment_obj, post_object=post)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def upload_post(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        brand = Brand.objects.get(pk=request.POST["brand_id"])
        is_bff = request.POST["is_bff"] == '1'
        title = request.POST["description"]
        image_b64 = request.POST["imageb64"]
    except KeyError:
        raise Http404("no user ID or imageb64")
    except PhotoItem.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_POST_NOT_EXISTS))
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    try:
        image_data = image_b64.decode("base64")
        image_file_name = POST_FILE_FORMAT.format(user_id=user.id, date=datetime.now().strftime("%y_%m_%d__%H_%M_%S"))
    except binasciiError:
        raise Http404("Invalid base64")

    try:
        image = UploadedImage(name=image_file_name, data=image_data)
        image.save()
    except IOError:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_SAVE_IMAGE_BINARY))

    try:
        type = request.POST['type']
        post_obj = PhotoItem(is_bff_item=is_bff, time_created=datetime.now(), title=title,
                             photo_url="/get_image/" + image_file_name,
                             user_created=user, brand_associated=brand, type=type)
        if type == "FeedBack":
            post_obj.days_to_delete = DAYS_TO_DELETE
        elif type == "Coupon":
            body = MIMEText('<p>Hello {}\n\n</p>'.format(user.first_name) + '<p><img src="cid:myimage" /></p>',
                            _subtype='html')
            send_mail.delay(brand, body, user.email)
        post_obj.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CREATE_PHOTOITEM_OBJ))

    # Creating notifications to all user's BFFs
    if is_bff:
        for bff_obj in Bff.objects.filter(following_user=user):
            _send_notification(bff_obj.follower_user, user, user.full_name, NotificationTypes.TYPE_BFF_POST,
                               post_object=post_obj)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def change_image(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        image_b64 = request.POST["imageb64"]

    except KeyError:
        raise Http404("no user ID or imageb64")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    try:
        image_data = image_b64.decode("base64")
        image_file_name = POST_FILE_FORMAT.format(user_id=user.id, date=datetime.now().strftime("%y_%m_%d__%H_%M_%S"))
    except binasciiError:
        raise Http404("Invalid base64")

    try:
        image = UploadedImage(name=image_file_name, data=image_data)
        image.save()
    except IOError:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_SAVE_IMAGE_BINARY))

    try:
        user.profile_pic_url = "/get_image/" + image_file_name
        user.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_CHANGE_USER_IMAGE_URL))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, **model_to_dict(user)))


@csrf_exempt
def search_user(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        search_string = request.POST["search_string"]
        unlimited = request.POST["unlimited"] == '1'
    except KeyError:
        raise Http404("no user ID or search string")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    users = User.objects.filter((Q(first_name__istartswith=search_string) |
                                 Q(last_name__istartswith=search_string) |
                                 Q(full_name__istartswith=search_string)) & ~Q(id=user.id))

    if not unlimited:
        users = users[:15]  # Maximum if 15 users if not flagged as unlimited

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item) for item in users]))


@csrf_exempt
def search_brand(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        search_string = request.POST["search_string"]
        unlimited = request.POST["unlimited"] == '1'
    except KeyError:
        raise Http404("no user ID or search string")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    brnads = Brand.objects.filter(Q(name__istartswith=search_string))

    if not unlimited:
        brnads = brnads[:15]  # Maximum if 15 users if not flagged as unlimited

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item) for item in brnads]))


@csrf_exempt
def add_bff(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        from_user = User.objects.get(pk=request.POST["from_user_id"])
        to_user = User.objects.get(pk=request.POST["to_user_id"])
    except KeyError:
        raise Http404("no from user ID or to user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    try:
        bff_obj = BffState.objects.get(state_num=BffState.STATE_BFF)
    except BffState.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_BFF_STATE_OBJECT_NOT_FOUND))

    if Bff.objects.filter(Q(follower_user_id=from_user.id) & Q(following_user_id=to_user.id)).count() > 0:
        # Already BFF
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))

    try:
        bff = Bff(follower_user=from_user, following_user=to_user, state=bff_obj)
        bff.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_SAVE_BFF))

    # Adding notification
    _send_notification(to_user, from_user, from_user.full_name, NotificationTypes.TYPE_BFF_REQUEST,
                       bff_req_object=bff)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def remove_bff(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        from_user = User.objects.get(pk=request.POST["from_user_id"])
        to_user = User.objects.get(pk=request.POST["to_user_id"])
        bff = Bff.objects.filter(follower_user=from_user, following_user=to_user)
    except KeyError:
        raise Http404("no from user ID or to user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except Bff.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_BFF_OBJECT_NOT_FOUND))

    try:
        for bff_obj in bff:
            bff_obj.delete()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_DELETE_BFF))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def add_follow(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        from_user = User.objects.get(pk=request.POST["from_user_id"])
        to_user = User.objects.get(pk=request.POST["to_user_id"])
    except KeyError:
        raise Http404("no from user ID or to user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    if Follow.objects.filter(Q(follower_user_id=from_user.id) & Q(following_user_id=to_user.id)).count() > 0:
        # Already Follow
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))

    try:
        follow = Follow(follower_user=from_user, following_user=to_user)
        follow.save()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_SAVE_FOLLOW))

    # Adding notification
    _send_notification(to_user, from_user, from_user.full_name, NotificationTypes.TYPE_FOLLOW_NOTIFY,
                       follow_object=follow)

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def remove_follow(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        from_user = User.objects.get(pk=request.POST["from_user_id"])
        to_user = User.objects.get(pk=request.POST["to_user_id"])
        follow = Follow.objects.filter(follower_user=from_user, following_user=to_user)
    except KeyError:
        raise Http404("no from user ID or to user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))
    except Follow.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_FOLLOW_OBJECT_NOT_FOUND))

    try:
        for follow_obj in follow:
            follow_obj.delete()
    except Exception:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_CANT_DELETE_FOLLOW))

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


def get_image(request, name):
    try:
        if request.method != 'GET':
            raise Http404("No GET requst")
        image = UploadedImage.objects.get(name=name)
    except UploadedImage.DoesNotExist:
        raise Http404("Image not found")

    return HttpResponse(image.data, content_type="image/jpeg")


@csrf_exempt
def get_notifications(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
    except KeyError:
        raise Http404("no from user ID or to user ID")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    items = Notifications.objects.filter(Q(to_user=user.id) & Q(is_read=False)).order_by('-date_created')

    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS, items=[model_to_dict(item) for item in items]))


@csrf_exempt
def update_gcm_id(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        user = User.objects.get(pk=request.POST["user_id"])
        gcm_reg_id = request.POST["gcm_reg"]
    except KeyError:
        raise Http404("no user ID or GCM reg id")
    except User.DoesNotExist:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_USER_NOT_EXISTS))

    if user.gcm_reg_id == gcm_reg_id:
        return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))

    # Removing from old users the gcm_reg_id (it identify device)
    old_users_gcm = User.objects.filter(gcm_reg_id=gcm_reg_id)
    for u in old_users_gcm:
        u.gcm_reg_id = None
        u.save()

    user.gcm_reg_id = gcm_reg_id
    user.save()
    return JsonResponse(__create_json_dict(ERROR_CODES.EC_SUCCESS))


@csrf_exempt
def mark_as_read(request):
    try:
        if request.method != 'POST':
            raise Http404("No POST requst")
        ids = json.loads(request.body)
    except ValueError:
        raise Http404("Not valid JSON")

    ec = ERROR_CODES.EC_SUCCESS
    for notification_id in ids:
        try:
            notification = Notifications.objects.get(pk=notification_id)
            notification.is_read = True
            notification.save()
        except (ValueError, Notifications.DoesNotExist):
            # Ignore bad ids
            ec = ERROR_CODES.EC_SOME_NOTIFICATION_NOT_SET_AS_READ

    return JsonResponse(__create_json_dict(ec))
