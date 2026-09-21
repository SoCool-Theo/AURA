from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import backend.app.schemas as schemas_package
from backend.app.schemas.agent import (
    AgentConversationMessage,
    AgentExplainRequest,
    AgentExplainResponse,
    AgentSourceReference,
)


_PORTFOLIO_ID = "20000000-0000-0000-0000-000000000001"
_REPORT_ID = "10000000-0000-0000-0000-000000000001"
_SIMULATION_ID = "30000000-0000-0000-0000-000000000001"


def _valid_request_data() -> dict[str, object]:
    return {
        "portfolio_id": _PORTFOLIO_ID,
        "message": "Why is this portfolio risky?",
    }


def _valid_response_data() -> dict[str, object]:
    return {
        "answer": "The report identifies concentration as a risk driver.",
        "sources": [{"type": "portfolio", "id": _PORTFOLIO_ID}],
        "limitations": [
            "Historical results do not predict future performance."
        ],
    }


def test_agent_schemas_are_importable_directly() -> None:
    assert AgentExplainRequest.__module__ == "backend.app.schemas.agent"
    assert AgentSourceReference.__module__ == "backend.app.schemas.agent"
    assert AgentExplainResponse.__module__ == "backend.app.schemas.agent"


def test_request_accepts_valid_minimum_payload() -> None:
    request = AgentExplainRequest.model_validate(_valid_request_data())

    assert request.portfolio_id == UUID(_PORTFOLIO_ID)
    assert request.message == "Why is this portfolio risky?"
    assert request.report_id is None
    assert request.simulation_id is None
    assert request.history == []


def test_request_accepts_completed_conversation_history() -> None:
    data = _valid_request_data()
    data["history"] = [
        {"role": "user", "content": "What is my portfolio?"},
        {"role": "assistant", "content": "Your portfolio is concentrated in TLT."},
    ]

    request = AgentExplainRequest.model_validate(data)

    assert request.history == [
        AgentConversationMessage(role="user", content="What is my portfolio?"),
        AgentConversationMessage(
            role="assistant",
            content="Your portfolio is concentrated in TLT.",
        ),
    ]


@pytest.mark.parametrize(
    "history",
    [
        [{"role": "user", "content": "First question"}],
        [
            {"role": "assistant", "content": "Wrong first role"},
            {"role": "user", "content": "Wrong second role"},
        ],
        [
            {"role": "user", "content": "Question one"},
            {"role": "user", "content": "Question two"},
        ],
    ],
)
def test_request_rejects_incomplete_or_misordered_history(
    history: list[dict[str, str]],
) -> None:
    data = _valid_request_data()
    data["history"] = history

    with pytest.raises(ValidationError, match="history must"):
        AgentExplainRequest.model_validate(data)


def test_request_limits_history_to_four_completed_turns() -> None:
    data = _valid_request_data()
    data["history"] = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message {index}",
        }
        for index in range(10)
    ]

    with pytest.raises(ValidationError):
        AgentExplainRequest.model_validate(data)


@pytest.mark.parametrize(
    ("field_name", "resource_id"),
    [
        ("report_id", _REPORT_ID),
        ("simulation_id", _SIMULATION_ID),
    ],
)
def test_request_accepts_one_optional_resource_reference(
    field_name: str,
    resource_id: str,
) -> None:
    data = _valid_request_data()
    data[field_name] = resource_id

    request = AgentExplainRequest.model_validate(data)

    assert getattr(request, field_name) == UUID(resource_id)


def test_request_accepts_both_optional_resource_references() -> None:
    data = _valid_request_data()
    data.update(report_id=_REPORT_ID, simulation_id=_SIMULATION_ID)

    request = AgentExplainRequest.model_validate(data)

    assert request.report_id == UUID(_REPORT_ID)
    assert request.simulation_id == UUID(_SIMULATION_ID)


@pytest.mark.parametrize(
    "field_name",
    ["portfolio_id", "report_id", "simulation_id"],
)
def test_request_rejects_invalid_resource_uuids(field_name: str) -> None:
    data = _valid_request_data()
    data[field_name] = "not-a-uuid"

    with pytest.raises(ValidationError):
        AgentExplainRequest.model_validate(data)


def test_request_trims_message_without_mutating_input() -> None:
    data = _valid_request_data()
    data["message"] = "  Explain the drawdown.  "
    original = deepcopy(data)

    request = AgentExplainRequest.model_validate(data)

    assert request.message == "Explain the drawdown."
    assert data == original


@pytest.mark.parametrize("message", ["", " \t\n "])
def test_request_rejects_empty_message(message: str) -> None:
    data = _valid_request_data()
    data["message"] = message

    with pytest.raises(ValidationError, match="text cannot be empty"):
        AgentExplainRequest.model_validate(data)


def test_request_enforces_message_maximum_length() -> None:
    data = _valid_request_data()
    data["message"] = "m" * 4000

    assert AgentExplainRequest.model_validate(data).message == "m" * 4000

    data["message"] = "m" * 4001
    with pytest.raises(ValidationError):
        AgentExplainRequest.model_validate(data)


@pytest.mark.parametrize("field_name", ["unexpected", "user_id"])
def test_request_rejects_unapproved_fields(field_name: str) -> None:
    data = _valid_request_data()
    data[field_name] = str(uuid4())

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentExplainRequest.model_validate(data)


@pytest.mark.parametrize("source_type", ["portfolio", "report", "simulation"])
def test_source_reference_accepts_approved_types(source_type: str) -> None:
    source = AgentSourceReference.model_validate(
        {"type": source_type, "id": _PORTFOLIO_ID}
    )

    assert source.type == source_type
    assert source.id == UUID(_PORTFOLIO_ID)


def test_source_reference_rejects_invalid_type_uuid_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AgentSourceReference.model_validate(
            {"type": "market-data", "id": _PORTFOLIO_ID}
        )
    with pytest.raises(ValidationError):
        AgentSourceReference.model_validate(
            {"type": "portfolio", "id": "not-a-uuid"}
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentSourceReference.model_validate(
            {"type": "portfolio", "id": _PORTFOLIO_ID, "name": "Hidden"}
        )


def test_response_accepts_valid_grounded_response() -> None:
    response = AgentExplainResponse.model_validate(_valid_response_data())

    assert response.answer == _valid_response_data()["answer"]
    assert response.sources == [
        AgentSourceReference(type="portfolio", id=UUID(_PORTFOLIO_ID))
    ]
    assert len(response.limitations) == 1


def test_response_accepts_multiple_source_types_and_empty_limitations() -> None:
    data = _valid_response_data()
    data["sources"] = [
        {"type": "portfolio", "id": _PORTFOLIO_ID},
        {"type": "report", "id": _REPORT_ID},
        {"type": "simulation", "id": _SIMULATION_ID},
    ]
    data["limitations"] = []

    response = AgentExplainResponse.model_validate(data)

    assert [source.type for source in response.sources] == [
        "portfolio",
        "report",
        "simulation",
    ]
    assert response.limitations == []


def test_response_normalizes_non_empty_limitations() -> None:
    data = _valid_response_data()
    data["limitations"] = ["  This is educational information only.  "]

    response = AgentExplainResponse.model_validate(data)

    assert response.limitations == ["This is educational information only."]


@pytest.mark.parametrize("answer", ["", " \n\t "])
def test_response_rejects_empty_answer(answer: str) -> None:
    data = _valid_response_data()
    data["answer"] = answer

    with pytest.raises(ValidationError, match="text cannot be empty"):
        AgentExplainResponse.model_validate(data)


def test_response_enforces_answer_maximum_length() -> None:
    data = _valid_response_data()
    data["answer"] = "a" * 8000

    assert AgentExplainResponse.model_validate(data).answer == "a" * 8000

    data["answer"] = "a" * 8001
    with pytest.raises(ValidationError):
        AgentExplainResponse.model_validate(data)


def test_response_rejects_invalid_nested_source_and_unknown_fields() -> None:
    data = _valid_response_data()
    data["sources"] = [{"type": "invalid", "id": _PORTFOLIO_ID}]

    with pytest.raises(ValidationError):
        AgentExplainResponse.model_validate(data)

    data = _valid_response_data()
    data["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentExplainResponse.model_validate(data)


@pytest.mark.parametrize("limitation", ["", "  \n\t  "])
def test_response_rejects_empty_limitations(limitation: str) -> None:
    data = _valid_response_data()
    data["limitations"] = [limitation]

    with pytest.raises(ValidationError, match="text cannot be empty"):
        AgentExplainResponse.model_validate(data)


def test_agent_schemas_do_not_expand_stable_package_exports() -> None:
    assert not {
        "AgentExplainRequest",
        "AgentSourceReference",
        "AgentExplainResponse",
    }.intersection(schemas_package.__all__)
