"""Against a real broker: produce, then watch both consumer groups converge.

KAFKA_BOOTSTRAP_SERVERS=kafka:9092 python -m click_stream.smoke
"""

import os
import time

from pico_boot import init
from pico_ioc import DictSource, configuration

from click_stream.app import ClickEvents, PageViews, SessionAudit


def wait_for(condition, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.1)
    return condition()


def main() -> int:
    config = configuration(
        DictSource(
            {
                "kafka": {
                    "bootstrap_servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                    "group_id": "views",
                }
            }
        )
    )
    container = init(modules=["click_stream"], config=config)
    try:
        clicks, views, audit = (
            container.get(ClickEvents),
            container.get(PageViews),
            container.get(SessionAudit),
        )

        # consumers read from the latest offset: keep producing a warm-up record
        # until BOTH groups have been assigned their partition and see it
        deadline = time.monotonic() + 60
        while "warmup" not in views.by_page or "warmup" not in audit.sessions:
            if time.monotonic() > deadline:
                print("SMOKE FAILED: consumer groups never got assigned")
                return 1
            clicks.clicked({"page": "warmup", "session": "warmup"})
            time.sleep(0.5)

        clicks.clicked({"page": "home", "session": "s1"})
        clicks.clicked({"page": "cart", "session": "s1"})
        clicks.clicked(
            {"session": "s2"}
        )  # no page: PageViews skips it, SessionAudit keeps it
        clicks.clicked({"page": "home", "session": "s3"})

        def converged() -> bool:
            return (
                views.by_page.get("home") == 2
                and views.by_page.get("cart") == 1
                and "s3" in audit.sessions
            )

        ok = wait_for(converged, 15)
        sessions = [session for session in audit.sessions if session != "warmup"]
        pages = {page: hits for page, hits in views.by_page.items() if page != "warmup"}
        ok = ok and sessions == ["s1", "s1", "s2", "s3"]
        print(f"views={pages} sessions={sessions}")
        print(
            "SMOKE OK: two consumer groups read the topic independently through a real Kafka"
            if ok
            else "SMOKE FAILED"
        )
        return 0 if ok else 1
    finally:
        container.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
