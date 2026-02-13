import smtplib


class DummySMTP:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self, *args, **kwargs):
        return None

    def login(self, *args, **kwargs):
        return None

    def send_message(self, *args, **kwargs):
        return None

    def sendmail(self, *args, **kwargs):
        return {}



def test_email_service_send(monkeypatch):
    from email_service import EmailService

    monkeypatch.setattr(smtplib, 'SMTP', DummySMTP)

    service = EmailService()
    assert service.send_email('client@example.com', 'Sujet', 'Bonjour') is True

    attachment_data = b"test"
    assert service.send_email_with_attachment(
        'client@example.com',
        'Sujet PJ',
        'Bonjour',
        attachment_data,
        'test.txt'
    ) is True
