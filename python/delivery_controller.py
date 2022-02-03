import datetime
from dataclasses import dataclass
from typing import List, Optional

from email_gateway import EmailGateway
from map_service import MapService, Location


@dataclass
class DeliveryEvent:
    id: str
    time_of_delivery: datetime.datetime
    location: Location


@dataclass
class Delivery:
    id: str
    contact_email: str
    location: Location
    time_of_delivery: datetime.datetime
    arrived: bool
    on_time: bool

    def arrive(self, time):
        self.arrived = True

        time_difference = time - self.time_of_delivery
        if time_difference < datetime.timedelta(minutes=10):
            self.on_time = True
        self.time_of_delivery = time


@dataclass
class ScheduleItem:

    delivery: Delivery
    prev: Optional["ScheduleItem"] = None
    next: Optional["ScheduleItem"] = None

    def find(self, id):
        """
        Walk the list looking for a delivery
        that has the given id.
        """
        if self.delivery.id == id:
            return self
        if self.next is not None:
            return self.next.find(id)

    def record_speed(self, maps: MapService):
        if not self.prev:
            return

        delivery = self.delivery
        prev = self.prev.delivery

        elapsed = delivery.time_of_delivery - prev.time_of_delivery

        maps.update_average_speed(prev.location, delivery.location, elapsed)

    def eta(self, maps):
        if not self.next:
            return

        return maps.calculate_eta(self.delivery.location, self.prev.delivery.location)

def build_schedule(deliveries: List[Delivery]) -> ScheduleItem:
    """
    Build a linked list of scheduled items.
    Each item contains a delivery and has an optional
    prev/next item.
    """
    prev = head = ScheduleItem(deliveries[0])
    for delivery in deliveries[1::]:
        curr = ScheduleItem(delivery)
        prev.next = curr
        curr.prev = prev
        prev = curr
    return head


class Notifier:
    def request_feedback(self, delivery: Delivery):
        raise NotImplemented()

    def send_eta_update(self, delivery: Delivery, new_eta: int):
        raise NotImplemented()


class SmtpNotifier:
    def __init__(self, gateway: EmailGateway):
        self.gateway = gateway

    def request_feedback(self, delivery: Delivery):
        message = f"""Regarding your delivery today at {delivery.time_of_delivery}. How likely would you be to recommend this delivery service to a friend? Click <a href="url">here</a>"""
        self.gateway.send(
            delivery.contact_email, "Your feedback is important to us", message
        )

    def send_eta_update(self, delivery: Delivery, new_eta: int):
        message = f"Your delivery to {delivery.location} is next, estimated time of arrival is in {new_eta} minutes. Be ready!"
        self.gateway.send(
            delivery.contact_email, "Your delivery will arrive soon", message
        )


class DeliveryController:
    def __init__(
        self,
        deliveries: List[Delivery],
        notifier: Optional[Notifier] = None,
        maps: Optional[MapService] = None,
    ):
        self.delivery_schedule = build_schedule(deliveries)
        self.map_service = maps or MapService()
        self.notifier = notifier or SmtpNotifier(EmailGateway())

    def update_delivery(self, delivery_event: DeliveryEvent):
        scheduled = self.delivery_schedule.find(delivery_event.id)
        scheduled.delivery.arrive(delivery_event.time_of_delivery)

        self.notifier.request_feedback(scheduled.delivery)

        scheduled.record_speed(self.map_service)

        if scheduled.next:
            self.notifier.send_eta_update(scheduled.next.delivery, scheduled.eta(self.map_service))
