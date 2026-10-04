from osahi.telemetry import model_attributes, tool_attributes


def test_model_and_tool_attributes_reuse_gen_ai_names():
    model = model_attributes(
        run_id="run_0001",
        workload_id="wl_echo",
        harness_name="osahi-reference",
        model_name="fixture-model",
        provider="scripted",
    )
    tool = tool_attributes(
        run_id="run_0001",
        workload_id="wl_echo",
        harness_name="osahi-reference",
        tool_name="echo",
        effect="deny",
    )
    assert model["gen_ai.operation.name"] == "chat"
    assert model["gen_ai.request.model"] == "fixture-model"
    assert model["gen_ai.system"] == "scripted"
    assert tool["gen_ai.operation.name"] == "execute_tool"
    assert tool["osahi.capability.effect"] == "deny"
    assert tool["osahi.spec.version"] == "0.1.0"
