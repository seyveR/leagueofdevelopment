"""External channels are explicitly unavailable until a provider is configured."""
from typing import Protocol

class DeliveryUnavailable(RuntimeError):pass
class DeliveryAdapter(Protocol):
    def send(self,recipient:str,message:str)->str:...
class UnconfiguredChannel:
    def __init__(self,name):self.name=name
    def send(self,recipient,message):raise DeliveryUnavailable(f'{self.name}: провайдер не настроен; сообщение не отправлено')
EXTERNAL_CHANNELS={name:UnconfiguredChannel(name) for name in ('email','sms','push')}
def channel_status():return {'in_app':True,**{name:False for name in EXTERNAL_CHANNELS}}
