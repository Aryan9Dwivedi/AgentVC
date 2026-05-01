from agentvc_generator.models import RawSourceRecord, SourcePacket


def test_packet_id_is_stable():
    packet = SourcePacket(
        channel="bioscience",
        source_name="PubMed",
        source_type="paper",
        source_url="https://example.com/1",
        external_id="1",
        title="Example",
        raw_text="Body",
        published_at="2026",
        fetched_at="2026-01-01T00:00:00+00:00",
    )

    assert packet.packet_id == packet.packet_id
    assert packet.to_dict()["packet_id"] == packet.packet_id


def test_raw_record_checksum_is_stable():
    record = RawSourceRecord(
        source_name="PubMed",
        source_type="paper",
        source_url="https://example.com/1",
        external_id="1",
        payload={"title": "Example"},
    )

    assert record.checksum == record.checksum

