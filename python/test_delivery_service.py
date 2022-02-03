import pytest
import datetime

from delivery_controller import DeliveryController, Delivery, DeliveryEvent
from map_service import MapService, Location

location1 = Location(52.2296756, 21.0122287)
location2 = Location(52.406374, 16.9251681)


def test_map_service():
    map_service = MapService()
    assert map_service.calculate_distance(location1, location2) == pytest.approx(
        278.546, rel=1e-2
    )


class FakeEmailGateway:
    def send(self, address, subject, message):
        pass


def test_a_single_delivery_is_delivered():

    now = datetime.datetime.now()

    delivery = Delivery(
        id=1,
        contact_email="fred@codefiend.co.uk",
        location=location1,
        time_of_delivery=now,
        arrived=False,
        on_time=True,
    )

    update = DeliveryEvent(1, now, location2)
    gateway = FakeEmailGateway()
    controller = DeliveryController([delivery], gateway)

    controller.update_delivery(update)

    assert delivery.arrived is True
    assert delivery.on_time is True
