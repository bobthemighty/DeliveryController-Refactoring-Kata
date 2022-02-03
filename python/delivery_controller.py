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
        delivery_schedule: List[Delivery],
        notifier: Optional[Notifier] = None,
        maps: Optional[MapService] = None,
    ):
        self.delivery_schedule = delivery_schedule
        self.map_service = maps or MapService()
        self.notifier = notifier or SmtpNotifier(EmailGateway())

    def update_delivery(self, delivery_event: DeliveryEvent):
        next_delivery = None
        for i, delivery in enumerate(self.delivery_schedule):
            if delivery_event.id == delivery.id:
                delivery.arrived = True
                time_difference = (
                    delivery_event.time_of_delivery - delivery.time_of_delivery
                )
                if time_difference < datetime.timedelta(minutes=10):
                    delivery.on_time = True
                delivery.time_of_delivery = delivery_event.time_of_delivery
                self.notifier.request_feedback(delivery)

                if len(self.delivery_schedule) > i + 1:
                    next_delivery = self.delivery_schedule[i + 1]
                if not delivery.on_time and len(self.delivery_schedule) > 1 and i > 0:
                    previous_delivery = self.delivery_schedule[i - 1]
                    elapsed_time = (
                        delivery.time_of_delivery - previous_delivery.time_of_delivery
                    )
                    self.map_service.update_average_speed(
                        previous_delivery.location, delivery.location, elapsed_time
                    )
        if next_delivery:
            next_eta = self.map_service.calculate_eta(
                delivery_event.location, next_delivery.location
            )
            self.notifier.send_eta_update(next_delivery, next_eta)
