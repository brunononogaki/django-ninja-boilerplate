from django.core.mail import send_mail


def send_message(mailOptions):
    send_mail(
        mailOptions['subject'],
        mailOptions['body'],
        mailOptions['from'],
        mailOptions['to'],
        fail_silently=False,
    )
