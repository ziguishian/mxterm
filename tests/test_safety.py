from mxterm.safety.assessor import assess_command


def test_high_risk_command_is_blocked():
    assessment = assess_command("rm -rf /", block_high_risk=True)
    assert assessment.level == "high"
    assert assessment.blocked is True


def test_medium_risk_command_requires_attention():
    assessment = assess_command("sudo apt update", block_high_risk=True)
    assert assessment.level == "medium"
    assert assessment.blocked is False


def test_low_risk_command_passes():
    assessment = assess_command("ls -la", block_high_risk=True)
    assert assessment.level == "low"
