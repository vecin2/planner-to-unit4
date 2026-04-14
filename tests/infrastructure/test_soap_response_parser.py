from xml.etree import ElementTree

import pytest

from planner_to_unit4.infrastructure.soap_response_parser import (
    parse_object_postback_response,
    parse_postback_fault_message,
)


def test_parse_object_postback_response_extracts_order_no_and_message() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>2</Row>
                      <Column>dim_3</Column>
                      <Message>B102397 is not a legal RESNO</Message>
                   </PostbackLogItem>
                </LogItems>
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
    assert (
        result["message"]
        == "Transactions posted for batch processing. Order no.: 51 (PL400).; "
        "Row 2 col dim_3: B102397 is not a legal RESNO"
    )


def test_parse_object_postback_response_aggregates_log_items() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>2</Row>
                      <Column>dim_3</Column>
                      <Message>B102397 is not a legal RESNO</Message>
                   </PostbackLogItem>
                   <PostbackLogItem>
                      <Row></Row>
                      <Column></Column>
                      <Message></Message>
                   </PostbackLogItem>
                </LogItems>
                <StatusItems/>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    result = parse_object_postback_response(xml_text)

    assert result["order_no"] is None
    assert (
        result["message"]
        == "Row 2 col dim_3: B102397 is not a legal RESNO; Row ? col ?: ?"
    )


def test_parse_postback_fault_message_extracts_faultstring() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <s:Fault>
             <faultcode>s:Server.GeneralError</faultcode>
             <faultstring xml:lang="en-US">Something went wrong.</faultstring>
          </s:Fault>
       </s:Body>
    </s:Envelope>
    """

    message = parse_postback_fault_message(xml_text)

    assert message == "s:Server.GeneralError: Something went wrong."


def test_parse_postback_fault_message_falls_back_to_log_items() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>2</Row>
                      <Column>dim_3</Column>
                      <Message>B102397 is not a legal RESNO</Message>
                   </PostbackLogItem>
                </LogItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    message = parse_postback_fault_message(xml_text)

    assert message == "Row 2 col dim_3: B102397 is not a legal RESNO"


def test_parse_object_postback_response_raises_on_invalid_xml() -> None:
    with pytest.raises(ElementTree.ParseError):
        parse_object_postback_response("not xml")
