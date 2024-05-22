import datetime
import logging

from kani import ChatMessage

from . import events
from .base_kani import BaseKani
from .delegation.delegate_and_wait import DelegateWaitMixin
from .functions.browsing import BrowsingMixin
from .namer import Namer

log = logging.getLogger(__name__)

# ==== prompts ====
ROOT_KANPAI = (
    "# Persona\n\nYou are acting as Kanpai. You are firm, dependable, a bit hot-headed, and tenacious, with a fiery"
    " temper. Despite being serious, you showcase a strong sense of camaraderie and loyalty. You should always reply in"
    " character.\n\n# Goals\n\nYour goal is to answer the user's questions and help them out by performing actions."
    " While you may be able to answer many questions from memory alone, the user's queries will sometimes require you"
    " to search on the Internet or take actions. You can use the provided function to ask your capable helpers, who can"
    " help you search the Internet and take actions. You should include any links they used in your response.\nThe"
    " current time is {time}."
)

DELEGATE_KANPAI = (
    "You are {name}, a helpful assistant with the goal of answering the user's questions as precisely as possible and"
    " helping them out by performing actions.\nYou can use the provided functions to search the Internet or ask your"
    " capable helpers, who can help you take actions.\nIf the user's query involves multiple steps, you should break it"
    " up into smaller pieces and delegate those pieces - for example, if you need to look up multiple sites, delegate"
    " each search to a helper. Say your plan before you do. If those pieces can be resolved at the same time, delegate"
    ' them all at once and use wait("all"). You may do multiple rounds of delegating and waiting for additional steps'
    " that depend on earlier steps.\nYou should include any links you used in your response.\nThe current time is"
    " {time}."
)


def get_system_prompt(kani: "BaseKani") -> str:
    """Fill in the system prompt template from the kani."""
    now = datetime.datetime.now().strftime("%a %d %b %Y, %I:%M%p")
    return kani.system_prompt.format(name=kani.name, time=now)


# ==== implementation ====
class RootKani(DelegateWaitMixin, BaseKani):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("retry_attempts", 10)
        super().__init__(*args, **kwargs)
        self.namer = Namer()

    async def get_prompt(self) -> list[ChatMessage]:
        if self.system_prompt is not None:
            self.always_included_messages[0] = ChatMessage.system(get_system_prompt(self))
        return await super().get_prompt()

    def create_delegate_kani(self):
        name = self.namer.get_name()
        return DelegateKani(self.engine, app=self.app, parent=self, system_prompt=DELEGATE_KANPAI, name=name)

    async def add_to_history(self, message: ChatMessage):
        await super().add_to_history(message)
        if self.parent is None:
            self.app.dispatch(events.RootMessage(msg=message))


class DelegateKani(BrowsingMixin, RootKani):
    pass
