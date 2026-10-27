from mcplens.token_estimator import estimate_json_tokens, estimate_tool_tokens


def test_estimate_json_tokens():
    data = {"type": "object", "properties": {"name": {"type": "string"}}}
    tokens = estimate_json_tokens(data)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_estimate_tool_tokens():
    name = "get_user_profile"
    desc = "Retrieve user details and active permissions for the authenticated identity."
    schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The unique identifier"}
        },
        "required": ["user_id"],
    }
    tokens = estimate_tool_tokens(name, desc, schema)
    assert tokens > 30
    assert tokens < 200
