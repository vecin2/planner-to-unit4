import pytest

from planner_to_unit4.infrastructure.planning_service import ResolvedPostbackError
from planner_to_unit4.infrastructure.soap_planning_service import (
    SoapPlanningService,
    SoapSubmissionError,
)


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_send_segment_returns_order_no_on_success() -> None:
    response_xml = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <StatusItems>
                   <PostbackStatusItem>
                      <Name>orderno</Name>
                      <Value>51</Value>
                      <Message>Transactions posted for batch processing. Order no.: 51 (PL400).</Message>
                   </PostbackStatusItem>
                </StatusItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    captured = {}

    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["data"] = data
        return FakeResponse(200, response_xml)

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    result = service.send_segment(
        [
            {
                "record_no": 1,
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
                "Version": "ADJ",
                "Batch": "WKD",
            }
        ]
    )

    assert result["order_no"] == "51"
    assert result["http_status"] == 200
    assert result["message"] == "Transactions posted for batch processing. Order no.: 51 (PL400)."
    assert (
        result["status_message"]
        == "Transactions posted for batch processing. Order no.: 51 (PL400)."
    )
    assert result["resolved_errors"] == []
    assert result["has_partial_errors_notice"] is False
    assert isinstance(result["request_payload"], str)
    assert "SOAPAction" in captured["headers"]


def test_send_segment_returns_faultstring_on_non_200() -> None:
    response_xml = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <s:Fault>
             <faultcode>s:Server.GeneralError</faultcode>
             <faultstring xml:lang="en-US">Something went wrong.</faultstring>
          </s:Fault>
       </s:Body>
    </s:Envelope>
    """

    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        return FakeResponse(500, response_xml)

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    result = service.send_segment([{"record_no": 1, "Client": "BI"}])

    assert result["order_no"] is None
    assert result["http_status"] == 500
    assert result["message"] == "s:Server.GeneralError: Something went wrong."
    assert result["fault_code"] == "s:Server.GeneralError"
    assert result["fault_string"] == "Something went wrong."
    assert result["resolved_errors"] == []
    assert result["has_partial_errors_notice"] is False
    assert isinstance(result["request_payload"], str)


def test_send_segment_uses_raw_response_when_non_200_not_parseable() -> None:
    response_text = "not xml"

    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        return FakeResponse(500, response_text)

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    result = service.send_segment([{"record_no": 1, "Client": "BI"}])

    assert result["order_no"] is None
    assert result["http_status"] == 500
    assert result["message"] == response_text
    assert result["fault_code"] is None
    assert result["fault_string"] is None
    assert result["resolved_errors"] == []
    assert result["has_partial_errors_notice"] is False
    assert isinstance(result["request_payload"], str)


def test_send_segment_raises_submission_error_with_request_payload() -> None:
    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        raise TimeoutError("network timeout")

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    with pytest.raises(SoapSubmissionError, match="network timeout") as excinfo:
        service.send_segment([{"record_no": 1, "Client": "BI"}])

    assert isinstance(excinfo.value.request_payload, str)


def test_send_segment_resolves_log_item_rows_to_transaction_ids() -> None:
    response_xml = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>1</Row>
                      <Column>dim_2</Column>
                      <Message>Dim2 is required</Message>
                   </PostbackLogItem>
                   <PostbackLogItem>
                      <Row>0</Row>
                      <Message>There are more errors, but only the first 100 errors is returned from the web service</Message>
                   </PostbackLogItem>
                </LogItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        return FakeResponse(200, response_xml)

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    segment = [{"record_no": 11, "Client": "BI"}, {"record_no": 12, "Client": "BI"}]
    result = service.send_segment(segment)

    assert result["resolved_errors"] == [
        ResolvedPostbackError(
            row_index_1_based=1,
            transaction_id=-11,
            column="dim_2",
            message="Dim2 is required",
            failed_row={"record_no": 11, "Client": "BI"},
        )
    ]
    assert result["has_partial_errors_notice"] is True


def test_send_segment_uses_unknown_transaction_id_for_out_of_range_row() -> None:
    response_xml = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>4</Row>
                      <Column>dim_3</Column>
                      <Message>Invalid value</Message>
                   </PostbackLogItem>
                </LogItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    def fake_post(url: str, data: str, headers: dict[str, str], timeout: int) -> FakeResponse:
        return FakeResponse(200, response_xml)

    service = SoapPlanningService(
        endpoint="https://example.test/service.svc",
        username="user",
        client="bi",
        password="secret",
        http_post=fake_post,
        log_fn=lambda _message: None,
    )

    result = service.send_segment([{"record_no": 1, "Client": "BI"}])

    assert result["resolved_errors"] == [
        ResolvedPostbackError(
            row_index_1_based=4,
            transaction_id=None,
            column="dim_3",
            message="Invalid value",
            failed_row=None,
        )
    ]
    assert result["has_partial_errors_notice"] is False
