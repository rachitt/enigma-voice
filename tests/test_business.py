from tools.business import get_services, render_system_prompt


def test_get_services_returns_three_services_with_required_keys():
    services = get_services()

    assert len(services) == 3
    for service in services:
        assert set(service) == {"name", "short", "desc"}
        assert all(service.values())


def test_render_system_prompt_substitutes_business_placeholders():
    prompt = render_system_prompt()

    assert "Enigma Labs" in prompt
    assert "{{POSITIONING}}" not in prompt
    assert "{{SERVICE_LIST}}" not in prompt
    assert "{{DIFFERENTIATORS}}" not in prompt
    assert "{{TONE}}" not in prompt
    assert "{{LEAD_NAME}}" in prompt
    assert "{{CONTEXT}}" in prompt
