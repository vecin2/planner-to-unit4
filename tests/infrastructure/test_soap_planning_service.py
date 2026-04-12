from planner_to_unit4.infrastructure.soap_planning_service import SoapPlanningService


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
    assert "SOAPAction" in captured["headers"]
