from agentvc_generator.models import RawSourceRecord, SourcePacket
from agentvc_generator.storage import GeneratorStore


def test_store_saves_packet(tmp_path):
    store = GeneratorStore(tmp_path / "generator.sqlite")
    raw = RawSourceRecord(
        source_name="PubMed",
        source_type="paper",
        source_url="https://example.com/1",
        external_id="1",
        payload={"title": "Example"},
    )
    packet = SourcePacket(
        channel="bioscience",
        source_name="PubMed",
        source_type="paper",
        source_url="https://example.com/1",
        external_id="1",
        title="Example",
        raw_text="Body",
        published_at="2026",
        fetched_at=raw.fetched_at,
        provenance={"raw_checksum": raw.checksum},
    )

    store.save_raw_record(raw)
    store.save_packet(packet)

    packets = store.list_packets()
    assert len(packets) == 1
    assert packets[0]["title"] == "Example"
    store.close()
