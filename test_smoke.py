"""Smoke test for syllabus_service (no API call, uses mocks)."""
import sys
sys.path.insert(0, ".")

from services.syllabus_service import SyllabusSchema, _extract_json
from utils.prompts import build_syllabus_prompt

# 1. Pydantic schema validates correctly
mock_data = {
    "title": "Python for Data Science",
    "description": "A comprehensive intro.",
    "modules": [
        {"title": "Module 1", "lessons": ["Lesson 1A", "Lesson 1B"]},
        {"title": "Module 2", "lessons": ["Lesson 2A", "Lesson 2B"]},
    ]
}
syllabus = SyllabusSchema(**mock_data)
assert syllabus.title == "Python for Data Science"
assert len(syllabus.modules) == 2
assert syllabus.modules[0].lessons == ["Lesson 1A", "Lesson 1B"]
print("PASS: SyllabusSchema validates correctly")

# 2. build_syllabus_prompt contains the topic
p = build_syllabus_prompt("Machine Learning", 3, 2)
assert "Machine Learning" in p
assert "3" in p
print("PASS: build_syllabus_prompt works")

# 3. _extract_json strips triple-backtick fences
raw_with_fence = "```json\n{\"key\": \"value\"}\n```"
cleaned = _extract_json(raw_with_fence)
assert cleaned == '{"key": "value"}', repr(cleaned)
print("PASS: _extract_json strips markdown fences")

# 4. _extract_json is no-op on clean JSON
raw_clean = '{"title": "test"}'
assert _extract_json(raw_clean) == raw_clean
print("PASS: _extract_json passthrough on clean JSON")

print("\nAll tests passed.")
