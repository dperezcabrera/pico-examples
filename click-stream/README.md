# click-stream

Two consumer groups on one Kafka topic, reading independently: `PageViews` (group `views`) counts pages, `SessionAudit` (group `audit`) keeps every session. One `@kafka_producer` feeds both.

What to look at:

- `@kafka_consumer("clicks")` takes the group from `kafka.group_id`; `@kafka_consumer("clicks", group_id="audit")` is a second, independent group on the same topic.
- A record without `page` makes `PageViews` raise: the record is logged and skipped, the offset advances, and the next record is counted. `SessionAudit` never noticed. The test asserts both.
- `smoke.py` runs the same components against a real Kafka (KRaft, single node) booted by `pico_boot.init`, and shows a Kafka fact the fake hides: a consumer group reads from the latest offset once it is assigned, so the smoke warms up until both groups are listening before producing the records it asserts on.

```bash
pip install -e ".[dev]" && pytest
./smoke.sh
```
