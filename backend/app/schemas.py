from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid', str_strip_whitespace=True)

class Credentials(Input):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class PasswordChange(Input):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    current_password: str = Field(min_length=1,max_length=128)
    new_password: str = Field(min_length=10,max_length=128)
    confirmation: str = Field(min_length=10,max_length=128)
    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password!=self.confirmation:raise ValueError('Новые пароли не совпадают')
        return self

class ChildInput(Input):
    request_id: str | None = Field(default=None,pattern=r'^[a-f0-9-]{36}$')
    name: str = Field(min_length=1,max_length=40)
    age: int = Field(ge=1,le=17)
    gender: Literal['male','female','unspecified']
    interests: list[str] = Field(default_factory=list,max_length=12)
    city: str = Field(min_length=1,max_length=80)
    consent: bool = False
    consent_version: str | None = None
    @field_validator('interests')
    @classmethod
    def tags(cls,v):
        if any(not x.strip() or len(x)>40 for x in v): raise ValueError('Некорректный интерес')
        return list(dict.fromkeys(x.strip() for x in v))

class StartInput(Input):
    child_id: str
    request_id: str = Field(pattern=r'^[a-f0-9-]{36}$')

class AnswerInput(Input):
    task_id: str
    option_id: str

class PhaseInput(Input):
    task_id: str

class FeedbackInput(Input):
    rating: int = Field(ge=1,le=5)
    message: str = Field(default='',max_length=2000)
    request_id: str = Field(pattern=r'^[a-f0-9-]{36}$')

class OpenInput(Input):
    club_id: str
    request_id: str = Field(pattern=r'^[a-f0-9-]{36}$')

class ClubInput(Input):
    request_id: str | None = Field(default=None,pattern=r'^[a-f0-9-]{36}$')
    name: str = Field(min_length=1,max_length=120)
    description: str = Field(min_length=1,max_length=2000)
    min_age: int = Field(ge=1,le=17)
    max_age: int = Field(ge=1,le=17)
    city: str = Field(min_length=1,max_length=80)
    address: str = Field(min_length=1,max_length=240)
    phone: str = Field(pattern=r'^\+?[0-9 ()-]{5,32}$')
    price: str = Field(min_length=1,max_length=120)
    photo_url: str = Field(default='',max_length=1000)
    archived: bool = False
    @model_validator(mode='after')
    def valid(self):
        from urllib.parse import urlparse
        if self.min_age>self.max_age: raise ValueError('Проверьте возрастной диапазон')
        if self.photo_url and (urlparse(self.photo_url).scheme not in ('http','https') or not urlparse(self.photo_url).netloc): raise ValueError('Нужен URL http или https')
        return self

class RuleInput(Input):
    metric: Literal['any','attention','memory'] = 'any'
    minimum: int = Field(default=0,ge=0,le=100)
    maximum: int = Field(default=100,ge=0,le=100)
    priority: int = Field(default=0,ge=-100,le=100)
    explanation: str = Field(min_length=1,max_length=300)
    @model_validator(mode='after')
    def valid(self):
        if self.minimum>self.maximum: raise ValueError('Минимум больше максимума')
        return self
