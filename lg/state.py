from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from models.request import UserRequest
from models.classification import ClassificationBundle

#State containing: just the convos?
class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_request: UserRequest
    classification_bundle: ClassificationBundle