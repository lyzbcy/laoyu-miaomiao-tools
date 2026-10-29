"""Run the shipped recovery regressions against source."""
from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/tests/test_youtube_recovery.py'
spec=importlib.util.spec_from_file_location('publisher_recovery_cases',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
DOMRecovery=module.DOMRecovery
IdentityRecovery=module.IdentityRecovery
