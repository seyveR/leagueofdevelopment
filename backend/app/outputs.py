from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict

class Output(BaseModel):
    model_config=ConfigDict(from_attributes=True)

class UserOut(Output):
    id:str;email:str;role:Literal['parent','admin']

class AuthOut(Output):
    user:UserOut | None;csrf:str

class ChildOut(Output):
    id:str;name:str;age:int;gender:str;interests:list[str];city:str;consent_at:datetime;consent_version:str

class SessionOut(Output):
    id:str;child_id:str;task_set_id:str;child_snapshot:dict;algorithm_version:str;position:int;phase:str;status:str;created_at:datetime;completed_at:datetime | None
    conditions:dict={}

class ResultOut(Output):
    id:str;session_id:str;algorithm_version:str;scores:dict;created_at:datetime

class ClubOut(Output):
    id:str;name:str;description:str;min_age:int;max_age:int;city:str;address:str;phone:str;price:str;photo_url:str;archived:bool

class RuleOut(Output):
    id:str;club_id:str;metric:str;minimum:int;maximum:int;priority:int;explanation:str

class StateOut(Output):
    children:list[ChildOut];sessions:list[SessionOut];results:list[ResultOut]

class TaskOut(Output):
    id:str;category:str;prompt:str;stimulus:str | None;options:list[dict[str,Any]]
    mechanic:str='choice';difficulty:int=1;left:list[str]=[];right:list[str]=[]

class DetailOut(Output):
    session:SessionOut;task:TaskOut | None;answers:list[dict[str,str]];total:int

class RecommendationOut(Output):
    club:ClubOut;explanation:str;rules_version:str

class FeedbackOut(Output):
    id:str;user_id:str;rating:int;message:str;created_at:datetime
