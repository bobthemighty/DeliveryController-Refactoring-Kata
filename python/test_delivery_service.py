import pytest
import datetime

from delivery_controller import DeliveryController, Delivery, DeliveryEvent, SmtpNotifier
from map_service import MapService, Location

location1 = Location(52.2296756, 21.0122287)
location2 = Location(52.406374, 16.9251681)
location3 = Location(51.406374, 17.9251681)

now = datetime.datetime.now()
one_hour = datetime.timedelta(hours=1)


def test_map_service():
    map_service = MapService()
    assert map_service.calculate_distance(location1, location2) == pytest.approx(
        278.546, rel=1e-2
    )


class FakeEmailGateway:
    def __init__(self):
        self.sent = []

    def send(self, address, subject, message):
        self.sent.append((address, subject, message))


class FakeMapService:
    def __init__(self, value):
        self.value = value
        self.updates = []

    def calculate_eta(self, location1, location2):
        return self.value

    def update_average_speed(self, location1, location2, time):
        self.updates.append((location1, location2, time))


def a_delivery(
    id,
    contact_email="fred@codefiend.co.uk",
    location=location1,
    time=None,
    arrived=False,
    on_time=False,
):
    return Delivery(
        id=id,
        contact_email="fred@codefiend.co.uk",
        location=location,
        time_of_delivery=time or now,
        arrived=False,
        on_time=False,
    )


def test_a_single_delivery_is_delivered():

    delivery = a_delivery(1)
    gateway = FakeEmailGateway()
    controller = DeliveryController([delivery], SmtpNotifier(gateway))

    controller.update_delivery(DeliveryEvent(1, now, location2))

    assert delivery.arrived is True
    assert delivery.on_time is True

    assert len(gateway.sent) == 1

    [(address, subject, message)] = gateway.sent
    assert address == "fred@codefiend.co.uk"
    assert subject == f"Your feedback is important to us"
    assert (
        message
        == f'Regarding your delivery today at {now}. How likely would you be to recommend this delivery service to a friend? Click <a href="url">here</a>'
    )



def test_when_a_delivery_affects_the_schedule():
    """
    In this scenario, we have three deliveries to three locations.
    The first is scheduled to happen now, the second in an hour, the third in
    two hours.

    When the second delivery is delivered an hour late, we should call the map
    service to recalculate our average speed.

    We should send an email to the recipient of delivery 3 with the updated
    ETA.
    """

    deliveries = [
        a_delivery(1, time=now, location=location1),
        a_delivery(2, time=now + one_hour, location=location2),
        a_delivery(3, time=now + (one_hour * 2), location=location3),
    ]

    gateway = FakeEmailGateway()
    maps = FakeMapService(325)
    controller = DeliveryController(deliveries, SmtpNotifier(gateway), maps)

    controller.update_delivery(DeliveryEvent(2, now + (one_hour * 2), location2))

    [(start, end, time)] = maps.updates

    assert start == location1
    assert end == location2
    assert time == (one_hour * 2)

    [_,(address, subject, message)] = gateway.sent

    assert subject == "Your delivery will arrive soon"
    assert message == f"Your delivery to {location3} is next, estimated time of arrival is in 325 minutes. Be ready!"
