from xml.etree import ElementTree

import pytest

from planner_to_unit4.infrastructure.soap_response_parser import (
    PostbackLogItem,
    parse_object_postback_response,
    parse_object_postback_response_canonical,
    parse_postback_fault_canonical,
    parse_postback_fault_message,
    parse_segment_submission_response,
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
        result["message"] == "Transactions posted for batch processing. Order no.: 51 (PL400).; "
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
    assert result["message"] == "Row 2 col dim_3: B102397 is not a legal RESNO; Row ? col ?: ?"


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


def test_parse_object_postback_response_canonical_returns_structured_log_items() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>1151</Row>
                      <Column>dim_4</Column>
                      <Message>B102395 is not a legal BUS</Message>
                   </PostbackLogItem>
                   <PostbackLogItem>
                      <Row>0</Row>
                      <Message>There are more errors, but only the first 100 errors is returned from the web service</Message>
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

    parsed = parse_object_postback_response_canonical(xml_text)

    assert parsed.order_no == "51"
    assert (
        parsed.status_message == "Transactions posted for batch processing. Order no.: 51 (PL400)."
    )
    assert parsed.log_items == [
        PostbackLogItem(
            row=1151,
            column="dim_4",
            message="B102395 is not a legal BUS",
        ),
        PostbackLogItem(
            row=0,
            column=None,
            message=(
                "There are more errors, but only the first 100 errors is returned from the web service"
            ),
        ),
    ]


def test_parse_postback_fault_canonical_extracts_fault_and_log_items() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <s:Fault>
             <faultcode>s:Server.GeneralError</faultcode>
             <faultstring xml:lang="en-US">Something went wrong.</faultstring>
          </s:Fault>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>1219</Row>
                      <Column>dim_4</Column>
                      <Message>B102397 is not a legal BUS</Message>
                   </PostbackLogItem>
                </LogItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    parsed = parse_postback_fault_canonical(xml_text)

    assert parsed is not None
    assert parsed.fault_code == "s:Server.GeneralError"
    assert parsed.fault_string == "Something went wrong."
    assert parsed.message == "s:Server.GeneralError: Something went wrong."
    assert parsed.log_items == [
        PostbackLogItem(
            row=1219,
            column="dim_4",
            message="B102397 is not a legal BUS",
        )
    ]


def test_parse_postback_fault_canonical_returns_none_for_invalid_xml() -> None:
    assert parse_postback_fault_canonical("not xml") is None


def test_parse_segment_submission_response_for_200_status() -> None:
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

    parsed = parse_segment_submission_response(xml_text, http_status=200)

    assert parsed is not None
    assert parsed.order_no == "51"
    assert (
        parsed.status_message == "Transactions posted for batch processing. Order no.: 51 (PL400)."
    )
    assert parsed.fault_code is None
    assert parsed.fault_string is None
    assert parsed.log_items == [
        PostbackLogItem(
            row=2,
            column="dim_3",
            message="B102397 is not a legal RESNO",
        )
    ]


def test_parse_segment_submission_response_for_non_200_status() -> None:
    xml_text = """
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
       <s:Body>
          <s:Fault>
             <faultcode>s:Server.GeneralError</faultcode>
             <faultstring xml:lang="en-US">Something went wrong.</faultstring>
          </s:Fault>
          <ObjectPostBackResponse xmlns="http://services.agresso.com/PlanningService/PlanningV201302">
             <ObjectPostBackResult>
                <LogItems>
                   <PostbackLogItem>
                      <Row>1219</Row>
                      <Column>dim_4</Column>
                      <Message>B102397 is not a legal BUS</Message>
                   </PostbackLogItem>
                </LogItems>
             </ObjectPostBackResult>
          </ObjectPostBackResponse>
       </s:Body>
    </s:Envelope>
    """

    parsed = parse_segment_submission_response(xml_text, http_status=500)

    assert parsed is not None
    assert parsed.order_no is None
    assert parsed.status_message is None
    assert parsed.fault_code == "s:Server.GeneralError"
    assert parsed.fault_string == "Something went wrong."
    assert parsed.message == "s:Server.GeneralError: Something went wrong."
    assert parsed.log_items == [
        PostbackLogItem(
            row=1219,
            column="dim_4",
            message="B102397 is not a legal BUS",
        )
    ]


def test_parse_segment_submission_response_non_200_returns_none_for_invalid_xml() -> None:
    assert parse_segment_submission_response("not xml", http_status=500) is None


def test_parse_object_postback_response_raises_on_invalid_xml() -> None:
    with pytest.raises(ElementTree.ParseError):
        parse_object_postback_response("not xml")
