import time

from click_stream.app import ClickEvents, PageViews, SessionAudit

CONFIG = {"kafka": {"bootstrap_servers": "fake:9092", "group_id": "views"}}


def eventually(condition, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    return condition()


def test_both_groups_receive_every_record(make_container, bus):
    container = make_container("pico_kafka", config=CONFIG)
    clicks = container.get(ClickEvents)
    clicks.clicked({"page": "home", "session": "s1"})
    clicks.clicked({"page": "cart", "session": "s1"})
    views, audit = container.get(PageViews), container.get(SessionAudit)
    assert eventually(lambda: views.by_page == {"home": 1, "cart": 1})
    assert eventually(lambda: audit.sessions == ["s1", "s1"])
    assert sorted(consumer.group_id for consumer in bus.consumers["clicks"]) == [
        "audit",
        "views",
    ]


def test_poison_record_is_skipped_by_one_group_and_kept_by_the_other(
    make_container, bus
):
    container = make_container("pico_kafka", config=CONFIG)
    clicks = container.get(ClickEvents)
    clicks.clicked(
        {"session": "s2"}
    )  # no page: PageViews raises, the record is skipped
    clicks.clicked({"page": "home", "session": "s3"})
    views, audit = container.get(PageViews), container.get(SessionAudit)
    assert eventually(lambda: views.by_page == {"home": 1})
    assert eventually(lambda: audit.sessions == ["s2", "s3"])
