from planner_to_unit4.infrastructure.soap_envelope_builder import (
    POSTBACK_FIELDS_IN_ORDER,
    build_postback_items,
    build_soap_envelope,
)


def test_build_postback_items_sets_required_fields() -> None:
    rows = [
        {
            "Client": "BI",
            "Description": "Test",
            "Account": "1000",
            "Dim2": "A1",
            "Dim3": "X",
            "Dim4": "B1",
            "Dim6": "C1",
            "Dim7": "ROM",
            "Currency": "USD",
            "Period": "202601",
            "CurAmount": "12.25",
        }
    ]

    items = build_postback_items(rows, version="ADJ", batch="WKD")

    assert items[0]["TransactionId"] == -1
    assert items[0]["TransactionSetup"] == "STD"
    assert items[0]["Version"] == "ADJ"
    assert items[0]["Batch"] == "WKD"
    assert items[0]["Submit"] == 0
    assert items[0]["PeriodFrom"] == "202601"
    assert items[0]["PeriodTo"] == "202601"


def test_build_soap_envelope_respects_field_order() -> None:
    rows = [
        {
            "Client": "BI",
            "Description": "Test",
            "Account": "1000",
            "Dim2": "A1",
            "Dim3": "X",
            "Dim4": "B1",
            "Dim6": "C1",
            "Dim7": "ROM",
            "Currency": "USD",
            "Period": "202601",
            "CurAmount": "12.25",
        }
    ]

    items = build_postback_items(rows, version="ADJ", batch="WKD")
    envelope = build_soap_envelope(
        items=items,
        username="user",
        client="bi",
        password="secret",
    )

    postback_item = next(
        element for element in envelope.iter() if element.tag.endswith("PostbackItem")
    )
    field_tags = [child.tag for child in list(postback_item)]
    expected_tags = [f"plan:{field}" for field in POSTBACK_FIELDS_IN_ORDER]

    assert field_tags == expected_tags
