from django.core.mail import send_mail


def send_message(mailOptions):
    """
    Envia email usando Django mail backend

    mailOptions deve conter:
    - subject: str
    - body: str (HTML ou plain text)
    - from: str (seu-email@gmail.com)
    - to: list ou str (destinatários)
    """

    # Garantir que 'to' seja uma lista
    to_list = mailOptions['to'] if isinstance(mailOptions['to'], list) else [mailOptions['to']]

    try:
        send_mail(
            subject=mailOptions['subject'],
            message=mailOptions['body'],
            from_email=mailOptions['from'],
            recipient_list=to_list,
            fail_silently=False,
            html_message=mailOptions['body'],  # Para HTML
        )
        print(f'Email enviado com sucesso para {", ".join(to_list)}')
        return True
    except Exception as e:
        print(f'Erro ao enviar email: {e}')
        raise
