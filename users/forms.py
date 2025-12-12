from django.contrib.auth.forms import UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'notification_email',
            'phone_number',
            'telegram_chat_id',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем дополнительные поля необязательными при создании
        for fname in ['email', 'first_name', 'notification_email', 'phone_number', 'telegram_chat_id']:
            if fname in self.fields:
                self.fields[fname].required = False
