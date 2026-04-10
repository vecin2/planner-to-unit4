from planner_to_unit4.infrastructure.soap_response_parser import parse_object_postback_response


def test_parse_object_postback_response_extracts_order_no_and_message() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems/>
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

    result = parse_object_postback_response(xml_text)

    assert result["order_no"] == "51"
    assert result["message"] == "Transactions posted for batch processing. Order no.: 51 (PL400)."
