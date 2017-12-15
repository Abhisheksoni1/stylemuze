from celery import task
from stylemuze.settings import DEFAULT_FROM_EMAIL
from django.core.mail import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from stylemuzeapp.models import Coupon


def send_mail_async(brand, body, mail_to):
    mail_to_list = [mail_to]
    subject = "Congrats! you have received a coupon from {}".format(brand)

    # Create a "related" message container that will hold the HTML
    # message and the image. These are "related" (not "alternative")
    # because they are different, unique parts of the HTML message,
    # not alternative (html vs. plain text) views of the same content.
    html_part = MIMEMultipart(_subtype='related')
    try:
        coupon = Coupon.objects.filter(brand=brand)[0]
        img_data = coupon.coupon_photo.read()
        # Create the body with HTML. Note that the image, since it is inline, is
        # referenced with the URL cid:myimage... you should take care to make
        # "myimage" unique

        html_part.attach(body)
        # Now create the MIME container for the image
        img = MIMEImage(img_data, 'jpeg')
        img.add_header('Content-Id', '<myimage>')  # angle brackets are important
        img.add_header("Content-Disposition", "inline", filename="myimage")
        html_part.attach(img)

        email = EmailMessage(subject=subject, from_email=DEFAULT_FROM_EMAIL, body=None, to=mail_to_list)
        email.attach(html_part)  # Attach the raw MIMEBase descendant. This is a public method on EmailMessage
        email.send()
    except Coupon.DoesNotExist:
        # TODO Exception does not pass silently use some logging or something to track it.
        pass


# create task for celery worker


@task
def send_mail(brand, body, mail_to):
    send_mail_async(brand=brand, body=body, mail_to=mail_to)
