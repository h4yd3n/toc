"""S6 outbound — Decision 1: check-in requests go out over SMS *and* chat at once.

Each channel is real when its credentials are configured and *simulated* otherwise. Simulated delivery is
recorded as such and shown as such — the wall never claims a message went out when it didn't."""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx


@dataclass
class Delivery:
    channel: str            # sms | chat
    status: str             # sent | simulated | failed
    provider_id: Optional[str] = None
    error: Optional[str] = None


def public_url() -> str:
    return os.environ.get("TOC_PUBLIC_URL", "http://localhost:5173").rstrip("/")


def checkin_message(person_name: str, incident_title: str, link: str) -> str:
    return (f"TOC roll call — {incident_title}. {person_name.split(' ')[0]}, please confirm you are safe: {link} "
            f"Reply SAFE, or call the watch floor if you need assistance.")


class SMSChannel:
    """Twilio Messages API over plain HTTP. Configured when TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM are set."""
    name = "sms"

    def __init__(self) -> None:
        self.sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.sender = os.environ.get("TWILIO_FROM")

    @property
    def configured(self) -> bool:
        return bool(self.sid and self.token and self.sender)

    async def send(self, to_phone: Optional[str], body: str) -> Delivery:
        if not to_phone:
            return Delivery("sms", "failed", error="no phone on file")
        if not self.configured:
            return Delivery("sms", "simulated")
        try:
            async with httpx.AsyncClient(timeout=15.0, auth=(self.sid, self.token)) as client:
                r = await client.post(f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json",
                                      data={"From": self.sender, "To": to_phone, "Body": body})
            if r.status_code in (200, 201):
                return Delivery("sms", "sent", provider_id=r.json().get("sid"))
            return Delivery("sms", "failed", error=f"twilio {r.status_code}: {r.text[:120]}")
        except Exception as e:  # noqa: BLE001
            return Delivery("sms", "failed", error=f"{type(e).__name__}: {e}")


class ChatChannel:
    """Slack incoming webhook. Configured when SLACK_WEBHOOK_URL is set. One post per roll call, naming everyone
    still unaccounted, into the ops channel — a webhook can't DM, so this is the floor's broadcast."""
    name = "chat"

    def __init__(self) -> None:
        self.webhook = os.environ.get("SLACK_WEBHOOK_URL")

    @property
    def configured(self) -> bool:
        return bool(self.webhook)

    async def post(self, text: str) -> Delivery:
        """One message to the ops channel — used to disseminate a product (§5.10 #4)."""
        if not self.configured:
            return Delivery("chat", "simulated")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(self.webhook, json={"text": text})
            return Delivery("chat", "sent") if r.status_code == 200 else Delivery("chat", "failed", error=f"slack {r.status_code}: {r.text[:120]}")
        except Exception as e:  # noqa: BLE001
            return Delivery("chat", "failed", error=f"{type(e).__name__}: {e}")

    async def broadcast(self, incident_title: str, names_and_links: List[tuple]) -> Delivery:
        if not self.configured:
            return Delivery("chat", "simulated")
        lines = "\n".join(f"• {n} — <{link}|check in>" for n, link in names_and_links)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(self.webhook, json={"text": f":rotating_light: *TOC roll call — {incident_title}*\nPlease confirm you are safe:\n{lines}"})
            if r.status_code == 200:
                return Delivery("chat", "sent")
            return Delivery("chat", "failed", error=f"slack {r.status_code}: {r.text[:120]}")
        except Exception as e:  # noqa: BLE001
            return Delivery("chat", "failed", error=f"{type(e).__name__}: {e}")


class Dispatcher:
    def __init__(self) -> None:
        self.sms, self.chat = SMSChannel(), ChatChannel()

    @property
    def simulated(self) -> bool:
        return not (self.sms.configured and self.chat.configured)

    async def request_checkins(self, incident_title: str, people: List[Dict], link_for) -> Dict[str, List[Delivery]]:
        """people: [{id, name, phone}] → per-person SMS deliveries, plus one chat broadcast copied to every person."""
        out: Dict[str, List[Delivery]] = {p["id"]: [] for p in people}
        for p in people:
            link = link_for(p["id"])
            out[p["id"]].append(await self.sms.send(p.get("phone"), checkin_message(p["name"], incident_title, link)))
        chat = await self.chat.broadcast(incident_title, [(p["name"], link_for(p["id"])) for p in people])
        for p in people:
            out[p["id"]].append(Delivery("chat", chat.status, chat.provider_id, chat.error))
        return out
